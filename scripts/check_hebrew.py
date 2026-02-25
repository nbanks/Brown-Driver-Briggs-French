#!/usr/bin/env python3
"""Check that Hebrew/Aramaic text is preserved verbatim between Entries_txt/ and Entries_txt_fr/.

Also flags size anomalies: empty French files and significant size differences.
"""

import re
import sys
from pathlib import Path

# U+0590–U+05FF: Hebrew block (letters, vowel points, cantillation marks)
# U+FB1D–U+FB4F: Hebrew presentation forms
HEBREW_RE = re.compile(r'[\u0590-\u05FF\uFB1D-\uFB4F]+')

# French files smaller than this fraction of the English are flagged
SIZE_RATIO_MIN = 0.85
SIZE_RATIO_MAX = 1.30


def extract_hebrew(text):
    """Return all Hebrew characters in order as a single string."""
    return ''.join(HEBREW_RE.findall(text))


def main():
    base = Path('Entries_txt')
    fr = Path('Entries_txt_fr')

    hebrew_errors = 0
    size_errors = 0
    checked = 0

    for txt in sorted(base.glob('BDB*.txt')):
        fr_path = fr / txt.name
        if not fr_path.exists():
            continue
        checked += 1

        en_text = txt.read_text('utf-8')
        fr_text = fr_path.read_text('utf-8')
        en_chars = len(en_text)
        fr_chars = len(fr_text)

        # Check for empty or drastically different character counts
        if en_chars > 0 and fr_chars == 0:
            size_errors += 1
            print(f"{txt.name}: EMPTY French file (English is {en_chars} chars)")
            continue
        if en_chars > 0 and fr_chars > 0:
            ratio = fr_chars / en_chars
            if ratio < SIZE_RATIO_MIN or ratio > SIZE_RATIO_MAX:
                size_errors += 1
                print(f"{txt.name}: SIZE ANOMALY en={en_chars} fr={fr_chars} ratio={ratio:.2f}")

        # Check Hebrew preservation
        heb_en = extract_hebrew(en_text)
        heb_fr = extract_hebrew(fr_text)
        if heb_en != heb_fr:
            hebrew_errors += 1
            minlen = min(len(heb_en), len(heb_fr))
            pos = next((i for i in range(minlen) if heb_en[i] != heb_fr[i]), minlen)
            ctx = 20
            print(f"{txt.name}: MISMATCH at Hebrew char {pos}")
            print(f"  en: ...{heb_en[max(0, pos - ctx):pos + ctx]}...")
            print(f"  fr: ...{heb_fr[max(0, pos - ctx):pos + ctx]}...")
            if len(heb_en) != len(heb_fr):
                print(f"  length: en={len(heb_en)} fr={len(heb_fr)}")

    print(f"\nChecked {checked} pairs.")
    print(f"  Hebrew mismatches: {hebrew_errors}")
    print(f"  Size anomalies:    {size_errors}")
    sys.exit(1 if (hebrew_errors or size_errors) else 0)


if __name__ == '__main__':
    main()
