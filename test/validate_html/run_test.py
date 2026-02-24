#!/usr/bin/env python3
"""Test harness for validate_html.py against known good/bad HTML translations.

Uses test fixtures in this directory (Entries/, Entries_fr/, Entries_txt_fr/)
with files named GOOD* (should pass) and BAD* (should have errors).

Usage:
    python3 test/validate_html/run_test.py
"""

import os
import sys
from pathlib import Path

# Add project root to path so we can import validate_html internals
TEST_DIR = Path(__file__).resolve().parent
ROOT = TEST_DIR.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# Monkey-patch the directory paths before importing
import validate_html
validate_html.ENTRIES_DIR = str(TEST_DIR / "Entries")
validate_html.ENTRIES_FR_DIR = str(TEST_DIR / "Entries_fr")
validate_html.TXT_FR_DIR = str(TEST_DIR / "Entries_txt_fr")


def main():
    # Discover test cases
    fr_files = sorted(
        Path(validate_html.ENTRIES_FR_DIR).glob("*.html")
    )
    good_ids = []
    bad_ids = []
    for f in fr_files:
        name = f.stem
        if name.startswith("GOOD"):
            good_ids.append(name)
        elif name.startswith("BAD"):
            bad_ids.append(name)

    print(f"=== validate_html.py Tests ({len(good_ids)} good, {len(bad_ids)} bad) ===")
    print()

    false_positives = []  # good files that got errors
    false_negatives = []  # bad files that passed clean
    passes = 0
    details = {}

    for bdb_id in good_ids + bad_ids:
        errors = []
        validate_html.validate_file(bdb_id, errors)
        is_good = bdb_id.startswith("GOOD")
        has_errors = len(errors) > 0
        details[bdb_id] = errors

        if is_good and has_errors:
            false_positives.append(bdb_id)
        elif not is_good and not has_errors:
            false_negatives.append(bdb_id)
        else:
            passes += 1

    total = len(good_ids) + len(bad_ids)
    print(f"  PASS: {passes}/{total}")

    if false_positives:
        print()
        print(f"  FALSE POSITIVES (good file flagged): {len(false_positives)}")
        for f in false_positives:
            print(f"    {f}:")
            for _, msg in details[f]:
                print(f"      {msg}")

    if false_negatives:
        print()
        print(f"  FALSE NEGATIVES (bad file not caught!): {len(false_negatives)}")
        for f in false_negatives:
            print(f"    {f}")

    # Show what was caught for bad files (informational)
    print()
    print("  --- Details for BAD files ---")
    for bdb_id in bad_ids:
        errs = details[bdb_id]
        status = "CAUGHT" if errs else "MISSED!"
        print(f"  {bdb_id}: {status} ({len(errs)} issues)")
        for _, msg in errs:
            print(f"    - {msg}")

    print()
    if false_negatives:
        print("FAIL: false negatives detected")
        return 1
    if false_positives:
        print("FAIL: false positives detected")
        return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
