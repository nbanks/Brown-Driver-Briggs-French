#!/usr/bin/env python3
"""Check that certain characters are preserved between Entries_txt/ and Entries_txt_fr/.

Supported checks (run all by default, or select with flags):
  --hebrew   Hebrew/Aramaic characters (U+0590-05FF, FB1D-FB4F)
  --caret    ^ markers (superscript boundaries)
  --sub      _N_ markers (subscript boundaries)
  --size     File size anomalies (empty French, ratio out of range)

Also supports filtering by trailing digit of BDB number (0-9).
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from split_entry import split_txt, subsplit_txt

# U+0590-U+05FF: Hebrew block (letters, vowel points, cantillation marks)
# U+FB1D-U+FB4F: Hebrew presentation forms
HEBREW_RE = re.compile(r'[\u0590-\u05FF\uFB1D-\uFB4F]+')

# French files smaller than this fraction of the English are flagged
SIZE_RATIO_MIN = 0.85
SIZE_RATIO_MAX = 1.30


def extract_hebrew(text):
    """Return all Hebrew characters in order as a single string."""
    return ''.join(HEBREW_RE.findall(text))


def extract_carets(text):
    """Return all ^ characters in order as a single string."""
    return ''.join(c for c in text if c == '^')


def extract_underscores(text):
    """Return all _ characters in order as a single string."""
    return ''.join(c for c in text if c == '_')


def get_sections(text):
    """Split text into leaf sections using split_txt + subsplit_txt.

    Returns list of (label, content) pairs where label is the chunk type
    (e.g. 'stem', 'stem.1', 'header').
    """
    chunks = split_txt(text)
    sections = []
    for chunk in chunks:
        subs = subsplit_txt(chunk)
        for sub in subs:
            label = sub.get("label", sub["type"])
            sections.append((label, sub["txt"]))
    return sections


def caret_context(text, n, char='^'):
    """Return context string around the nth occurrence of char in text."""
    idx = -1
    for i in range(n + 1):
        idx = text.index(char, idx + 1)
    start = max(0, idx - 15)
    end = min(len(text), idx + 16)
    return text[start:end].replace('\n', '↵')


def compare_extracted(txt_name, label, en_str, fr_str, en_sec, fr_sec,
                      check_name):
    """Compare extracted strings and print diagnostics. Returns 1 if mismatch."""
    if en_str == fr_str:
        return 0

    if check_name == 'hebrew':
        minlen = min(len(en_str), len(fr_str))
        pos = next((i for i in range(minlen)
                     if en_str[i] != fr_str[i]), minlen)
        ctx = 20
        sect = f" [{label}]" if label else ""
        print(f"{txt_name}{sect}: HEBREW mismatch at char {pos}")
        print(f"  en: ...{en_str[max(0, pos - ctx):pos + ctx]}...")
        print(f"  fr: ...{fr_str[max(0, pos - ctx):pos + ctx]}...")
        if len(en_str) != len(fr_str):
            print(f"  length: en={len(en_str)} fr={len(fr_str)}")
    else:  # caret or sub
        char = '^' if check_name == 'caret' else '_'
        tag = check_name.upper()
        en_c = len(en_str)
        fr_c = len(fr_str)
        sect = f" [{label}]" if label else ""
        print(f"{txt_name}{sect}: {tag} en={en_c} fr={fr_c}")
        if en_c > fr_c:
            try:
                print(f"  missing: ...{caret_context(en_sec, fr_c, char)}...")
            except (ValueError, IndexError):
                pass
        elif fr_c > en_c:
            try:
                print(f"  extra:   ...{caret_context(fr_sec, en_c, char)}...")
            except (ValueError, IndexError):
                pass

    return 1


def check_file(en_text, fr_text, txt_name, extract_fn, check_name):
    """Run one check (hebrew or caret) on a file pair. Returns error count."""
    en_sections = get_sections(en_text)
    fr_sections = get_sections(fr_text)

    if [l for l, _ in en_sections] == [l for l, _ in fr_sections]:
        for (label, en_sec), (_, fr_sec) in zip(en_sections, fr_sections):
            en_str = extract_fn(en_sec)
            fr_str = extract_fn(fr_sec)
            err = compare_extracted(txt_name, label, en_str, fr_str,
                                    en_sec, fr_sec, check_name)
            if err:
                return 1  # one error per file
    else:
        en_str = extract_fn(en_text)
        fr_str = extract_fn(fr_text)
        return compare_extracted(txt_name, None, en_str, fr_str,
                                 en_text, fr_text, check_name)
    return 0


def main():
    args = sys.argv[1:]
    do_hebrew = '--hebrew' in args
    do_caret = '--caret' in args
    do_sub = '--sub' in args
    do_size = '--size' in args
    # If no flags given, run all checks
    if not (do_hebrew or do_caret or do_sub or do_size):
        do_hebrew = do_caret = do_sub = do_size = True

    digits = [a for a in args if a.isdigit() and len(a) == 1]

    base = Path('Entries_txt')
    fr = Path('Entries_txt_fr')

    hebrew_errors = 0
    caret_errors = 0
    sub_errors = 0
    size_errors = 0
    checked = 0

    for txt in sorted(base.glob('BDB*.txt')):
        fr_path = fr / txt.name
        if not fr_path.exists():
            continue

        if digits:
            bdb_num = txt.stem[3:]
            if bdb_num[-1] not in digits:
                continue

        en_text = txt.read_text('utf-8')
        fr_text = fr_path.read_text('utf-8')
        checked += 1

        # Size check
        if do_size:
            en_chars = len(en_text)
            fr_chars = len(fr_text)
            if en_chars > 0 and fr_chars == 0:
                size_errors += 1
                print(f"{txt.name}: EMPTY French file "
                      f"(English is {en_chars} chars)")
                continue
            if en_chars > 0 and fr_chars > 0:
                ratio = fr_chars / en_chars
                if ratio < SIZE_RATIO_MIN or ratio > SIZE_RATIO_MAX:
                    size_errors += 1
                    print(f"{txt.name}: SIZE ANOMALY en={en_chars} "
                          f"fr={fr_chars} ratio={ratio:.2f}")

        if do_hebrew:
            hebrew_errors += check_file(en_text, fr_text, txt.name,
                                        extract_hebrew, 'hebrew')

        if do_caret:
            caret_errors += check_file(en_text, fr_text, txt.name,
                                       extract_carets, 'caret')

        if do_sub:
            sub_errors += check_file(en_text, fr_text, txt.name,
                                     extract_underscores, 'sub')

    print(f"\nChecked {checked} pairs.")
    total = 0
    if do_hebrew:
        print(f"  Hebrew mismatches: {hebrew_errors}")
        total += hebrew_errors
    if do_caret:
        print(f"  Caret mismatches:  {caret_errors}")
        total += caret_errors
    if do_sub:
        print(f"  Sub mismatches:    {sub_errors}")
        total += sub_errors
    if do_size:
        print(f"  Size anomalies:    {size_errors}")
        total += size_errors
    sys.exit(1 if total else 0)


if __name__ == '__main__':
    main()
