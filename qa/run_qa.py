import argparse
import os
import json
import asyncio
import logging
from pathlib import Path

# Load .env FIRST — before any kb_server import reads env vars at module level
from config.bootstrap_env import bootstrap_env
bootstrap_env()

# IMPORTANT: Import kb_server package AFTER .env is loaded, and before any
# mcp imports, to prevent mcp's 'server' submodule from shadowing ours.
import kb_server  # noqa: F401 - must be before mcp

from kb_server.vector_store import VectorStore as _VS  # warm up kb_server package

from qa.embedder import Embedder
from qa.metrics import compute_all
from qa.report import render_report

def parse_args():
    parser = argparse.ArgumentParser(description="Run KB QA pipeline end-to-end.")
    parser.add_argument("--docs-path", type=str, help="Path to docs root (for ingest)")
    parser.add_argument("--workers", type=int, default=4, help="Number of ingest workers to use")
    parser.add_argument("--eval", action="store_true", help="Run only QA eval (skip ingestion)")
    parser.add_argument("--output", type=str, default="QA_REPORT.md", help="Report output path")
    return parser.parse_args()

async def run_ingest_stage(docs_path, workers):
    from ingest.ingest import run_ingest
    os.environ["QDRANT_COLLECTION"] = "qa_otcs"
    print(f"Ingesting documents from {docs_path} ...")
    await run_ingest(Path(docs_path), "default", workers, clean=True, force=True)
    print("Ingestion complete.")

async def run_probe_and_metrics():
    # 1. Load queries
    with open("qa/queries.json", "r", encoding="utf-8") as f:
        queries = json.load(f)
    questions = [q["question"] for q in queries]
    golden_answers = [q["answer_chunk_id"] for q in queries]

    # 2. Embed questions in a batch (async, uses same backend as production)
    embedder = Embedder()
    question_vectors = await embedder.aembed_batch(questions)

    # 3. Connect to vector store
    #    Use QDRANT_COLLECTION env if set; fall back to kb_docs (production collection).
    from kb_server.vector_store import VectorStore
    if "QDRANT_COLLECTION" not in os.environ:
        os.environ["QDRANT_COLLECTION"] = "kb_docs"
    store = VectorStore()
    await store.connect()

    # 4. Run async searches for each query
    retrieved_results = []
    score_lists = []
    for vec in question_vectors:
        hits = await store.search(vec, top_k=10)
        retrieved_results.append([h["chunk_id"] for h in hits])
        score_lists.append([h.get("score", 0.0) for h in hits])

    # 5. Compute metrics
    metrics = compute_all(retrieved_results, golden_answers, score_lists)

    # 6. Render markdown report
    md = render_report(metrics)
    return md, metrics, queries, retrieved_results, golden_answers

async def run_pipeline(args):
    try:
        if not args.eval:
            await run_ingest_stage(args.docs_path, args.workers)
        report_md, metrics, queries, retrieved_results, golden_answers = await run_probe_and_metrics()
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report_md)
        # Save/update golden dataset
        golden_entries = [
            {"question": q["question"], "answer_chunk_id": g, "retrieved_chunk_ids": r}
            for q, g, r in zip(queries, golden_answers, retrieved_results)
        ]
        with open("kb_server/evaluation/golden_dataset.json", "w", encoding="utf-8") as f:
            json.dump(golden_entries, f, indent=2)
        print(f"\nReport written to {args.output}")
        print("Golden dataset updated at kb_server/evaluation/golden_dataset.json")
    except Exception as e:
        logging.exception("Fatal error in QA pipeline:")
        print(f"[ERROR] {e}")
        exit(1)

def main():
    args = parse_args()
    asyncio.run(run_pipeline(args))

if __name__ == "__main__":
    main()
