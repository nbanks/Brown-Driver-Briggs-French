#!/usr/bin/env python3
"""Verify @@SPLIT markers are at structurally equivalent positions in txt vs txt_fr.

Strips all Latin text, keeping only Hebrew characters and @@SPLIT markers,
then compares the two sequences. If splits land at the same position in the
Hebrew stream, the sequences match exactly.

Usage:
    python3 scripts/check_splits.py               # check all
    python3 scripts/check_splits.py 0 3 7          # only entries ending in 0, 3, 7
    python3 scripts/check_splits.py --count        # summary only
    python3 scripts/check_splits.py --mismatched   # list mismatched entries only
"""

import re
import sys
from pathlib import Path

HEBREW_RE = re.compile(r'[\u0590-\u05FF\uFB1D-\uFB4F]+')
SPLIT_RE = re.compile(r'^@@SPLIT:\w+@@$')


def hebrew_split_sequence(text):
    """Reduce text to a list of Hebrew tokens and SPLIT markers in order.

    Returns a list where each element is either a Hebrew character run
    or a @@SPLIT:type@@ marker string, preserving document order.
    """
    seq = []
    for line in text.splitlines():
        stripped = line.strip()
        if SPLIT_RE.match(stripped):
            seq.append(stripped)
        else:
            for m in HEBREW_RE.finditer(line):
                seq.append(m.group())
    return seq


def compare_entry(en_text, fr_text):
    """Compare Hebrew+SPLIT sequences between English and French.

    Returns (ok, detail) where ok is True if sequences match exactly,
    and detail describes the first mismatch if not.
    """
    en_seq = hebrew_split_sequence(en_text)
    fr_seq = hebrew_split_sequence(fr_text)

    if en_seq == fr_seq:
        return True, None

    min_len = min(len(en_seq), len(fr_seq))
    for i in range(min_len):
        if en_seq[i] != fr_seq[i]:
            return False, (
                f"diverge at token {i}: "
                f"en={en_seq[i]!r} fr={fr_seq[i]!r}"
            )

    longer = "en" if len(en_seq) > len(fr_seq) else "fr"
    extra = en_seq[min_len:] if longer == "en" else fr_seq[min_len:]
    return False, (
        f"{longer} has {len(extra)} extra token(s) "
        f"starting with {extra[0]!r}"
    )


def main():
    base = Path(__file__).parent.parent
    txt_dir = base / 'Entries_txt'
    fr_dir = base / 'Entries_txt_fr'

    digits = set()
    count_only = False
    mismatched_only = False
    for arg in sys.argv[1:]:
        if arg == '--count':
            count_only = True
        elif arg == '--mismatched':
            mismatched_only = True
        elif arg.isdigit() and len(arg) == 1:
            digits.add(int(arg))

    matched = 0
    mismatched = 0
    missing_fr = 0
    no_splits = 0
    missing_fr_splits = 0
    failures = []

    for txt in sorted(txt_dir.glob('BDB*.txt')):
        stem = txt.stem
        num = int(stem.replace('BDB', ''))
        if digits and (num % 10) not in digits:
            continue

        en_text = txt.read_text('utf-8')

        en_has_splits = any(
            SPLIT_RE.match(line.strip()) for line in en_text.splitlines()
        )
        if not en_has_splits:
            no_splits += 1
            continue

        fr_path = fr_dir / txt.name
        if not fr_path.exists():
            missing_fr += 1
            continue

        fr_text = fr_path.read_text('utf-8')
        if not fr_text.strip():
            missing_fr += 1
            continue

        fr_has_splits = any(
            SPLIT_RE.match(line.strip()) for line in fr_text.splitlines()
        )
        if not fr_has_splits:
            missing_fr_splits += 1
            failures.append((stem, "no @@SPLIT markers in French"))
            continue

        ok, detail = compare_entry(en_text, fr_text)
        if ok:
            matched += 1
        else:
            mismatched += 1
            failures.append((stem, detail))

    total_with_splits = matched + mismatched + missing_fr + missing_fr_splits

    if count_only:
        print(f"Entries with splits: {total_with_splits}")
        print(f"  No splits (skip):    {no_splits}")
        print(f"  Matched:             {matched}")
        print(f"  Mismatched:          {mismatched}")
        print(f"  Missing FR splits:   {missing_fr_splits}")
        print(f"  Missing FR file:     {missing_fr}")
        return 0 if not failures else 1

    if mismatched_only:
        for stem, detail in failures:
            print(f"{stem}: {detail}")
        print(f"\nTotal: {len(failures)}")
        return 0 if not failures else 1

    for stem, detail in failures:
        print(f"{stem}: {detail}")

    print(f"\n--- Summary ---")
    print(f"Entries with splits: {total_with_splits}")
    print(f"  Matched:             {matched}")
    print(f"  Mismatched:          {mismatched}")
    print(f"  Missing FR splits:   {missing_fr_splits}")
    print(f"  Missing FR file:     {missing_fr}")
    print(f"  No splits (skip):    {no_splits}")

    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
