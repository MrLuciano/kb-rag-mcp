#!/usr/bin/env python3
"""Benchmark PDF extractors — pre-loads models, single pass."""

import time
from pathlib import Path

FIXTURES = sorted(Path("qa/fixtures").glob("*.pdf"))
RUNS = 2


def main():
    # Pre-load all models once
    print("Pre-loading models...", flush=True)

    import fitz
    fitz.open(str(FIXTURES[0])).close()

    import pymupdf4llm
    pymupdf4llm.to_markdown(str(FIXTURES[0]))
    print("  PyMuPDF4LLM: OK", flush=True)

    from docling.document_converter import DocumentConverter
    conv = DocumentConverter()
    conv.convert(str(FIXTURES[0]))
    print("  docling: OK", flush=True)

    extractors = {
        "PyMuPDF": lambda p: _pymupdf(p),
        "4LLM": lambda p: _pymupdf4llm(p),
        "docling": lambda p: _docling(p, conv),
    }

    print(f"\n{'Extractor':<10} {'PDF':<52} {'Pg':>3} {'Time':>8} {'Chars':>7} {'ms/pg':>7}")
    print("-" * 90)

    totals = {n: {"t": 0.0, "c": 0, "p": 0} for n in extractors}

    for pdf in FIXTURES:
        d = fitz.open(str(pdf))
        n_pages = d.page_count
        d.close()

        for name, fn in extractors.items():
            times = []
            chars = 0
            for _ in range(RUNS):
                t0 = time.perf_counter()
                c, _ = fn(pdf)
                t = time.perf_counter() - t0
                times.append(t)
                chars = c

            avg = sum(times) / len(times)
            mpp = avg / n_pages * 1000
            label = f"{avg*1000:>7.0f}ms" if avg < 10 else f"{avg:>7.2f}s"
            print(f"{name:<10} {pdf.name:<52} {n_pages:>3} {label} {chars:>7} {mpp:>6.0f}")
            totals[name]["t"] += avg
            totals[name]["c"] += chars
            totals[name]["p"] += n_pages

    print("-" * 90)
    base_t = totals["PyMuPDF"]["t"]
    for name in sorted(extractors):
        t = totals[name]
        if t["p"] == 0:
            continue
        ratio = t["t"] / base_t if base_t > 0 else 1
        label = f"{t['t']*1000:>7.0f}ms" if t['t'] < 10 else f"{t['t']:>7.2f}s"
        print(f"{name:<10} {'TOTAL':<52} {t['p']:>3} {label} {t['c']:>7}  {ratio:.1f}× baseline")


def _pymupdf(path):
    import fitz
    doc = fitz.open(str(path))
    parts = []
    for page in doc:
        t = page.get_text("text").strip()
        if t:
            parts.append(t)
    doc.close()
    return len("".join(parts)), None


def _pymupdf4llm(path):
    import pymupdf4llm
    chunks = pymupdf4llm.to_markdown(str(path), page_chunks=True)
    text = "\n\n".join(c["text"] for c in chunks)
    return len(text), None


def _docling(path, conv):
    r = conv.convert(str(path))
    text = r.document.export_to_markdown()
    return len(text), None


if __name__ == "__main__":
    main()
