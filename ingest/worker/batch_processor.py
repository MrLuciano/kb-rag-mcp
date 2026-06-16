"""
PHASE 8: Batch document processor for high-throughput ingestion.

Optimizes ingestion by:
1. Collecting multiple files before processing
2. Batching all chunk embeddings together
3. Parallel batch upsert to Qdrant

Can achieve 3-5x throughput vs sequential processing.
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from ingest.validation.pipeline import (
    ValidationPipeline,
    create_default_pipeline,
)

log = logging.getLogger("kb-ingest.worker.batch")


@dataclass
class FileChunk:
    """
    Single chunk from a file with metadata.

    Attributes:
        file_path: Source file path
        chunk_index: Index in document
        text: Chunk text content
        metadata: Additional metadata dict
    """

    file_path: Path
    chunk_index: int
    text: str
    metadata: dict


@dataclass
class BatchResult:
    """
    Result of batch processing.

    Attributes:
        total_files: Number of files processed
        total_chunks: Number of chunks created
        success_files: Number of successful files
        failed_files: List of (file_path, error) tuples
        elapsed_seconds: Total processing time
    """

    total_files: int
    total_chunks: int
    success_files: int
    failed_files: List[tuple[Path, str]]
    elapsed_seconds: float


class BatchDocumentProcessor:
    """
    PHASE 8: High-throughput batch document processor.

    Processes multiple files in optimized batches:
    1. Parse all files → collect chunks
    2. Batch embed all chunks together (native API)
    3. Batch upsert all vectors to Qdrant

    Example:
        processor = BatchDocumentProcessor(
            vector_store=store,
            registry=registry,
            batch_size=50,
        )
        result = await processor.process_files(file_paths)
        print(f"Processed {result.total_chunks} chunks "
              f"in {result.elapsed_seconds:.1f}s")
    """

    def __init__(
        self,
        vector_store,
        registry,
        batch_size: int = 50,
        embed_batch_size: int = 32,
        validation_pipeline: Optional[ValidationPipeline] = None,
        skip_validation: bool = False,
    ):
        """
        Initialize batch processor.

        Args:
            vector_store: Qdrant vector store
            registry: File registry
            batch_size: Files to process per batch
            embed_batch_size: Texts per embedding batch
            validation_pipeline: Optional validation pipeline
            skip_validation: Skip validation (for testing)
        """
        self.vector_store = vector_store
        self.registry = registry
        self.batch_size = batch_size
        self.embed_batch_size = embed_batch_size
        self.validation_pipeline = (
            validation_pipeline
            if validation_pipeline is not None
            else create_default_pipeline()
        )
        self.skip_validation = skip_validation

        log.info(
            f"BatchProcessor: batch_size={batch_size}, "
            f"embed_batch_size={embed_batch_size}"
        )

    async def process_files(
        self,
        file_paths: List[Path],
        docs_root: Path,
        product_override: Optional[str] = None,
        force: bool = False,
    ) -> BatchResult:
        """
        Process multiple files in optimized batches.

        Args:
            file_paths: List of files to process
            docs_root: Root documentation directory
            product_override: Override product detection
            force: Re-process already indexed files

        Returns:
            BatchResult with processing statistics
        """
        import time

        start_time = time.time()

        log.info(
            f"Batch processing {len(file_paths)} files "
            f"(batch_size={self.batch_size})"
        )

        all_chunks: List[FileChunk] = []
        failed_files: List[tuple[Path, str]] = []
        success_count = 0

        # Step 1: Parse all files and collect chunks
        for i in range(0, len(file_paths), self.batch_size):
            batch_files = file_paths[i : i + self.batch_size]

            log.debug(
                f"Processing file batch {i // self.batch_size + 1}: "
                f"{len(batch_files)} files"
            )

            # Parse files in parallel
            parse_tasks = [
                self._parse_file(fp, docs_root, product_override, force)
                for fp in batch_files
            ]
            parse_results = await asyncio.gather(
                *parse_tasks, return_exceptions=True
            )

            for file_path, result in zip(batch_files, parse_results):
                if isinstance(result, Exception):
                    failed_files.append((file_path, str(result)))
                    log.error(f"Parse failed: {file_path.name}: {result}")
                elif result is None:
                    # Skipped (validation failed or already indexed)
                    log.debug(f"Skipped: {file_path.name}")
                else:
                    assert isinstance(result, list)
                    all_chunks.extend(result)
                    success_count += 1

        if not all_chunks:
            log.warning("No chunks to embed (all files skipped or failed)")
            return BatchResult(
                total_files=len(file_paths),
                total_chunks=0,
                success_files=success_count,
                failed_files=failed_files,
                elapsed_seconds=time.time() - start_time,
            )

        log.info(f"Parsed {success_count} files → {len(all_chunks)} chunks")

        # Step 2: Batch embed all chunks
        try:
            chunk_texts = [chunk.text for chunk in all_chunks]

            # Import here to avoid circular dependency
            from kb_server.embed_client import get_embeddings_batch

            log.info(
                f"Batch embedding {len(chunk_texts)} chunks "
                f"(embed_batch_size={self.embed_batch_size})..."
            )
            vectors = await get_embeddings_batch(
                chunk_texts,
                batch_size=self.embed_batch_size,
                use_cache=True,
            )

            log.info(f"Embedded {len(vectors)} chunks")

        except Exception as e:
            log.error(f"Batch embedding failed: {e}", exc_info=True)
            # Mark all files as failed
            for file_path in file_paths:
                if file_path not in [f[0] for f in failed_files]:
                    failed_files.append((file_path, f"Embedding failed: {e}"))
            return BatchResult(
                total_files=len(file_paths),
                total_chunks=len(all_chunks),
                success_files=0,
                failed_files=failed_files,
                elapsed_seconds=time.time() - start_time,
            )

        # Step 3: Batch upsert to Qdrant
        try:
            qdrant_chunks = []
            for chunk, vector in zip(all_chunks, vectors):
                qdrant_chunks.append(
                    {
                        "text": chunk.text,
                        "vector": vector,
                        "chunk_index": chunk.chunk_index,
                        **chunk.metadata,
                    }
                )

            log.info(f"Upserting {len(qdrant_chunks)} chunks to Qdrant...")

            # Use parallel batch upsert for large batches
            if len(qdrant_chunks) > 300:
                await self.vector_store.upsert_chunks_parallel(
                    qdrant_chunks, max_parallel=3
                )
            else:
                await self.vector_store.upsert_chunks(qdrant_chunks)

            log.info("Upsert complete")

        except Exception as e:
            log.error(f"Batch upsert failed: {e}", exc_info=True)
            # Mark all files as failed
            for file_path in file_paths:
                if file_path not in [f[0] for f in failed_files]:
                    failed_files.append((file_path, f"Upsert failed: {e}"))
            return BatchResult(
                total_files=len(file_paths),
                total_chunks=len(all_chunks),
                success_files=0,
                failed_files=failed_files,
                elapsed_seconds=time.time() - start_time,
            )

        # Step 4: Update registry for successful files
        try:
            from ingest.core.metadata import IngestRegistry

            seen: set[Path] = set()
            for chunk in all_chunks:
                file_path = chunk.file_path
                if file_path in seen:
                    continue
                seen.add(file_path)
                _checksum = IngestRegistry.sha256(file_path)
                _chunks = sum(
                    1 for c in all_chunks if c.file_path == file_path
                )
                self.registry.mark_indexed(
                    str(file_path.relative_to(docs_root)),
                    checksum=_checksum,
                    chunks=_chunks,
                )
        except Exception as e:
            log.warning(f"Registry update failed: {e}")

        elapsed = time.time() - start_time
        throughput = len(all_chunks) / elapsed if elapsed > 0 else 0

        log.info(
            f"Batch complete: {success_count} files, "
            f"{len(all_chunks)} chunks in {elapsed:.1f}s "
            f"({throughput:.1f} chunks/sec)"
        )

        return BatchResult(
            total_files=len(file_paths),
            total_chunks=len(all_chunks),
            success_files=success_count,
            failed_files=failed_files,
            elapsed_seconds=elapsed,
        )

    async def _parse_file(
        self,
        file_path: Path,
        docs_root: Path,
        product_override: Optional[str],
        force: bool,
    ) -> Optional[List[FileChunk]]:
        """
        Parse single file and return chunks.

        Returns:
            List of FileChunk objects, or None if skipped
        """
        # Validation
        if not self.skip_validation:
            result = self.validation_pipeline.validate_file(file_path)  # type: ignore[attr-defined]
            if not result.is_valid():
                log.debug(
                    f"Validation failed: {file_path.name}: "
                    f"{result.get_error_summary()}"
                )
                return None

        # Check if already indexed
        relative_path = str(file_path.relative_to(docs_root))
        if not force and self.registry.is_indexed(relative_path):
            log.debug(f"Already indexed: {file_path.name}")
            return None

        # Parse document
        try:
            from ingest.classifier import classify_document
            from ingest.ingest import parse_document

            # Classify document
            doc_info = classify_document(file_path)
            product = product_override or doc_info.get("product", "geral")
            doc_type = doc_info.get("doc_type", "document")

            # Parse into chunks
            chunks_data = parse_document(file_path)

            if not chunks_data:
                log.warning(f"No chunks extracted: {file_path.name}")
                return None

            # Create FileChunk objects
            file_chunks = []
            for idx, chunk_dict in enumerate(chunks_data):
                file_chunks.append(
                    FileChunk(
                        file_path=file_path,
                        chunk_index=idx,
                        text=chunk_dict["text"],
                        metadata={
                            "source_file": str(
                                file_path.relative_to(docs_root)
                            ),
                            "file_type": chunk_dict.get(
                                "file_type", "unknown"
                            ),
                            "product": product,
                            "doc_type": doc_type,
                            "vendor": doc_info.get("vendor", ""),
                            "subsystem": doc_info.get("subsystem", ""),
                            "page": chunk_dict.get("page"),
                        },
                    )
                )

            return file_chunks

        except Exception as e:
            log.error(f"Parse error: {file_path.name}: {e}")
            raise
