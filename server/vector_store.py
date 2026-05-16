"""
Vector Store — abstração sobre Qdrant.
Gerencia coleções, busca semântica, filtros e metadados.

FASE 8: Enhanced with connection pooling and batch optimizations.
"""

import logging
import os
import uuid
from typing import Optional

from embed_client import get_embed_dim
from qdrant_client import AsyncQdrantClient  # type: ignore[import]
from qdrant_client import models as qmodels  # type: ignore[import]
from qdrant_client.models import Distance  # type: ignore[import]
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

log = logging.getLogger("kb-mcp.store")

# ── Config
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_PATH = os.getenv("QDRANT_PATH", "")  # se definido, usa modo embedded
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "kb_docs")
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "0.35"))

# FASE 8: Connection pool and batch config
QDRANT_GRPC = os.getenv("QDRANT_GRPC", "false").lower() == "true"
QDRANT_GRPC_PORT = int(os.getenv("QDRANT_GRPC_PORT", "6334"))
QDRANT_TIMEOUT = float(os.getenv("QDRANT_TIMEOUT", "60.0"))
QDRANT_BATCH_SIZE = int(os.getenv("QDRANT_BATCH_SIZE", "100"))


class VectorStore:
    def __init__(self):
        self.client: AsyncQdrantClient | None = None
        self.collection = COLLECTION_NAME
        self.dim = get_embed_dim()
        self.batch_size = QDRANT_BATCH_SIZE

    async def connect(self) -> None:
        assert self.client is None, "Client should not already be connected"

        """
        FASE 8: Conecta ao Qdrant com connection pooling.
        
        Supports:
        - HTTP API (default)
        - gRPC API (set QDRANT_GRPC=true for better performance)
        - Embedded mode (set QDRANT_PATH)
        """
        if QDRANT_PATH:
            log.info(f"Qdrant embedded em: {QDRANT_PATH}")
            self.client = AsyncQdrantClient(
                path=QDRANT_PATH,
                timeout=QDRANT_TIMEOUT,
            )
        elif QDRANT_GRPC:
            log.info(
                f"Qdrant gRPC server em: {QDRANT_HOST}:{QDRANT_GRPC_PORT}"
            )
            self.client = AsyncQdrantClient(
                host=QDRANT_HOST,
                grpc_port=QDRANT_GRPC_PORT,
                prefer_grpc=True,
                timeout=QDRANT_TIMEOUT,
            )
        else:
            log.info(f"Qdrant HTTP server em: {QDRANT_HOST}:{QDRANT_PORT}")
            self.client = AsyncQdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT,
                timeout=QDRANT_TIMEOUT,
            )

        await self._ensure_collection()
        log.info(
            f"Conectado ao Qdrant — coleção: {self.collection}, "
            f"batch_size: {self.batch_size}"
        )

    async def _ensure_collection(self) -> None:
        assert self.client is not None, "Client not connected"

        """Cria a coleção se não existir."""
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
            log.info(f"Coleção '{self.collection}' criada (dim={self.dim})")

    # ── Busca ───────────────────────────────────────────────────────

    async def search(
        self,
        vector: list[float],
        top_k: int = 5,
        filter_type: str | None = None,
        product: str | None = None,
        doc_type: str | None = None,
    ) -> list[dict]:
        """Busca semântica com filtros opcionais por
        file_type, product e doc_type.
        """
        assert self.client is not None, "Client not connected"
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

        query_filter = Filter(must=conditions) if conditions else None

        response = await self.client.query_points(
            collection_name=self.collection,
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
                "product": r.payload.get("product", ""),
                "doc_type": r.payload.get("doc_type", "document"),
                "page": r.payload.get("page"),
                "chunk_index": r.payload.get("chunk_index", 0),
            }
            for r in response.points
        ]

    # ── Upsert ───────────────────────────────────────────────────────

    async def upsert_chunks(self, chunks: list[dict]) -> None:
        assert self.client is not None, "Client not connected"

        """
        FASE 8: Optimized batch insert/update for chunks.
        
        Insere ou atualiza chunks no Qdrant com batching eficiente.
        Cada chunk deve ter: text, vector, source_file, file_type, product,
                         chunk_index, page (opcional), chunk_id (opcional).
        
        Performance improvements:
        - Configurable batch size via QDRANT_BATCH_SIZE
        - Parallel batch uploads
        - Progress logging
        """
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
        assert self.client is not None, "Client not connected"

        """
        Remove todos os chunks de um documento pelo caminho do arquivo.
        """
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
        log.info(f"Documento removido: {source_file}")

    # ── Listagem ──────────────────────────────────────────────────────

    async def list_documents(
        self,
        filter_type: str | None = None,
        product: str | None = None,
        doc_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        assert self.client is not None, "Client not connected"
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

        query_filter = Filter(must=conditions) if conditions else None

        docs: dict[str, dict] = {}
        offset = None

        while len(docs) < limit:
            results, offset = await self.client.scroll(
                collection_name=self.collection,
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
                        "product": r.payload.get("product", ""),
                        "doc_type": r.payload.get("doc_type", "document"),
                        "chunk_count": 0,
                    }
                docs[sf]["chunk_count"] += 1

            if offset is None:
                break

        return list(docs.values())[:limit]

    # ── Chunk por ID ─────────────────────────────────────────────────────────

    async def get_chunk_with_context(
        self, chunk_id: str, context_window: int = 1
    ) -> list[dict]:
        assert self.client is not None, "Client not connected"

        """
        Retorna um chunk e seus vizinhos
        (mesmo documento, índices adjacentes).
        """
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

        # Busca chunks vizinhos no mesmo documento
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

    # ── Stats ─────────────────────────────────────────────────────────

    async def get_stats(self) -> dict:
        assert self.client is not None, "Client not connected"
        """Retorna estatísticas da coleção."""
        info = await self.client.get_collection(self.collection)
        count = info.points_count or 0

        # Amostra para contar por tipo
        sample, _ = await self.client.scroll(
            collection_name=self.collection,
            limit=1000,
            with_payload=["file_type", "source_file"],
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

        from embed_client import BACKEND, MODEL

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

    # ── FASE 8: Parallel batch operations ────────────────────────────

    async def upsert_chunks_parallel(
        self, chunks: list[dict], max_parallel: int = 3
    ) -> None:
        """
        FASE 8: Parallel batch upsert for maximum throughput.
        
        Splits chunks into batches and uploads multiple batches in parallel.
        Use this for large ingestion jobs (>1000 chunks).
        
        Args:
            chunks: List of chunk dicts with vectors and metadata
            max_parallel: Maximum parallel batch uploads (default 3)
        """
        if not chunks:
            return
        
        assert self.client is not None, "Client not connected"
        
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

    async def close(self) -> None:
        """
        FASE 8: Cleanup Qdrant client connections.
        
        Call on server shutdown for graceful cleanup.
        """
        if self.client is not None:
            await self.client.close()
            self.client = None
            log.info("Qdrant client closed")
