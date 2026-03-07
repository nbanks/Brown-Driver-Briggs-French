#!/usr/bin/env python3
"""Test harness for llm_html_assemble.py against known expected outputs.

Runs the assembly script on test fixtures (Entries/ + Entries_txt_fr/) and
compares the LLM output against Entries_fr_expected/. Also validates each
output with validate_html.py.

Expected outcomes are defined in expected.txt (one line per entry with status
and comment). Entries marked ERRATA have deliberately bad txt_fr translations
and are expected to fail validation. No Entries_fr_expected/ file is needed
for them.

Usage:
    python3 test/html_assemble/run_test.py                # run all tests
    python3 test/html_assemble/run_test.py --compare-only  # skip LLM, compare existing
    python3 test/html_assemble/run_test.py -n 3            # only first 3 tests
    python3 test/html_assemble/run_test.py --server http://host:8080
"""

import argparse
import difflib
import re
import shutil
import subprocess
import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
ROOT = TEST_DIR.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate_html


# Directories
ENTRIES_DIR = TEST_DIR / "Entries"
TXT_FR_DIR = TEST_DIR / "Entries_txt_fr"
EXPECTED_DIR = TEST_DIR / "Entries_fr_expected"
OUTPUT_DIR = TEST_DIR / "Entries_fr"
RESULTS_FILE = TEST_DIR / "html_assemble_test_results.txt"
EXPECTED_FILE = TEST_DIR / "expected.txt"

TEST_DIRS = {
    "entries_dir": str(ENTRIES_DIR),
    "entries_fr_dir": str(OUTPUT_DIR),
    "txt_fr_dir": str(TXT_FR_DIR),
}


def load_expected() -> dict[str, str]:
    """Load expected statuses from expected.txt.

    Returns dict mapping BDB ID (e.g. "BDB105") to status ("CLEAN"/"ERRATA").
    """
    expected = {}
    for line in EXPECTED_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            bdb_id = parts[0].replace(".html", "")
            expected[bdb_id] = parts[1]
    return expected


def normalize_html(text: str) -> str:
    """Normalize whitespace in HTML for comparison (collapse runs, strip)."""
    # Collapse whitespace runs to single space within lines
    lines = []
    for line in text.splitlines():
        line = line.rstrip()
        if line.strip():
            lines.append(line)
    return "\n".join(lines)


def compare_html(expected: str, actual: str) -> tuple[float, list[str]]:
    """Compare expected vs actual HTML. Returns (similarity_ratio, diff_lines)."""
    exp_norm = normalize_html(expected)
    act_norm = normalize_html(actual)

    ratio = difflib.SequenceMatcher(None, exp_norm, act_norm).ratio()

    diff = list(difflib.unified_diff(
        exp_norm.splitlines(), act_norm.splitlines(),
        fromfile="expected", tofile="actual", lineterm="", n=1
    ))
    return ratio, diff


def check_key_elements(expected: str, actual: str) -> list[str]:
    """Check that key structural elements from expected are in actual."""
    issues = []

    # Check all Hebrew text preserved
    heb_pat = re.compile(r'[\u0590-\u05FF\uFB1D-\uFB4F]+')
    exp_heb = set(heb_pat.findall(expected))
    act_heb = set(heb_pat.findall(actual))
    missing_heb = exp_heb - act_heb
    if missing_heb:
        issues.append(f"Missing Hebrew: {', '.join(list(missing_heb)[:5])}")

    # Check all <ref> tags preserved
    ref_pat = re.compile(r'<ref\s[^>]*>')
    exp_refs = set(ref_pat.findall(expected))
    act_refs = set(ref_pat.findall(actual))
    missing_refs = exp_refs - act_refs
    if missing_refs:
        issues.append(f"Missing {len(missing_refs)} ref tags")

    # Check French keywords present (from expected)
    for keyword in ["hébreu biblique", "araméen biblique"]:
        if keyword in expected and keyword not in actual:
            issues.append(f"Missing '{keyword}'")

    # Check no English remnants in pos/primary/language tags
    for tag in ["pos", "primary", "language"]:
        pat = re.compile(rf"<{tag}>(.*?)</{tag}>", re.DOTALL)
        for m in pat.finditer(actual):
            content = m.group(1).strip()
            # Check for common English words that should be French
            for eng, fr in [("noun", "nom"), ("verb", "verbe"),
                            ("adjective", "adjectif"),
                            ("Biblical Hebrew", "hébreu biblique")]:
                if eng in content and fr not in content:
                    issues.append(f"English '{eng}' in <{tag}>: {content[:60]}")

    return issues


