"""
E2E test suite runner for KB-RAG-MCP.

Runs end-to-end tests with different configurations.
"""

import subprocess
import sys
from pathlib import Path


def run_e2e_tests(
    integration: bool = False,
    verbose: bool = False,
    coverage: bool = False
):
    """Run E2E test suite."""
    cmd = ["pytest", "tests/e2e/"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=server", "--cov=ingest", "--cov-report=html"])
    
    if integration:
        cmd.append("--run-integration")
        print("Running with integration tests (requires external services)")
    else:
        print("Running unit E2E tests only (no external dependencies)")
    
    env = {}
    if not integration:
        env["SKIP_INTEGRATION_TESTS"] = "1"
        env["SKIP_DEPLOYMENT_TESTS"] = "1"
    
    print(f"Command: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, env={**env, **dict(os.environ)})
    return result.returncode


if __name__ == "__main__":
    import argparse
    import os
    
    parser = argparse.ArgumentParser(
        description="Run KB-RAG E2E tests"
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests (requires external services)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    args = parser.parse_args()
    
    exit_code = run_e2e_tests(
        integration=args.integration,
        verbose=args.verbose,
        coverage=args.coverage
    )
    
    sys.exit(exit_code)
