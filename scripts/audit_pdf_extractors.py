"""Audit PDF extraction: measure docling success rate vs PyMuPDF fallback.

Usage:
    python scripts/audit_pdf_extractors.py /path/to/pdf/dir [options]

Outputs:
    - audit_report.json     Full per-file results
    - audit_summary.txt     Human-readable summary
"""

import argparse
import csv
import json
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("audit")


def try_docling(path: Path) -> tuple[bool, float, str]:
    """Try extracting with docling. Returns (success, duration_seconds, note).

    Uses a singleton DocumentConverter with GPU acceleration — models are
    loaded once and reused across all files.
    """
    try:
        from ingest.docling_utils import get_docling_converter

        converter = get_docling_converter()
        if converter is None:
            return False, 0.0, "docling_not_installed"

        start = time.monotonic()
        result = converter.convert(str(path))
        text = result.document.export_to_markdown()
        elapsed = time.monotonic() - start
        if text and text.strip():
            return True, elapsed, "ok"
        return True, elapsed, "empty_output"
    except ImportError:
        return False, 0.0, "docling_not_installed"
    except Exception as exc:
        return False, 0.0, f"error: {exc}"


def try_pymupdf(path: Path) -> tuple[bool, float, str, int]:
    """Try extracting with PyMuPDF. Returns (success, duration_seconds, note, pages)."""
    try:
        import fitz

        start = time.monotonic()
        doc = fitz.open(str(path))
        page_count = 0
        for page in doc:
            text = page.get_text("text").strip()
            if text:
                page_count += 1
        doc.close()
        elapsed = time.monotonic() - start
        return True, elapsed, "ok", page_count
    except ImportError:
        return False, 0.0, "pymupdf_not_installed", 0
    except Exception as exc:
        return False, 0.0, f"error: {exc}", 0


def collect_pdfs(root: Path, recursive: bool, max_files: int) -> list[Path]:
    if root.is_file():
        return [root]
    pattern = "**/*.pdf" if recursive else "*.pdf"
    files = sorted(root.glob(pattern))
    if max_files:
        files = files[:max_files]
    return files


