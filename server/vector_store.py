"""
Vector Store — abstração sobre Qdrant.
Gerencia coleções, busca semântica, filtros e metadados.
"""

import logging
import os
import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
    QueryRequest,
)
from qdrant_client import models as qmodels

from embed_client import get_embed_dim

log = logging.getLogger("kb-mcp.store")

# ── Config ────────────────────────────────────────────────────────────────────
QDRANT_HOST       = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT       = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_PATH       = os.getenv("QDRANT_PATH", "")          # se definido, usa modo embedded
COLLECTION_NAME   = os.getenv("QDRANT_COLLECTION", "kb_docs")
SCORE_THRESHOLD   = float(os.getenv("SCORE_THRESHOLD", "0.35"))


class VectorStore:
    def __init__(self):
        self.client: AsyncQdrantClient | None = None
        self.collection = COLLECTION_NAME
        self.dim = get_embed_dim()

    async def connect(self):
        """Conecta ao Qdrant (embedded ou servidor)."""
        if QDRANT_PATH:
            log.info(f"Qdrant embedded em: {QDRANT_PATH}")
            self.client = AsyncQdrantClient(path=QDRANT_PATH)
        else:
            log.info(f"Qdrant server em: {QDRANT_HOST}:{QDRANT_PORT}")
            self.client = AsyncQdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        await self._ensure_collection()
        log.info(f"Conectado ao Qdrant — coleção: {self.collection}")

    async def _ensure_collection(self):
        """Cria a coleção se não existir."""
        existing = [c.name for c in (await self.client.get_collections()).collections]
        if self.collection not in existing:
            await self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
            )
            log.info(f"Coleção '{self.collection}' criada (dim={self.dim})")

    # ── Busca ─────────────────────────────────────────────────────────────────

    async def search(
        self,
        vector: list[float],
        top_k: int = 5,
        filter_type: str | None = None,
        product: str | None = None,
        doc_type: str | None = None,
    ) -> list[dict]:
        """Busca semântica com filtros opcionais por file_type, product e doc_type."""
        conditions = []
        if filter_type:
            conditions.append(FieldCondition(key="file_type", match=MatchValue(value=filter_type)))
        if product:
            conditions.append(FieldCondition(key="product",   match=MatchValue(value=product)))
        if doc_type:
            conditions.append(FieldCondition(key="doc_type",  match=MatchValue(value=doc_type)))

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
                "chunk_id":    str(r.id),
                "score":       r.score,
                "text":        r.payload.get("text", ""),
                "source_file": r.payload.get("source_file", ""),
                "file_type":   r.payload.get("file_type", ""),
                "product":     r.payload.get("product", ""),
                "doc_type":    r.payload.get("doc_type", "document"),
                "page":        r.payload.get("page"),
                "chunk_index": r.payload.get("chunk_index", 0),
            }
            for r in response.points
        ]

    # ── Upsert ───────────────────────────────────────────────────────────────

    async def upsert_chunks(self, chunks: list[dict]):
        """
        Insere ou atualiza chunks no Qdrant.
        Cada chunk deve ter: text, vector, source_file, file_type, product,
                             chunk_index, page (opcional), chunk_id (opcional).
        """
        points = []
        for chunk in chunks:
            cid = chunk.get("chunk_id") or str(uuid.uuid4())
            payload = {k: v for k, v in chunk.items() if k != "vector"}
            payload["chunk_id"] = cid
            points.append(PointStruct(id=cid, vector=chunk["vector"], payload=payload))

        # Qdrant aceita no máximo 100 pontos por upsert
        batch_size = 100
        for i in range(0, len(points), batch_size):
            await self.client.upsert(
                collection_name=self.collection,
                points=points[i:i + batch_size],
            )
        log.info(f"Upserted {len(points)} chunks")

    async def delete_document(self, source_file: str):
        """Remove todos os chunks de um documento pelo caminho do arquivo."""
        await self.client.delete(
            collection_name=self.collection,
            points_selector=qmodels.FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="source_file", match=MatchValue(value=source_file))]
                )
            ),
        )
        log.info(f"Documento removido: {source_file}")

    # ── Listagem ──────────────────────────────────────────────────────────────

    async def list_documents(
        self,
        filter_type: str | None = None,
        product: str | None = None,
        doc_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Lista documentos únicos indexados, agrupados por source_file."""
        conditions = []
        if filter_type:
            conditions.append(FieldCondition(key="file_type", match=MatchValue(value=filter_type)))
        if product:
            conditions.append(FieldCondition(key="product",   match=MatchValue(value=product)))
        if doc_type:
            conditions.append(FieldCondition(key="doc_type",  match=MatchValue(value=doc_type)))

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
                        "file_type":   r.payload.get("file_type", ""),
                        "product":     r.payload.get("product", ""),
                        "doc_type":    r.payload.get("doc_type", "document"),
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
        """Retorna um chunk e seus vizinhos (mesmo documento, índices adjacentes)."""
        results = await self.client.retrieve(
            collection_name=self.collection,
            ids=[chunk_id],
            with_payload=True,
            with_vectors=False,
        )
        if not results:
            return []

        target = results[0].payload
        source_file  = target.get("source_file", "")
        target_index = int(target.get("chunk_index", 0))

        # Busca chunks vizinhos no mesmo documento
        min_idx = max(0, target_index - context_window)
        max_idx = target_index + context_window

        neighbors, _ = await self.client.scroll(
            collection_name=self.collection,
            scroll_filter=Filter(
                must=[FieldCondition(key="source_file", match=MatchValue(value=source_file))]
            ),
            limit=context_window * 2 + 10,
            with_payload=True,
            with_vectors=False,
        )

        chunks = [
            {
                "chunk_id":    str(n.id),
                "text":        n.payload.get("text", ""),
                "source_file": n.payload.get("source_file", ""),
                "chunk_index": int(n.payload.get("chunk_index", 0)),
            }
            for n in neighbors
            if min_idx <= int(n.payload.get("chunk_index", 0)) <= max_idx
        ]
        chunks.sort(key=lambda c: c["chunk_index"])
        return chunks

    # ── Stats ─────────────────────────────────────────────────────────────────

    async def get_stats(self) -> dict:
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
            "total_chunks":    count,
            "total_documents": len({r.payload.get("source_file") for r in sample}),
            "index_size_mb":   count * self.dim * 4 / 1024 / 1024,
            "embed_model":     MODEL,
            "embed_backend":   BACKEND,
            "embed_dim":       self.dim,
            "by_file_type":    {k: len(v) for k, v in by_type.items()},
            "by_doc_type":     {k: len(v) for k, v in by_doc_type.items()},
        }
