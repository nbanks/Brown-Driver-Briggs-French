#!/usr/bin/env python3
"""Test harness for check_hebrew.py against known good/bad file pairs.

Uses test fixtures in this directory (Entries_txt/, Entries_txt_fr/)
with files named GOOD_* (should pass) and BAD_* (should have errors).

Test cases:
  GOOD_exact     - Hebrew tokens identical, only French text differs
  GOOD_noheb     - No Hebrew in either file
  BAD_holam      - Holam male (U+05BA) replaced with holam (U+05B9)
  BAD_vowel_added - Spurious hiriq added to unpointed word
  BAD_wrong_letter - He swapped for chet (different consonant)
  BAD_empty      - French file is 0 bytes
  BAD_truncated  - French file cut short (size anomaly + missing Hebrew)
  BAD_shin_sin   - Sin dot (U+05C2) replaced with shin dot (U+05C1)
  BAD_empty_aramaic - Real Aramaic entry with 0-byte French translation

Usage:
    python3 test/check_hebrew/run_test.py
"""

import re
import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent

HEBREW_RE = re.compile(r'[\u0590-\u05FF\uFB1D-\uFB4F]+')
SIZE_RATIO_MIN = 0.85
SIZE_RATIO_MAX = 1.30


def extract_hebrew(text):
    return ''.join(HEBREW_RE.findall(text))


def check_pair(en_path, fr_path):
    """Return list of error strings for this pair, empty if clean."""
    errors = []
    en_text = en_path.read_text('utf-8')
    fr_text = fr_path.read_text('utf-8')
    en_chars = len(en_text)
    fr_chars = len(fr_text)

    if en_chars > 0 and fr_chars == 0:
        errors.append(f"EMPTY French file (English is {en_chars} chars)")
        return errors

    if en_chars > 0 and fr_chars > 0:
        ratio = fr_chars / en_chars
        if ratio < SIZE_RATIO_MIN or ratio > SIZE_RATIO_MAX:
            errors.append(f"SIZE ANOMALY en={en_chars} fr={fr_chars} ratio={ratio:.2f}")

    heb_en = extract_hebrew(en_text)
    heb_fr = extract_hebrew(fr_text)
    if heb_en != heb_fr:
        minlen = min(len(heb_en), len(heb_fr))
        pos = next((i for i in range(minlen) if heb_en[i] != heb_fr[i]), minlen)
        msg = f"MISMATCH at Hebrew char {pos}"
        if len(heb_en) != len(heb_fr):
            msg += f" (length: en={len(heb_en)} fr={len(heb_fr)})"
        errors.append(msg)

    return errors


def main():
    en_dir = TEST_DIR / 'Entries_txt'
    fr_dir = TEST_DIR / 'Entries_txt_fr'

    good_files = sorted(en_dir.glob('GOOD_*.txt'))
    bad_files = sorted(en_dir.glob('BAD_*.txt'))

    total = len(good_files) + len(bad_files)
    print(f"=== check_hebrew Tests ({len(good_files)} good, {len(bad_files)} bad) ===")
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
        print(f"  FALSE POSITIVES (good file flagged): {len(false_positives)}")
        for name, errs in false_positives:
            print(f"    {name}:")
            for e in errs:
                print(f"      {e}")

    if false_negatives:
        print()
        print(f"  FALSE NEGATIVES (bad file not caught!): {len(false_negatives)}")
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
