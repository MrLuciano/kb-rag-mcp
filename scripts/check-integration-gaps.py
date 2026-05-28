#!/usr/bin/env python3
"""Integration gap checker — validates cross-referencing between documentation,
requirement traceability, and plan implementation. Runs as a CI gate."""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    Console = None
    Table = None


RESULTS_PATH = "scripts/check-integration-gaps-results.json"


class GapCheck:
    def __init__(self, name: str):
        self.name = name
        self.passed = True
        self.gaps: list[str] = []

    def fail(self, detail: str):
        self.passed = False
        self.gaps.append(detail)

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"

    def __str__(self) -> str:
        return f"{self.name}: {self.status()} ({len(self.gaps)} gap(s))"


def check_verification_presence(project_root: Path) -> GapCheck:
    """Check 1: Every phase directory must have a VERIFICATION.md file."""
    check = GapCheck("VERIFICATION.md presence")
    phases_dir = project_root / ".planning" / "phases"
    if not phases_dir.is_dir():
        check.fail(".planning/phases/ directory not found")
        return check
    for entry in sorted(phases_dir.iterdir()):
        if not entry.is_dir():
            continue
        has_verification = any(
            f.name.upper().startswith("VERIFICATION") or "VERIFICATION" in f.name.upper()
            for f in entry.iterdir()
            if f.is_file()
        )
        if not has_verification:
            check.fail(f"{entry.name} — missing VERIFICATION.md")
    return check


def check_requirements_traceability(project_root: Path) -> GapCheck:
    """Check 2: Parse REQUIREMENTS.md — verify every REQ-ID appears in the
    traceability table and that completion markers are internally consistent."""
    check = GapCheck("REQUIREMENTS.md traceability")
    req_path = project_root / ".planning" / "REQUIREMENTS.md"
    if not req_path.is_file():
        check.fail(".planning/REQUIREMENTS.md not found")
        return check

    text = req_path.read_text(encoding="utf-8")

    req_ids_from_sections: list[str] = []
    for line in text.split("\n"):
        m = re.match(r"^-\s+\[\s?(x| )\s?\]\s+\*\*([A-Z]+-\d+)", line)
        if m:
            req_ids_from_sections.append(m.group(2))

    in_traceability = False
    req_status: dict[str, str] = {}

    for line in text.split("\n"):
        if line.strip().startswith("| Requirement") and "|" in line:
            in_traceability = True
            continue
        if in_traceability:
            stripped = line.strip()
            if not stripped.startswith("|"):
                in_traceability = False
                continue
            if stripped.startswith("|---"):
                continue
            parts = [p.strip() for p in stripped.split("|")]
            if len(parts) >= 2:
                req_id = parts[1].strip()
                if req_id == "Requirement":
                    continue
                if req_id and not req_id.startswith("REQ-ID"):
                    status_cell = parts[3].strip() if len(parts) > 3 else ""
                    req_status[req_id] = status_cell

    for rid in req_ids_from_sections:
        if rid not in req_status:
            check.fail(f"{rid} — found in Active Requirements but missing from traceability table")

    for rid in req_status:
        status = req_status[rid]
        is_completed_in_table = "Complete" in status or "✅" in status
        is_checked_in_section = rid in req_ids_from_sections
        if is_completed_in_table and not is_checked_in_section:
            check.fail(
                f"{rid} — traceability table shows completed but Active Requirements has no [x] marker"
            )

    return check


def parse_frontmatter(text: str) -> dict:
    """Parse YAML-like frontmatter between --- delimiters."""
    if not text.startswith("---"):
        return {}
    end_idx = text.find("---", 3)
    if end_idx == -1:
        return {}
    raw = text[3:end_idx]
    result: dict = {}
    current_key = None
    current_list: list[str] = []
    in_list = False
    for line in raw.split("\n"):
        list_match = re.match(r"^\s{2,}-\s+(.+)$", line)
        key_match = re.match(r"^([a-zA-Z_-][a-zA-Z0-9_-]*):\s*(.*)", line)
        if list_match:
            val = list_match.group(1).strip().strip('"').strip("'")
            current_list.append(val)
            in_list = True
        elif key_match:
            if in_list and current_key:
                result[current_key] = current_list
                current_list = []
                in_list = False
            current_key = key_match.group(1).strip()
            rest = key_match.group(2).strip()
            if rest == "" or rest.startswith("#"):
                current_list = []
                in_list = True
            elif rest.startswith("[") and rest.endswith("]"):
                items = [
                    i.strip().strip("'").strip('"')
                    for i in rest[1:-1].split(",")
                    if i.strip()
                ]
                result[current_key] = items
                current_key = None
            else:
                result[current_key] = rest.strip().strip('"').strip("'")
                current_key = None
                in_list = False
    if in_list and current_key:
        result[current_key] = current_list
    return result