def main():
    parser = argparse.ArgumentParser(
        description="Audit PDF extraction fallback rate between docling and PyMuPDF"
    )
    parser.add_argument("path", type=str, help="PDF file or directory of PDFs")
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="Search directories recursively"
    )
    parser.add_argument(
        "-n", "--max-files", type=int, default=0, help="Limit number of PDFs to process"
    )
    parser.add_argument(
        "--csv", type=str, default="", help="Write per-file results to CSV file"
    )
    args = parser.parse_args()

    root = Path(args.path)
    if not root.exists():
        log.error("Path does not exist: %s", root)
        sys.exit(1)

    pdfs = collect_pdfs(root, args.recursive, args.max_files)
    if not pdfs:
        log.error("No PDF files found at %s", root)
        sys.exit(1)

    log.info("Found %d PDF(s). Processing...", len(pdfs))

    results = []
    docling_count = 0
    pymupdf_count = 0
    both_failed = 0
    docling_time_total = 0.0
    pymupdf_time_total = 0.0

    for i, pdf in enumerate(pdfs, 1):
        fsize = pdf.stat().st_size
        log.info("[%d/%d] %s (%.1f MB)", i, len(pdfs), pdf.name, fsize / 1e6)

        d_ok, d_time, d_note = try_docling(pdf)
        docling_time_total += d_time

        if d_ok:
            docling_count += 1
            pymupdf_note = "not_tried"
            p_ok = None
            p_time = 0.0
            p_pages = 0
        else:
            p_ok, p_time, p_note, p_pages = try_pymupdf(pdf)
            pymupdf_time_total += p_time
            if p_ok:
                pymupdf_count += 1
            else:
                both_failed += 1

        entry = {
            "file": str(pdf),
            "size_bytes": fsize,
            "docling_ok": d_ok,
            "docling_time_s": round(d_time, 3),
            "docling_note": d_note,
            "pymupdf_ok": p_ok,
            "pymupdf_time_s": round(p_time, 3),
            "pymupdf_note": p_note if p_ok is not None else pymupdf_note,
            "pymupdf_nonempty_pages": p_pages if p_ok else 0,
            "fallback_used": not d_ok and p_ok,
            "both_failed": not d_ok and not p_ok,
        }
        results.append(entry)

        status = "  docling OK"
        if not d_ok:
            if p_ok:
                status = f"  docling FAILED → pymupdf OK ({d_note})"
            else:
                status = f"  BOTH FAILED (docling: {d_note}, pymupdf: {p_note})"
        log.info(status)

    n = len(pdfs)
    fallback_rate = (pymupdf_count / n * 100) if n else 0.0
    docling_rate = (docling_count / n * 100) if n else 0.0
    both_failed_rate = (both_failed / n * 100) if n else 0.0
    avg_docling_time = (docling_time_total / docling_count) if docling_count else 0.0
    avg_pymupdf_time = (pymupdf_time_total / pymupdf_count) if pymupdf_count else 0.0

    summary = {
        "total_pdfs": n,
        "docling_success": docling_count,
        "docling_success_pct": round(docling_rate, 1),
        "docling_avg_time_s": round(avg_docling_time, 3),
        "fallback_pymupdf_success": pymupdf_count,
        "fallback_pymupdf_pct": round(fallback_rate, 1),
        "pymupdf_avg_time_s": round(avg_pymupdf_time, 3) if pymupdf_count else None,
        "both_failed": both_failed,
        "both_failed_pct": round(both_failed_rate, 1),
        "docling_not_installed": any(
            r["docling_note"] == "docling_not_installed" for r in results
        ),
        "pymupdf_not_installed": any(
            r.get("pymupdf_note") == "pymupdf_not_installed" for r in results
        ),
    }

    report = {"summary": summary, "files": results}

    out_dir = Path.cwd()
    with open(out_dir / "audit_report.json", "w") as f:
        json.dump(report, f, indent=2)
    log.info("Full report written to audit_report.json")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader()
            w.writerows(results)
        log.info("CSV written to %s", args.csv)

    lines = [
        "=" * 60,
        "PDF EXTRACTION AUDIT SUMMARY",
        "=" * 60,
        f"  Total PDFs processed:      {summary['total_pdfs']}",
        f"  docling success:           {summary['docling_success']} ({summary['docling_success_pct']}%)",
        f"    avg time:                {summary['docling_avg_time_s']}s",
        f"  PyMuPDF fallback success:  {summary['fallback_pymupdf_success']} ({summary['fallback_pymupdf_pct']}%)",
    ]
    if summary["pymupdf_avg_time_s"] is not None:
        lines.append(f"    avg time:                {summary['pymupdf_avg_time_s']}s")
    lines += [
        f"  Both failed:               {summary['both_failed']} ({summary['both_failed_pct']}%)",
        "",
    ]
    if summary["docling_not_installed"]:
        lines.append("  ⚠ docling is NOT installed — all PDFs hit fallback path")
    if summary["pymupdf_not_installed"]:
        lines.append("  ⚠ PyMuPDF is NOT installed — no fallback available")

    if n > 0:
        worst = sorted(
            [r for r in results if not r["docling_ok"]],
            key=lambda x: x["size_bytes"],
            reverse=True,
        )[:5]
        if worst:
            lines += [
                "",
                "Largest PDFs where docling failed (consider investigating):",
            ]
            for w in worst:
                lines.append(
                    f"  {w['file']} ({w['size_bytes']/1e6:.1f} MB) "
                    f"→ docling: {w['docling_note']}, "
                    f"pymupdf: {w.get('pymupdf_note', 'n/a')}"
                )

    lines += ["=" * 60]
    summary_text = "\n".join(lines)
    print("\n" + summary_text)

    with open(out_dir / "audit_summary.txt", "w") as f:
        f.write(summary_text + "\n")
    log.info("Summary also written to audit_summary.txt")


if __name__ == "__main__":
    main()
