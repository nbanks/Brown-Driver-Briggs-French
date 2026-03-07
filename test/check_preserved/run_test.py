#!/usr/bin/env python3
"""Test harness for check_preserved.py against known good/bad file pairs.

Uses test fixtures in this directory (Entries_txt/, Entries_txt_fr/)
with files named GOOD_* (should pass) and BAD_* (should have errors).

Hebrew test cases:
  GOOD_exact     - Hebrew tokens identical, only French text differs
  GOOD_noheb     - No Hebrew in either file
  BAD_holam      - Holam male (U+05BA) replaced with holam (U+05B9)
  BAD_vowel_added - Spurious hiriq added to unpointed word
  BAD_wrong_letter - He swapped for chet (different consonant)
  BAD_empty      - French file is 0 bytes
  BAD_truncated  - French file cut short (size anomaly + missing Hebrew)
  BAD_shin_sin   - Sin dot (U+05C2) replaced with shin dot (U+05C1)
  BAD_empty_aramaic - Real Aramaic entry with 0-byte French translation

Caret test cases:
  GOOD_carets    - Carets preserved in matching positions
  BAD_caret_missing - French file missing ^ markers
  BAD_caret_extra - French file has extra ^ marker

Subscript test cases:
  BAD_sub_missing - French file missing _N_ subscript marker
  BAD_sub_extra   - French file has extra _N_ subscript marker

Usage:
    python3 test/check_hebrew/run_test.py
"""

import os
import sys
from pathlib import Path

# Import from the actual script
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))
from check_preserved import (extract_hebrew, extract_carets,
                              extract_underscores, check_file)

TEST_DIR = Path(__file__).resolve().parent

SIZE_RATIO_MIN = 0.85
SIZE_RATIO_MAX = 1.30


def check_pair(en_path, fr_path):
    """Return list of error strings for this pair, empty if clean.

    Runs all checks: hebrew, caret, and size.
    """
    errors = []
    en_text = en_path.read_text('utf-8')
    fr_text = fr_path.read_text('utf-8')
    en_chars = len(en_text)
    fr_chars = len(fr_text)

    # Size check
    if en_chars > 0 and fr_chars == 0:
        errors.append(f"EMPTY French file (English is {en_chars} chars)")
        return errors

    if en_chars > 0 and fr_chars > 0:
        ratio = fr_chars / en_chars
        if ratio < SIZE_RATIO_MIN or ratio > SIZE_RATIO_MAX:
            errors.append(f"SIZE ANOMALY en={en_chars} fr={fr_chars} "
                          f"ratio={ratio:.2f}")

    # Hebrew check
    if check_file(en_text, fr_text, en_path.name,
                   extract_hebrew, 'hebrew'):
        errors.append("HEBREW mismatch")

    # Caret check
    if check_file(en_text, fr_text, en_path.name,
                   extract_carets, 'caret'):
        errors.append("CARET mismatch")

    # Subscript check
    if check_file(en_text, fr_text, en_path.name,
                   extract_underscores, 'sub'):
        errors.append("SUB mismatch")

    return errors


def main():
    en_dir = TEST_DIR / 'Entries_txt'
    fr_dir = TEST_DIR / 'Entries_txt_fr'

    good_files = sorted(en_dir.glob('GOOD_*.txt'))
    bad_files = sorted(en_dir.glob('BAD_*.txt'))

    total = len(good_files) + len(bad_files)
    print(f"=== check_preserved Tests "
          f"({len(good_files)} good, {len(bad_files)} bad) ===")
    print()

    passes = 0
    false_positives = []
    false_negatives = []

    for en_path in good_files:
        fr_path = fr_dir / en_path.name
        if not fr_path.exists():
            print(f"  SKIP {en_path.name}: no French counterpart")
            continue
        errors = check_pair(en_path, fr_path)
        if errors:
            false_positives.append((en_path.name, errors))
        else:
            passes += 1

    for en_path in bad_files:
        fr_path = fr_dir / en_path.name
        if not fr_path.exists():
            print(f"  SKIP {en_path.name}: no French counterpart")
            continue
        errors = check_pair(en_path, fr_path)
        if errors:
            passes += 1
        else:
            false_negatives.append(en_path.name)

    print(f"  PASS: {passes}/{total}")

    if false_positives:
        print()
        print(f"  FALSE POSITIVES (good file flagged): "
              f"{len(false_positives)}")
        for name, errs in false_positives:
            print(f"    {name}:")
            for e in errs:
                print(f"      {e}")

    if false_negatives:
        print()
        print(f"  FALSE NEGATIVES (bad file not caught!): "
              f"{len(false_negatives)}")
        for name in false_negatives:
            print(f"    {name}")

    # Details for bad files
    print()
    print("  --- Details for BAD files ---")
    for en_path in bad_files:
        fr_path = fr_dir / en_path.name
        if not fr_path.exists():
            continue
        errors = check_pair(en_path, fr_path)
        status = "CAUGHT" if errors else "MISSED!"
        print(f"  {en_path.name}: {status} ({len(errors)} issues)")
        for e in errors:
            print(f"    - {e}")

    print()
    if false_negatives or false_positives:
        print("FAIL")
        return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == '__main__':
    sys.exit(main())
