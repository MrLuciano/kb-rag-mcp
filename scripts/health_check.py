#!/usr/bin/env python3
"""
health_check.py — Verifica se todos os componentes estão funcionando.
Execute antes de ligar o MCP server.

    python scripts/health_check.py
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# ── Carrega .env ANTES de qualquer import que leia os.getenv ─────────
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root / "server"))

_env_file = _project_root / ".env"
if _env_file.exists():
    load_dotenv(_env_file, override=True)
else:
    print(f"[WARN] .env não encontrado em {_env_file}", file=sys.stderr)


async def check_embedding():
    print("\n[1/3] Testando embedding backend...")
    from embed_client import (
        BACKEND,
        LMS_BASE_URL,
        LMS_HOST,
        LMS_PORT,
        MODEL,
        health_check,
    )

    print(f"  Backend : {BACKEND}")
    print(f"  Modelo  : {MODEL}")
    if BACKEND in ("lmstudio-sdk", "lmstudio-rest", "openai-compat"):
        print(f"  URL base: {LMS_BASE_URL}  (normalizada de LMS_BASE_URL)")
        if BACKEND == "openai-compat":
            print(f"  Endpoint: {LMS_BASE_URL}/v1/embeddings")
        elif BACKEND == "lmstudio-rest":
            print(f"  Endpoint: {LMS_BASE_URL}/api/v0/embeddings")
        elif BACKEND == "lmstudio-sdk":
            print(f"  WS host : {LMS_HOST}:{LMS_PORT}")
    result = await health_check()
    if result["status"] == "ok":
        print(f"  ✓ Embedding OK — {result['dims']} dimensões")
        return True
    else:
        print(f"  ✗ Embedding FALHOU: {result['error']}")
        print()
        print("  Dicas de diagnóstico:")
        if BACKEND == "openai-compat":
            print(f"    curl http://{LMS_HOST}:{LMS_PORT}/v1/embeddings \\")
            print("      -H 'Content-Type: application/json' \\")
            print(f'      -d \'{{"model":"{MODEL}","input":["test"]}}\'')
        elif BACKEND == "lmstudio-rest":
            print(
                f"    curl http://{LMS_HOST}:{LMS_PORT}"
                "/api/v0/embeddings \\"
            )
            print("      -H 'Content-Type: application/json' \\")
            print(f'      -d \'{{"model":"{MODEL}","input":"test"}}\'')
        print()
        print("  Variáveis no .env:")
        print(
            "    EMBED_BACKEND=openai-compat  "
            "← recomendado para LM Studio remoto"
        )
        print(
            "    LMS_BASE_URL=http://<ip>:1234  "
            "← SEM /v1 ou /api/v0 no final"
        )
        print("    EMBED_MODEL=<nome exato do modelo no LM Studio>")
        return False


async def check_qdrant():
    print("\n[2/3] Testando conexão com Qdrant...")
    from vector_store import (
        QDRANT_HOST,
        QDRANT_PATH,
        QDRANT_PORT,
        VectorStore,
    )

    if QDRANT_PATH:
        print(f"  Modo: embedded em {QDRANT_PATH}")
    else:
        print(f"  Modo: server em {QDRANT_HOST}:{QDRANT_PORT}")
    try:
        store = VectorStore()
        await store.connect()
        stats = await store.get_stats()
        print(f"  ✓ Qdrant OK — {stats['total_chunks']} chunks indexados")
        return True, store
    except Exception as e:
        print(f"  ✗ Qdrant FALHOU: {e}")
        return False, None


async def check_search(store):
    print("\n[3/3] Testando busca semântica...")
    from embed_client import get_embedding

    try:
        vec = await get_embedding("teste de busca")
        results = await store.search(vec, top_k=3)
        if results:
            print(f"  ✓ Busca OK — {len(results)} resultados")
            print(
                f"  Top resultado: {results[0]['source_file']} "
                f"(score: {results[0]['score']:.2f})"
            )
        else:
            print("  ⚠ Busca OK mas sem resultados (KB vazia?)")
        return True
    except Exception as e:
        print(f"  ✗ Busca FALHOU: {e}")
        return False


async def main():
    print("=" * 50)
    print(" KB RAG — Health Check")
    print("=" * 50)

    ok_embed = await check_embedding()
    ok_qdrant, store = await check_qdrant()
    ok_search = (
        await check_search(store) if (ok_embed and ok_qdrant) else False
    )

    print("\n" + "=" * 50)
    all_ok = ok_embed and ok_qdrant and ok_search
    if all_ok:
        print(" ✓ Todos os componentes OK — pronto para iniciar o servidor!")
    else:
        print(" ✗ Alguns componentes falharam. Verifique as mensagens acima.")
    print("=" * 50)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