def _strip_description(path: str) -> str:
    """Strip trailing description from a file path (after : or —)."""
    for sep in (" — ", " -- ", ": ", ":"):
        if sep in path and not path.startswith("/"):
            parts = path.split(sep)
            candidate = parts[0].strip()
            if not candidate.startswith(".") and "/" in candidate:
                return candidate
    return path.strip()


def check_summary_file_refs(project_root: Path) -> GapCheck:
    """Check 3: Every file path listed in SUMMARY.md key-files must exist on disk."""
    check = GapCheck("SUMMARY.md file references")
    phases_dir = project_root / ".planning" / "phases"
    if not phases_dir.is_dir():
        check.fail(".planning/phases/ directory not found")
        return check
    found_any = False
    for entry in sorted(phases_dir.iterdir()):
        if not entry.is_dir():
            continue
        for f in sorted(entry.iterdir()):
            if not (f.name.endswith("-SUMMARY.md") or f.name.upper() == "SUMMARY.md"):
                continue
            found_any = True
            text = f.read_text(encoding="utf-8")
            fm = parse_frontmatter(text)
            if not fm:
                continue
            kf = fm.get("key-files") or fm.get("key_files") or {}
            if isinstance(kf, dict):
                for category in ("created", "modified"):
                    files = kf.get(category, [])
                    if isinstance(files, list):
                        for filepath in files:
                            clean = _strip_description(str(filepath))
                            abs_path = project_root / clean
                            if not abs_path.exists():
                                check.fail(
                                    f"{f.name} ({category}): {clean} — not found"
                                )
            elif isinstance(kf, list):
                for filepath in kf:
                    clean = _strip_description(str(filepath))
                    abs_path = project_root / clean
                    if not abs_path.exists():
                        check.fail(f"{f.name}: {clean} — not found")

    if not found_any:
        check.fail("No SUMMARY.md files found in .planning/phases/")
    return check


def run_checks(project_root: Path) -> list[GapCheck]:
    return [
        check_verification_presence(project_root),
        check_requirements_traceability(project_root),
        check_summary_file_refs(project_root),
    ]


def print_results(checks: list[GapCheck]):
    if Console and Table:
        console = Console()
        table = Table(title="Integration Gap Check Results")
        table.add_column("Check", style="cyan", no_wrap=True)
        table.add_column("Status", style="bold")
        table.add_column("Gaps", style="yellow")
        for c in checks:
            status_str = "[green]PASS[/green]" if c.passed else "[red]FAIL[/red]"
            gap_summary = (
                "\n".join(f"  • {g}" for g in c.gaps[:5])
                if c.gaps
                else "—"
            )
            table.add_row(c.name, status_str, gap_summary)
        console.print(table)
    else:
        print("=" * 60)
        print("Integration Gap Check Results")
        print("=" * 60)
        for c in checks:
            print(f"\n{c.name}: {'PASS' if c.passed else 'FAIL'}")
            if c.gaps:
                for g in c.gaps:
                    print(f"  • {g}")
    print()


def write_json_results(
    checks: list[GapCheck], timestamp: str, exit_code: int
):
    results = {
        "timestamp": timestamp,
        "exit_code": exit_code,
        "summary": {
            "total": len(checks),
            "passed": sum(1 for c in checks if c.passed),
            "failed": sum(1 for c in checks if not c.passed),
        },
        "checks": [
            {
                "name": c.name,
                "passed": c.passed,
                "gap_count": len(c.gaps),
                "gaps": c.gaps,
            }
            for c in checks
        ],
    }
    out_path = Path(RESULTS_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Integration gap checker — validates docs <-> code, plans <-> implementation"
    )
    parser.parse_args()

    project_root = Path(os.environ.get("PROJECT_ROOT", Path.cwd()))
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print("Integration Gap Checker")
    print("========================")
    print(f"Timestamp: {timestamp}")
    print(f"Project:  {project_root}")
    print()

    checks = run_checks(project_root)
    overall_passed = all(c.passed for c in checks)
    exit_code = 0 if overall_passed else 1

    print_results(checks)

    total = len(checks)
    passed = sum(1 for c in checks if c.passed)
    failed = total - passed
    print(f"Summary: {passed}/{total} checks passed, {failed} failed")
    print()

    if overall_passed:
        print("PASS: No integration gaps detected.")
    else:
        print(f"FAIL: {failed} check(s) detected integration gaps.")
        print("Review the gaps above before merging.")

    write_json_results(checks, timestamp, exit_code)
    print(f"\nResults written to: {RESULTS_PATH}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
