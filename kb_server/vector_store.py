"""
Vector Store — Qdrant abstraction.
Manages collections, semantic search, filters, and metadata.

PHASE 8: Enhanced with connection pooling and batch optimizations.
"""

import logging
import os
import uuid


from kb_server.embed_client import get_embed_dim
from qdrant_client import AsyncQdrantClient  # type: ignore[import]
from qdrant_client import models as qmodels  # type: ignore[import]
from qdrant_client.models import Distance  # type: ignore[import]
from qdrant_client.http.models import (  # type: ignore[import]
    NamedSparseVector,
    SparseVector,
)
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

log = logging.getLogger("kb-mcp.store")

# ── Config
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_PATH = os.getenv("QDRANT_PATH", "")  # if set, uses embedded mode
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "kb_docs")
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "0.35"))

# PHASE 8: Connection pool and batch config
QDRANT_GRPC = os.getenv("QDRANT_GRPC", "false").lower() == "true"
QDRANT_GRPC_PORT = int(os.getenv("QDRANT_GRPC_PORT", "6334"))
QDRANT_TIMEOUT = float(os.getenv("QDRANT_TIMEOUT", "60.0"))
QDRANT_BATCH_SIZE = int(os.getenv("QDRANT_BATCH_SIZE", "100"))


class VectorStore:
    """Abstraction over Qdrant for vector storage, search, and metadata management.

    Provides semantic search with optional filtering by product, doc_type,
    version, and file_type. Supports batch upsert operations, sparse vector
    search for hybrid retrieval, and scroll-based document listing.

    Attributes:
        client: AsyncQdrantClient instance (None until connect() is called).
        collection: Name of the default Qdrant collection.
        dim: Embedding vector dimension.
        batch_size: Number of points per batch during upsert.
    """

    def __init__(self):
        self.client: AsyncQdrantClient | None = None
        # Read at init time (not module import) so env overrides set before
        # construction (e.g. in run_qa.py) are respected.
        self.collection = os.getenv("QDRANT_COLLECTION", "kb_docs")
        self.dim = get_embed_dim()
        self.batch_size = QDRANT_BATCH_SIZE

    async def connect(self) -> None:
        """Connect to Qdrant with connection pooling support.

        Supports HTTP API (default), gRPC API (set QDRANT_GRPC=true for
        better performance), and embedded mode (set QDRANT_PATH).

        Raises:
            RuntimeError: If the VectorStore is already connected.
        """
        if self.client is not None:
            raise RuntimeError("VectorStore already connected")
        if QDRANT_PATH:
            log.info(f"Qdrant embedded at: {QDRANT_PATH}")
            self.client = AsyncQdrantClient(
                path=QDRANT_PATH,
                timeout=QDRANT_TIMEOUT,
            )
        elif QDRANT_GRPC:
            log.info(
                f"Qdrant gRPC server at: {QDRANT_HOST}:{QDRANT_GRPC_PORT}"
            )
            self.client = AsyncQdrantClient(
                host=QDRANT_HOST,
                grpc_port=QDRANT_GRPC_PORT,
                prefer_grpc=True,
                timeout=QDRANT_TIMEOUT,
            )
        else:
            log.info(f"Qdrant HTTP server at: {QDRANT_HOST}:{QDRANT_PORT}")
            self.client = AsyncQdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT,
                timeout=QDRANT_TIMEOUT,
            )

        await self._ensure_collection()
        log.info(
            f"Connected to Qdrant — collection: {self.collection}, "
            f"batch_size: {self.batch_size}"
        )

    async def _ensure_collection(self) -> None:
        if self.client is None:
            raise RuntimeError("VectorStore client not connected")

        """Create the collection if it doesn't exist."""
        existing = [
            c.name for c in (await self.client.get_collections()).collections
        ]
        if self.collection not in existing:
            await self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=self.dim, distance=Distance.COSINE
                ),
            )
            log.info(f"Collection '{self.collection}' created (dim={self.dim})")
            
            # PHASE 12: Create payload indexes for fast filtered queries
            await self._create_payload_indexes()

    async def _create_payload_indexes(self) -> None:
        """
        Create payload indexes on product, doc_type, and version fields.
        
        PHASE 12: Accelerates filtered queries from O(n) to O(log n).
        PHASE 13: Added version field index.
        """
        if self.client is None:
            raise RuntimeError("VectorStore client not connected")
        
        indexed_fields = ["product", "doc_type", "version"]        
        for field in indexed_fields:
            try:
                await self.client.create_payload_index(
                    collection_name=self.collection,
                    field_name=field,
                    field_schema=PayloadSchemaType.KEYWORD,
                    wait=True,
                )
                log.info(f"Index created on field '{field}'")
            except Exception as e:
                # Non-fatal: indexes improve performance but aren't critical
                log.warning(
                    f"Failed to create index on field '{field}': {e}"
                )

    # ── Search ──────────────────────────────────────────────────────

    async def search(
        self,
        vector: list[float],
        top_k: int = 5,
        filter_type: str | None = None,
        product: str | None = None,
        doc_type: str | None = None,
        version: str | None = None,  # PHASE 13: Version filter
        vendor: str | None = None,  # PHASE 11.1: Vendor filter
        subsystem: str | None = None,  # PHASE 11.1: Subsystem filter
        module: str | None = None,  # PHASE 17: Module filter
        collection_name: str | None = None,  # PHASE 15: multi-collection override
    ) -> list[dict]:
        """Semantic search with optional filters by
        file_type, product, doc_type, version, vendor, subsystem, and module.
        """
        if self.client is None:
            raise RuntimeError("VectorStore client not connected")
        conditions = []
        if filter_type:
            conditions.append(
                FieldCondition(
                    key="file_type", match=MatchValue(value=filter_type)
                )
            )
        if product:
            conditions.append(
                FieldCondition(key="product", match=MatchValue(value=product))
            )
        if doc_type:
            conditions.append(
                FieldCondition(
                    key="doc_type", match=MatchValue(value=doc_type)
                )
            )
        if version:  # PHASE 13: Version filtering
            conditions.append(
                FieldCondition(
                    key="version", match=MatchValue(value=version)
                )
            )
        if vendor:  # PHASE 11.1: Vendor filtering
            conditions.append(
                FieldCondition(
                    key="vendor", match=MatchValue(value=vendor)
                )
            )
        if subsystem:  # PHASE 11.1: Subsystem filtering
            conditions.append(
                FieldCondition(
                    key="subsystem", match=MatchValue(value=subsystem)
                )
            )
        if module:  # PHASE 17: Module filtering
            conditions.append(
                FieldCondition(
                    key="module", match=MatchValue(value=module)
                )
            )

        query_filter = Filter(must=conditions) if conditions else None

        response = await self.client.query_points(
            collection_name=collection_name or self.collection,
            query=vector,
            limit=top_k,
            query_filter=query_filter,
            score_threshold=SCORE_THRESHOLD,
            with_payload=True,
        )

        return [
            {
                "chunk_id": str(r.id),
                "score": r.score,
                "text": r.payload.get("text", ""),
                "source_file": r.payload.get("source_file", ""),
                "file_type": r.payload.get("file_type", ""),
                "vendor": r.payload.get("vendor", ""),  # PHASE 11.1
                "product": r.payload.get("product", ""),
                "subsystem": r.payload.get("subsystem", ""),  # PHASE 11.1
                "module": r.payload.get("module", ""),  # PHASE 17
                "doc_type": r.payload.get("doc_type", "document"),
                "version": r.payload.get("version", ""),  # PHASE 13
                "page": r.payload.get("page"),
                "chunk_index": r.payload.get("chunk_index", 0),
            }
            for r in response.points
        ]

    async def search_sparse(
        self,
        sparse_vector: dict[int, float],
        top_k: int = 5,
        filter_type: str | None = None,
        product: str | None = None,
        doc_type: str | None = None,
        version: str | None = None,
        vendor: str | None = None,  # PHASE 11.1: Vendor filter
        subsystem: str | None = None,  # PHASE 11.1: Subsystem filter
        module: str | None = None,  # PHASE 17: Module filter
        collection_name: str | None = None,
    ) -> list[dict]:
        """
        BM25 sparse vector search against Qdrant.

        Requires the target collection to have a sparse vector field named
        ``"sparse"``. If the collection does not have sparse vectors (common
        for existing collections), this method returns an empty list so the
        caller can gracefully fall back to dense-only results.
        """
        if self.client is None:
            raise RuntimeError("VectorStore client not connected")
        if not sparse_vector:
            return []

        conditions = []
        if filter_type:
            conditions.append(
                FieldCondition(
                    key="file_type", match=MatchValue(value=filter_type)
                )
            )
        if product:
            conditions.append(
                FieldCondition(
                    key="product", match=MatchValue(value=product)
                )
            )
        if doc_type:
            conditions.append(
                FieldCondition(
                    key="doc_type", match=MatchValue(value=doc_type)
                )
            )
        if version:
            conditions.append(
                FieldCondition(
                    key="version", match=MatchValue(value=version)
                )
            )
        if vendor:  # PHASE 11.1: Vendor filtering
            conditions.append(
                FieldCondition(
                    key="vendor", match=MatchValue(value=vendor)
                )
            )
        if subsystem:  # PHASE 11.1: Subsystem filtering
            conditions.append(
                FieldCondition(
                    key="subsystem", match=MatchValue(value=subsystem)
                )
            )
        if module:  # PHASE 17: Module filtering
            conditions.append(
                FieldCondition(
                    key="module", match=MatchValue(value=module)
                )
            )

        query_filter = Filter(must=conditions) if conditions else None
        indices = list(sparse_vector.keys())
        values = list(sparse_vector.values())
        named_sparse = NamedSparseVector(
            name="sparse",
            vector=SparseVector(indices=indices, values=values),
        )

        try:
            response = await self.client.query_points(
                collection_name=collection_name or self.collection,
                query=named_sparse,
                limit=top_k,
                query_filter=query_filter,
                with_payload=True,
            )
            return [
                {
                    "chunk_id": str(r.id),
                    "score": r.score,
                    "text": r.payload.get("text", ""),
                    "source_file": r.payload.get("source_file", ""),
                    "file_type": r.payload.get("file_type", ""),
                    "vendor": r.payload.get("vendor", ""),  # PHASE 11.1
                    "product": r.payload.get("product", ""),
                    "subsystem": r.payload.get("subsystem", ""),  # PHASE 11.1
                    "doc_type": r.payload.get("doc_type", "document"),
                    "version": r.payload.get("version", ""),  # PHASE 13
                    "page": r.payload.get("page"),
                    "chunk_index": r.payload.get("chunk_index"),
                }
                for r in response.points
            ]
        except Exception as e:
            log.warning(
                "Sparse search failed "
                f"(collection may lack sparse index): {e}"
            )
            return []

    # ── Upsert ───────────────────────────────────────────────────────

    async def upsert_chunks(self, chunks: list[dict]) -> None:
        """Insert or update chunks in Qdrant with efficient batching.

        Each chunk dict must contain: text, vector, source_file, file_type,
        product, chunk_index, and optionally page and chunk_id.
        Supports configurable batch size via QDRANT_BATCH_SIZE.

        Args:
            chunks: List of chunk dicts with vectors and metadata.

        Raises:
            RuntimeError: If the VectorStore client is not connected.
        """
        if self.client is None:
            raise RuntimeError("VectorStore client not connected")
        if not chunks:
            log.warning("upsert_chunks called with empty list")
            return
        
        points = []
        for chunk in chunks:
            cid = chunk.get("chunk_id") or str(uuid.uuid4())
            payload = {k: v for k, v in chunk.items() if k != "vector"}
            payload["chunk_id"] = cid
            points.append(
                PointStruct(id=cid, vector=chunk["vector"], payload=payload)
            )

        # Split into batches and upload
        total_batches = (len(points) + self.batch_size - 1) // self.batch_size
        log.info(
            f"Upserting {len(points)} chunks in {total_batches} batches "
            f"(batch_size={self.batch_size})"
        )
        
        for batch_num, i in enumerate(
            range(0, len(points), self.batch_size), 1
        ):
            batch_points = points[i : i + self.batch_size]
            await self.client.upsert(
                collection_name=self.collection,
                points=batch_points,
            )
            log.debug(
                f"Batch {batch_num}/{total_batches} uploaded "
                f"({len(batch_points)} points)"
            )
        
        log.info(f"Upserted {len(points)} chunks successfully")

    async def delete_document(self, source_file: str) -> None:
        """Delete all chunks belonging to a document by file path.

        Args:
            source_file: Path of the document to remove.

        Raises:
            RuntimeError: If the VectorStore client is not connected.
        """
        if self.client is None:
            raise RuntimeError("VectorStore client not connected")
        await self.client.delete(
            collection_name=self.collection,
            points_selector=qmodels.FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="source_file",
                            match=MatchValue(value=source_file),
                        )
                    ]
                )
            ),
        )
        log.info(f"Document removed: {source_file}")

    # ── Listing ─────────────────────────────────────────────────────

    async def list_documents(
        self,
        filter_type: str | None = None,
        product: str | None = None,
        doc_type: str | None = None,
        vendor: str | None = None,  # PHASE 11.1: Vendor filter
        subsystem: str | None = None,  # PHASE 11.1: Subsystem filter
        module: str | None = None,  # PHASE 17: Module filter
        limit: int = 50,
        collection_name: str | None = None,  # PHASE 15: multi-collection override
    ) -> list[dict]:
        """List indexed documents with optional filtering.

        Uses scroll-based pagination to aggregate chunk counts per document.

        Args:
            filter_type: Optional file type filter (pdf, docx, etc.).
            product: Optional product name filter.
            doc_type: Optional document type filter.
            vendor: Optional vendor name filter (PHASE 11.1).
            subsystem: Optional subsystem name filter (PHASE 11.1).
            module: Optional module name filter (PHASE 17).
            limit: Maximum number of documents to return (default 50).
            collection_name: Override target collection (PHASE 15).

        Returns:
            List of dicts with source_file, file_type, vendor, product,
            subsystem, module, doc_type, and chunk_count.

        Raises:
            RuntimeError: If the VectorStore client is not connected.
        """
        if self.client is None:
            raise RuntimeError("VectorStore client not connected")
        conditions = []
        if filter_type:
            conditions.append(
                FieldCondition(
                    key="file_type", match=MatchValue(value=filter_type)
                )
            )
        if product:
            conditions.append(
                FieldCondition(key="product", match=MatchValue(value=product))
            )
        if doc_type:
            conditions.append(
                FieldCondition(
                    key="doc_type", match=MatchValue(value=doc_type)
                )
            )
        if vendor:  # PHASE 11.1: Vendor filtering
            conditions.append(
                FieldCondition(
                    key="vendor", match=MatchValue(value=vendor)
                )
            )
        if subsystem:  # PHASE 11.1: Subsystem filtering
            conditions.append(
                FieldCondition(
                    key="subsystem", match=MatchValue(value=subsystem)
                )
            )
        if module:  # PHASE 17: Module filtering
            conditions.append(
                FieldCondition(
                    key="module", match=MatchValue(value=module)
                )
            )

        query_filter = Filter(must=conditions) if conditions else None

        docs: dict[str, dict] = {}
        offset = None

        while len(docs) < limit:
            results, offset = await self.client.scroll(
                collection_name=collection_name or self.collection,
                scroll_filter=query_filter,
                limit=500,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for r in results:
                sf = r.payload.get("source_file", "")
                if sf not in docs:
                    docs[sf] = {
                        "source_file": sf,
                        "file_type": r.payload.get("file_type", ""),
                        "vendor": r.payload.get("vendor", ""),  # PHASE 11.1
                        "product": r.payload.get("product", ""),
                        "subsystem": r.payload.get("subsystem", ""),  # PHASE 11.1
                        "module": r.payload.get("module", ""),  # PHASE 17
                        "doc_type": r.payload.get("doc_type", "document"),
                        "version": r.payload.get("version", ""),  # PHASE 13
                        "chunk_count": 0,
                    }
                docs[sf]["chunk_count"] += 1

            if offset is None:
                break

        return list(docs.values())[:limit]

    # ── Chunk by ID ──────────────────────────────────────────────────────────

    async def get_chunk_with_context(
        self, chunk_id: str, context_window: int = 1
    ) -> list[dict]:
        """Return a chunk and its neighbors from the same document.

        Retrieves adjacent chunk indices to provide surrounding context.

        Args:
            chunk_id: ID of the target chunk.
            context_window: Number of neighboring chunks on each side
                to include (default 1, range 0-3).

        Returns:
            List of chunk dicts sorted by chunk_index, or empty list if
            chunk not found.

        Raises:
            RuntimeError: If the VectorStore client is not connected.
        """
        if self.client is None:
            raise RuntimeError("VectorStore client not connected")
        results = await self.client.retrieve(
            collection_name=self.collection,
            ids=[chunk_id],
            with_payload=True,
            with_vectors=False,
        )
        if not results:
            return []

        target = results[0].payload
        source_file = target.get("source_file", "")
        target_index = int(target.get("chunk_index", 0))

        # Search neighboring chunks in the same document
        min_idx = max(0, target_index - context_window)
        max_idx = target_index + context_window

        neighbors, _ = await self.client.scroll(
            collection_name=self.collection,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="source_file", match=MatchValue(value=source_file)
                    )
                ]
            ),
            limit=context_window * 2 + 10,
            with_payload=True,
            with_vectors=False,
        )

        chunks = [
            {
                "chunk_id": str(n.id),
                "text": n.payload.get("text", ""),
                "source_file": n.payload.get("source_file", ""),
                "chunk_index": int(n.payload.get("chunk_index", 0)),
            }
            for n in neighbors
            if min_idx <= int(n.payload.get("chunk_index", 0)) <= max_idx
        ]
        chunks.sort(key=lambda c: c["chunk_index"])
        return chunks

    # ── Terms Table (Phase 17) ─────────────────────────────────────────

    async def get_distinct_values(
        self,
        field: str,
        top_n: int = 0,
        with_counts: bool = False,
        collection_name: str | None = None,
    ) -> list[str] | list[dict]:
        """Get distinct values for a payload field across a collection.

        PHASE 17: Used by FilterTermsCache to build the terms table.

        Args:
            field: Qdrant payload field name.
            top_n: If > 0, return only the top N most frequent values.
            with_counts: If True, return list of {value, count} dicts.
            collection_name: Target collection (default: self.collection).

        Returns:
            List of distinct values (strings) or list of {value, count} dicts.
        """
        col = collection_name or self.collection
        if not col or not self.client:
            return []

        try:
            all_values: dict[str, int] = {}
            next_offset = None
            limit = 100

            while True:
                records, next_offset = await self.client.scroll(
                    collection_name=col,
                    limit=limit,
                    offset=next_offset,
                    with_payload=[field],
                    with_vectors=False,
                )
                for record in records:
                    val = record.payload.get(field)
                    if val and isinstance(val, str) and val.strip():
                        all_values[val] = all_values.get(val, 0) + 1

                if next_offset is None:
                    break

            if not all_values:
                return []

            sorted_vals = sorted(
                all_values.items(),
                key=lambda x: (-x[1], x[0]),
            )

            if top_n > 0:
                sorted_vals = sorted_vals[:top_n]

            if with_counts:
                return [
                    {"value": val, "count": count}
                    for val, count in sorted_vals
                ]
            return [val for val, _ in sorted_vals]

        except Exception as e:
            log.error(f"Failed to get distinct values for '{field}': {e}")
            return []

    # ── Stats ─────────────────────────────────────────────────────────

    async def get_stats(self) -> dict:
        """Return collection statistics.

        Queries Qdrant for point count, documents, embedding model info,
        and breakdowns by file type and document type.

        Returns:
            Dict with total_chunks, total_documents, index_size_mb,
            embed_model, embed_backend, embed_dim, by_file_type,
            and by_doc_type.

        Raises:
            RuntimeError: If the VectorStore client is not connected.
        """
        if self.client is None:
            raise RuntimeError("VectorStore client not connected")
        info = await self.client.get_collection(self.collection)
        count = info.points_count or 0

        # Sample to count by type
        sample, _ = await self.client.scroll(
            collection_name=self.collection,
            limit=1000,
            with_payload=["file_type", "source_file", "doc_type"],
            with_vectors=False,
        )
        by_type: dict[str, set] = {}
        by_doc_type: dict[str, set] = {}
        for r in sample:
            ft = r.payload.get("file_type", "unknown")
            dt = r.payload.get("doc_type", "document")
            sf = r.payload.get("source_file", "")
            by_type.setdefault(ft, set()).add(sf)
            by_doc_type.setdefault(dt, set()).add(sf)

        from kb_server.embed_client import BACKEND, MODEL

        return {
            "total_chunks": count,
            "total_documents": len(
                {r.payload.get("source_file") for r in sample}
            ),
            "index_size_mb": count * self.dim * 4 / 1024 / 1024,
            "embed_model": MODEL,
            "embed_backend": BACKEND,
            "embed_dim": self.dim,
            "by_file_type": {k: len(v) for k, v in by_type.items()},
            "by_doc_type": {k: len(v) for k, v in by_doc_type.items()},
        }

    # ── PHASE 8: Parallel batch operations ───────────────────────────

    async def upsert_chunks_parallel(
        self, chunks: list[dict], max_parallel: int = 3
    ) -> None:
        """
        PHASE 8: Parallel batch upsert for maximum throughput.
        
        Splits chunks into batches and uploads multiple batches in parallel.
        Use this for large ingestion jobs (>1000 chunks).
        
        Args:
            chunks: List of chunk dicts with vectors and metadata
            max_parallel: Maximum parallel batch uploads (default 3)
        """
        if not chunks:
            return
        
        if self.client is None:
            raise RuntimeError("VectorStore client not connected")
        
        points = []
        for chunk in chunks:
            cid = chunk.get("chunk_id") or str(uuid.uuid4())
            payload = {k: v for k, v in chunk.items() if k != "vector"}
            payload["chunk_id"] = cid
            points.append(
                PointStruct(id=cid, vector=chunk["vector"], payload=payload)
            )
        
        # Split into batches
        batches = [
            points[i : i + self.batch_size]
            for i in range(0, len(points), self.batch_size)
        ]
        
        log.info(
            f"Parallel upsert: {len(points)} chunks in {len(batches)} "
            f"batches (max_parallel={max_parallel})"
        )
        
        # Upload batches in parallel (with limit)
        import asyncio
        
        async def upload_batch(batch_num: int, batch: list) -> None:
            """Upload a single batch of points to Qdrant.

            Args:
                batch_num: Batch number (for logging).
                batch: List of PointStruct points to upload.
            """
            await self.client.upsert(
                collection_name=self.collection,
                points=batch,
            )
            log.debug(
                f"Parallel batch {batch_num}/{len(batches)} uploaded "
                f"({len(batch)} points)"
            )
        
        # Process in chunks of max_parallel
        for i in range(0, len(batches), max_parallel):
            parallel_batches = batches[i : i + max_parallel]
            await asyncio.gather(
                *[
                    upload_batch(i + j + 1, batch)
                    for j, batch in enumerate(parallel_batches)
                ]
            )
        
        log.info(f"Parallel upsert complete: {len(points)} chunks")

    # ── Phase 16: Reclassification metadata update ──────────────────────

    async def update_chunk_metadata(
        self,
        collection_name: str,
        source_file: str,
        updates: dict[str, str],
        chunk_index: int | None = None,
    ) -> int:
        """
        Update metadata fields for chunks in-place without re-embedding.

        Preserves existing vectors and chunk text while updating only
        specified metadata fields in the Qdrant payload. Used for
        reclassification when classification logic improves.

        Args:
            collection_name: Qdrant collection name.
            source_file: Source file path to filter chunks.
            updates: Dict of field_name -> new_value to update.
            chunk_index: Optional specific chunk index (updates single chunk).

        Returns:
            Number of chunks updated.

        Raises:
            RuntimeError: If VectorStore client is not connected.
            QdrantException: If Qdrant update fails.
        """
        if self.client is None:
            raise RuntimeError("VectorStore client not connected")

        log.info(
            f"Updating metadata for {source_file} in {collection_name}"
        )

        # Build filter
        must_conditions = [
            FieldCondition(
                key="source_file", match=MatchValue(value=source_file)
            )
        ]
        if chunk_index is not None:
            must_conditions.append(
                FieldCondition(
                    key="chunk_index", match=MatchValue(value=chunk_index)
                )
            )

        filter_query = Filter(must=must_conditions)

        # Scroll to get point IDs
        points, _ = await self.client.scroll(
            collection_name=collection_name,
            scroll_filter=filter_query,
            limit=10000,  # max chunks per document
            with_payload=False,
            with_vectors=False,
        )

        if not points:
            log.warning(f"No chunks found for {source_file}")
            return 0

        point_ids = [p.id for p in points]

        # Update payload
        await self.client.set_payload(
            collection_name=collection_name,
            payload=updates,
            points=point_ids,
        )

        log.info(f"Updated {len(point_ids)} chunks for {source_file}")
        return len(point_ids)

    async def close(self) -> None:
        """
        PHASE 8: Cleanup Qdrant client connections.
        
        Call on server shutdown for graceful cleanup.
        """
        if self.client is not None:
            await self.client.close()
            self.client = None
            log.info("Qdrant client closed")
