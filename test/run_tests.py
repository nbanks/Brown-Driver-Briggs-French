#!/usr/bin/env python3
"""Run project test suites.

By default runs only offline tests (no LLM server needed).
Use --html-assemble or --llm-verify to include LLM-dependent suites.

Usage:
    python3 test/run_tests.py                # offline tests only
    python3 test/run_tests.py --all          # everything (needs LLM server)
    python3 test/run_tests.py --html-assemble  # include HTML assembly tests
    python3 test/run_tests.py --llm-verify     # include LLM verify tests
    python3 test/run_tests.py -v             # verbose output
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = ROOT / "test"

# Suites: (name, runner_path, needs_llm)
SUITES = [
    ("check_preserved",
     TEST_DIR / "check_preserved" / "run_check_preserved_test.py", False),
    ("validate_html",
     TEST_DIR / "validate_html" / "run_validate_html_test.py", False),
    ("html_assemble",
     TEST_DIR / "html_assemble" / "run_html_assemble_test.py", True),
    ("llm_verify",
     TEST_DIR / "llm_verify" / "run_llm_verify_test.py", True),
]


def main():
    parser = argparse.ArgumentParser(
        description="Run project test suites.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="verbose output")
    parser.add_argument("--all", action="store_true",
                        help="run all suites including LLM-dependent ones")
    parser.add_argument("--html-assemble", action="store_true",
                        help="include HTML assembly tests (needs LLM server)")
    parser.add_argument("--llm-verify", action="store_true",
                        help="include LLM verify tests (needs LLM server)")
    parser.add_argument("--server", default=None,
                        help="LLM server URL (passed to LLM suites)")
    args = parser.parse_args()

    failures = []

    # Determine which suites to run
    for name, runner, needs_llm in SUITES:
        if needs_llm:
            include = args.all
            if name == "html_assemble":
                include = include or args.html_assemble
            elif name == "llm_verify":
                include = include or args.llm_verify
            if not include:
                continue

        print(f"\n{'='*60}")
        print(f"  Running {name} tests")
        print(f"{'='*60}")
        cmd = [sys.executable, str(runner)]
        if args.server and needs_llm:
            cmd.extend(["--server", args.server])
        result = subprocess.run(cmd, cwd=ROOT)
        if result.returncode != 0:
            failures.append(name)

    # Standalone pytest unit tests (never need LLM)
    print(f"\n{'='*60}")
    print(f"  Running pytest unit tests")
    print(f"{'='*60}")
    test_files = sorted(TEST_DIR.glob("test_*.py"))
    pytest_args = [sys.executable, "-m", "pytest"]
    if args.verbose:
        pytest_args.append("-v")
    else:
        pytest_args.append("-q")
    pytest_args.extend(str(f) for f in test_files)
    result = subprocess.run(pytest_args, cwd=ROOT)
    if result.returncode != 0:
        failures.append("pytest unit tests")

    # Summary
    print(f"\n{'='*60}")
    if failures:
        print(f"  FAILURES: {', '.join(failures)}")
        sys.exit(1)
    else:
        print("  ALL TEST SUITES PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
