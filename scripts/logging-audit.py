#!/usr/bin/env python3
"""Logging coverage audit — scans kb_server/ and ingest/ for public functions
without log calls. One-time static analysis, no project imports required."""

import ast
import os
import sys
from pathlib import Path


def _get_logger_name(module_path: str) -> str:
    """Infer logger name from module path for display."""
    parts = module_path.replace(".py", "").split("/")
    return ".".join(parts)


def audit_file(filepath: Path) -> dict:
    """Audit a single Python file for logging coverage on public functions/classes."""
    with open(filepath) as f:
        try:
            tree = ast.parse(f.read(), filename=str(filepath))
        except SyntaxError:
            return {"module": str(filepath), "error": "SyntaxError"}

    log_levels = {"log.info", "log.debug", "log.warning", "log.error", "log.exception"}

    results = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            has_log = False
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Attribute):
                        call_str = (
                            f"{ast.unparse(child.func.value)}."
                            f"{child.func.attr}"
                        )
                        if call_str in log_levels:
                            has_log = True
                            break
            results[node.name] = has_log
    return results


def main():
    project_root = Path(os.environ.get("PROJECT_ROOT", Path.cwd()))
    source_dirs = [project_root / "kb_server", project_root / "ingest"]

    print("Logging Coverage Audit")
    print("======================")
    print(f"Generated: 2026-05-23")
    print()

    total_functions = 0
    total_with_logs = 0
    report_lines = []

    for src_dir in source_dirs:
        if not src_dir.exists():
            continue
        py_files = sorted(src_dir.rglob("*.py"))
        py_files = [f for f in py_files if f.name != "__init__.py" and "__pycache__" not in f.parts]

        for py_file in py_files:
            try:
                results = audit_file(py_file)
            except Exception as e:
                report_lines.append(f"{py_file.relative_to(project_root)}: ERROR: {e}")
                continue

            if not results:
                continue

            relative = py_file.relative_to(project_root)
            functions_with_logs = sum(1 for v in results.values() if v)
            total_functions += len(results)
            total_with_logs += functions_with_logs
            pct = functions_with_logs / len(results) * 100 if results else 0

            report_lines.append(f"\n{relative}:")
            gap_count = 0
            for func_name, has_log in sorted(results.items()):
                if not has_log:
                    gap_count += 1
                    report_lines.append(f"  {func_name} — NO LOG")
            if gap_count == 0:
                report_lines.append(f"  All {len(results)} public methods have log calls ✓")
            report_lines.append(
                f"  -> {functions_with_logs}/{len(results)} public methods have log calls ({pct:.0f}%)"
            )

    print("\n".join(report_lines))
    print()
    print("Summary:")
    print(f"  Total functions: {total_functions}")
    print(f"  Functions with logs: {total_with_logs}")
    total_pct = total_with_logs / total_functions * 100 if total_functions else 0
    print(f"  Coverage: {total_pct:.1f}%")
    print(f"  Functions without logs: {total_functions - total_with_logs}")


if __name__ == "__main__":
    main()