def get_test_entries(expect: dict[str, str]) -> list[str]:
    """Get sorted list of BDB IDs from expected.txt that have test fixtures.

    An entry qualifies if it has both Entries/*.html and Entries_txt_fr/*.txt.
    CLEAN entries also need an Entries_fr_expected/*.html file.
    """
    ids = []
    for bdb_id, status in sorted(expect.items()):
        if not (ENTRIES_DIR / f"{bdb_id}.html").exists():
            continue
        if not (TXT_FR_DIR / f"{bdb_id}.txt").exists():
            continue
        if status == "CLEAN" and not (EXPECTED_DIR / f"{bdb_id}.html").exists():
            continue
        ids.append(bdb_id)
    return sorted(ids)


def parse_results_file() -> dict[str, str]:
    """Parse the results file to get status per entry."""
    statuses = {}
    if not RESULTS_FILE.exists():
        return statuses
    for line in RESULTS_FILE.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            filename = parts[0]
            status = parts[1]
            bdb_id = filename.replace(".html", "")
            statuses[bdb_id] = status
    return statuses


def main():
    parser = argparse.ArgumentParser(
        description="Test llm_html_assemble.py against expected outputs.")
    parser.add_argument("--compare-only", action="store_true",
                        help="Skip LLM run, just compare existing output.")
    parser.add_argument("-n", "--max", type=int, default=0, metavar="N",
                        help="Limit to first N test entries (0 = all).")
    parser.add_argument("--server", default="http://127.0.0.1:8080",
                        help="llama.cpp server URL.")
    parser.add_argument("-j", "--parallel", type=int, default=1, metavar="J",
                        help="Number of parallel LLM requests.")
    parser.add_argument("--fresh", action="store_true",
                        help="Clear previous output and results before running.")
    args = parser.parse_args()

    expect = load_expected()
    expect_errata = {k for k, v in expect.items() if v == "ERRATA"}

    entries = get_test_entries(expect)
    if args.max > 0:
        entries = entries[:args.max]

    if not entries:
        print("No test entries found.", file=sys.stderr)
        sys.exit(1)

    clean_entries = [e for e in entries if e not in expect_errata]
    errata_entries = [e for e in entries if e in expect_errata]
    print(f"=== html_assemble Tests ({len(entries)} entries: "
          f"{len(clean_entries)} clean, {len(errata_entries)} errata-expected) ===")
    print()

    if args.fresh:
        if OUTPUT_DIR.exists():
            shutil.rmtree(OUTPUT_DIR)
        if RESULTS_FILE.exists():
            RESULTS_FILE.unlink()

    OUTPUT_DIR.mkdir(exist_ok=True)

    if not args.compare_only:
        # Run the assembly script
        cmd = [
            sys.executable, str(ROOT / "scripts" / "llm_html_assemble.py"),
            "--entries-dir", str(ENTRIES_DIR),
            "--txt-fr-dir", str(TXT_FR_DIR),
            "--output-dir", str(OUTPUT_DIR),
            "--results", str(RESULTS_FILE),
            "--server", args.server,
            "--max-retries", "2",
            "--force",
            "--errata-dir", "/tmp",
            "-j", str(args.parallel),
        ]
        if args.max > 0:
            cmd.extend(["-n", str(args.max)])

        print(f"Running llm_html_assemble.py on {len(entries)} test entries...")
        print()
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print("llm_html_assemble.py failed", file=sys.stderr)
            sys.exit(result.returncode)
        print()

    # Parse results file for ERRATA status detection
    result_statuses = parse_results_file()

    # Compare results
    passes = 0
    errata_passes = 0
    validation_fails = []
    comparison_fails = []
    missing_output = []

    for bdb_id in entries:
        is_errata_expected = bdb_id in expect_errata
        output_path = OUTPUT_DIR / f"{bdb_id}.html"
        expected_path = EXPECTED_DIR / f"{bdb_id}.html"

        if is_errata_expected:
            # For ERRATA-expected entries: pass if results show ERRATA or
            # if output has validation errors
            result_status = result_statuses.get(bdb_id, "")
            has_output = output_path.exists()

            if result_status == "ERRATA":
                errata_passes += 1
                print(f"  {bdb_id:<12s} PASS  (ERRATA as expected)")
            elif has_output:
                # Check if validation would catch it
                val_errors = validate_html.validate_file(bdb_id, **TEST_DIRS)
                if val_errors:
                    errata_passes += 1
                    print(f"  {bdb_id:<12s} PASS  (val_errors={len(val_errors)}, errata-expected)")
                else:
                    print(f"  {bdb_id:<12s} FAIL  (expected ERRATA but output passed validation)")
                    for err in val_errors[:3]:
                        print(f"    val: {err}")
            elif args.compare_only:
                # In compare-only mode, no output is expected for errata entries
                errata_passes += 1
                print(f"  {bdb_id:<12s} PASS  (no output, errata-expected, compare-only)")
            else:
                errata_passes += 1
                print(f"  {bdb_id:<12s} PASS  (no output produced, errata-expected)")
            continue

        # Clean-expected entry
        if not output_path.exists():
            missing_output.append(bdb_id)
            continue

        actual_html = output_path.read_text()
        expected_html = expected_path.read_text()

        # 1. Run validate_html
        val_errors = validate_html.validate_file(bdb_id, **TEST_DIRS)

        # 2. Compare with expected output
        similarity, diff = compare_html(expected_html, actual_html)

        # 3. Check key structural elements
        key_issues = check_key_elements(expected_html, actual_html)

        # Determine pass/fail
        # Pass if: no validation errors AND similarity > 0.8 AND no key issues
        is_pass = (not val_errors and similarity > 0.8 and not key_issues)

        if is_pass:
            passes += 1
            status = "PASS"
        else:
            status = "FAIL"

        print(f"  {bdb_id:<12s} {status}  sim={similarity:.1%}", end="")
        if val_errors:
            print(f"  val_errors={len(val_errors)}", end="")
            validation_fails.append((bdb_id, val_errors, similarity))
        if key_issues:
            print(f"  key_issues={len(key_issues)}", end="")
        print()

        if not is_pass:
            if not val_errors and not key_issues:
                comparison_fails.append((bdb_id, similarity, diff))
            # Show details for failures
            if val_errors:
                for _, msg in val_errors[:3]:
                    print(f"    val: {msg}")
            if key_issues:
                for issue in key_issues[:3]:
                    print(f"    key: {issue}")
            if diff and similarity < 0.95:
                print(f"    diff ({len(diff)} lines):")
                for line in diff[:8]:
                    print(f"      {line}")

    print()
    clean_checked = len(clean_entries) - len(missing_output)
    total_errata = len(errata_entries)
    print(f"  CLEAN PASS: {passes}/{clean_checked}")
    print(f"  ERRATA PASS: {errata_passes}/{total_errata}")

    if missing_output:
        print(f"  MISSING OUTPUT: {len(missing_output)}")
        for bdb_id in missing_output:
            print(f"    {bdb_id}")

    if validation_fails:
        print(f"  VALIDATION FAILURES: {len(validation_fails)}")

    print()
    all_passed = (passes == clean_checked and clean_checked > 0
                  and errata_passes == total_errata)
    if all_passed:
        print("ALL TESTS PASSED")
        return 0
    else:
        total_pass = passes + errata_passes
        total_check = clean_checked + total_errata
        print(f"DONE: {total_pass}/{total_check} passed")
        return 1 if total_pass < total_check else 0


if __name__ == "__main__":
    sys.exit(main())
