#!/usr/bin/env python3
"""Verify that split_html and split_txt produce aligned chunks.

For every entry that has both Entries/*.html and Entries_txt/*.txt,
checks that:
1. The chunk counts match between HTML and txt splitting.
2. The Hebrew/Aramaic content in each chunk is identical.
3. No stray </div> replaces a proper closing tag (e.g. <meta>X</div>
   instead of <meta>X</meta>), which confuses split_html's depth counter.

Run from the project root:
    python3 test/test_split_alignment.py
    python3 test/test_split_alignment.py BDB6636    # single entry
    python3 test/test_split_alignment.py --malformed  # tag check only
    python3 test/test_split_alignment.py --alignment  # split check only
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from split_entry import split_html, split_txt

HEBREW_RE = re.compile(r'[\u0590-\u05FF\uFB1D-\uFB4F]+')

# Simple malformation: <tag>WORD</div> where WORD is short (no nested tags)
# These are clear cases where </div> should be </tag>.
_SIMPLE_MALFORMED_RE = re.compile(
    r'<(meta|highlight|primary|pos|gloss|language)\b[^>]*>'
    r'([^<]{1,50})'  # short text content, no nested tags
    r'</div>'
)


def extract_hebrew(text):
    """Return all Hebrew/Aramaic characters in order."""
    return ''.join(HEBREW_RE.findall(text))


def check_malformed(html_path):
    """Check for simple stray </div> replacing closing tags.

    Returns list of (tag_name, content, position) tuples.
    """
    html = html_path.read_text('utf-8')
    issues = []
    for m in _SIMPLE_MALFORMED_RE.finditer(html):
        issues.append((m.group(1), m.group(2).strip(), m.start()))
    return issues


def check_alignment(html_path, txt_path):
    """Check chunk alignment between HTML and txt. Returns list of issues.

    Only checks entries where the txt has ## SPLIT markers (canonical splits
    from extract_txt.py). Entries without markers use heuristic fallback in
    split_txt which may legitimately disagree with split_html.
    """
    html = html_path.read_text('utf-8')
    txt = txt_path.read_text('utf-8')

    # Skip entries without canonical split markers — the heuristic fallback
    # may split differently from the HTML, but llm_html_assemble handles
    # this by treating the entry as a single chunk.
    if '## SPLIT ' not in txt:
        return []

    html_chunks = split_html(html)
    txt_chunks = split_txt(txt)

    issues = []

    if len(html_chunks) != len(txt_chunks):
        h_labels = [(c['type'], c['label']) for c in html_chunks]
        t_labels = [(c['type'], c['label']) for c in txt_chunks]
        issues.append(
            f"chunk count: html={len(html_chunks)} {h_labels} "
            f"txt={len(txt_chunks)} {t_labels}")
        return issues

    for i, (hc, tc) in enumerate(zip(html_chunks, txt_chunks)):
        heb_h = extract_hebrew(hc['html'])
        heb_t = extract_hebrew(tc['txt'])
        if heb_h != heb_t:
            minlen = min(len(heb_h), len(heb_t))
            pos = next((j for j in range(minlen)
                        if heb_h[j] != heb_t[j]), minlen)
            ctx = 15
            issues.append(
                f"hebrew mismatch chunk {i} at char {pos}: "
                f"html=...{heb_h[max(0,pos-ctx):pos+ctx]}... "
                f"txt=...{heb_t[max(0,pos-ctx):pos+ctx]}...")

    return issues


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('entries', nargs='*',
                        help='Specific BDB entries to check (e.g. BDB6636)')
    parser.add_argument('--malformed', action='store_true',
                        help='Only check for malformed HTML tags')
    parser.add_argument('--alignment', action='store_true',
                        help='Only check split alignment')
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    entries_dir = root / "Entries"
    txt_dir = root / "Entries_txt"

    if args.entries:
        html_files = []
        for e in args.entries:
            e = e.replace('.html', '').replace('.txt', '')
            p = entries_dir / f"{e}.html"
            if p.exists():
                html_files.append(p)
            else:
                print(f"WARNING: {p} not found", file=sys.stderr)
        html_files.sort()
    else:
        html_files = sorted(entries_dir.glob('BDB*.html'))

    total = 0
    malformed_count = 0
    alignment_count = 0

    for html_path in html_files:
        bdb = html_path.stem
        total += 1

        # Check malformed HTML
        if not args.alignment:
            mal_issues = check_malformed(html_path)
            if mal_issues:
                malformed_count += 1
                for tag, content, pos in mal_issues:
                    print(f"{bdb}: MALFORMED <{tag}>{content}</div>"
                          f" at pos {pos} (should be </{tag}>)")

        if args.malformed:
            continue

        # Check alignment
        txt_path = txt_dir / f"{bdb}.txt"
        if not txt_path.exists():
            continue

        align_issues = check_alignment(html_path, txt_path)
        if align_issues:
            alignment_count += 1
            for issue in align_issues:
                print(f"{bdb}: ALIGNMENT {issue}")

    print(f"\nChecked {total} entries.")
    if not args.alignment:
        print(f"  Malformed HTML (simple): {malformed_count}")
    if not args.malformed:
        print(f"  Split misalignment: {alignment_count}")

    sys.exit(1 if (malformed_count or alignment_count) else 0)


if __name__ == '__main__':
    main()
