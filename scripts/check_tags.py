#!/usr/bin/env python3
"""Check for unmatched opening/closing tags in HTML entries.

Scans Entries/ and Entries_fr/ for tags that have an uneven number of
openers vs closers within each file. Self-closing tags (like
<placeholder123 />) are ignored.

Usage:
    python3 scripts/check_tags.py              # check both dirs
    python3 scripts/check_tags.py --en         # English only
    python3 scripts/check_tags.py --fr         # French only
    python3 scripts/check_tags.py BDB7431      # specific entry
    python3 scripts/check_tags.py --summary    # totals only
"""

import argparse
import re
import sys
from pathlib import Path

# Matches opening tags like <pos>, <ref ...>, but not self-closing <placeholder1 />
TAG_OPEN_RE = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)\b[^/>]*>")
# Matches closing tags like </pos>
TAG_CLOSE_RE = re.compile(r"</([a-zA-Z][a-zA-Z0-9]*)\s*>")
# Self-closing tags to skip entirely
SELF_CLOSING_RE = re.compile(r"<[a-zA-Z][a-zA-Z0-9]*\b[^>]*/\s*>")

# Tags we don't care about (structural wrappers that may legitimately
# span chunk boundaries or be injected by lxml)
# Void elements (never have closing tags) and structural wrappers.
# Note: <meta> is NOT ignored because BDB uses it as a paired content
# tag (e.g. <meta>figurative</meta>).
# Void elements (no closing tag) and parser-injected wrappers
IGNORED_TAGS = {"html", "head", "body", "link", "hr", "br", "img"}


def check_file(path):
    """Return list of (tag_name, open_count, close_count) for mismatched tags."""
    text = path.read_text(encoding="utf-8")

    opens = {}
    for m in TAG_OPEN_RE.finditer(text):
        # Skip if this is actually part of a self-closing tag
        # (check if there's a /> before the next >)
        tag = m.group(1).lower()
        if tag in IGNORED_TAGS:
            continue
        opens[tag] = opens.get(tag, 0) + 1

    closes = {}
    for m in TAG_CLOSE_RE.finditer(text):
        tag = m.group(1).lower()
        if tag in IGNORED_TAGS:
            continue
        closes[tag] = closes.get(tag, 0) + 1

    # Remove self-closing tags from open counts (they match TAG_OPEN_RE too)
    for m in SELF_CLOSING_RE.finditer(text):
        inner = m.group()
        m2 = re.match(r"<([a-zA-Z][a-zA-Z0-9]*)", inner)
        if m2:
            tag = m2.group(1).lower()
            if tag in opens:
                opens[tag] -= 1
                if opens[tag] == 0:
                    del opens[tag]

    all_tags = sorted(set(list(opens.keys()) + list(closes.keys())))
    mismatches = []
    for tag in all_tags:
        o = opens.get(tag, 0)
        c = closes.get(tag, 0)
        if o != c:
            mismatches.append((tag, o, c))
    return mismatches


def main():
    parser = argparse.ArgumentParser(
        description="Check for unmatched HTML tags in entries.")
    parser.add_argument("entries", nargs="*",
                        help="Specific BDB entries (e.g. BDB7431)")
    parser.add_argument("--en", action="store_true",
                        help="Check English entries only")
    parser.add_argument("--fr", action="store_true",
                        help="Check French entries only")
    parser.add_argument("--summary", action="store_true",
                        help="Show totals only, not per-file details")
    args = parser.parse_args()

    # Default to both if neither specified
    if not args.en and not args.fr:
        args.en = True
        args.fr = True

    dirs = []
    if args.en:
        dirs.append(("English", Path("Entries")))
    if args.fr:
        dirs.append(("French", Path("Entries_fr")))

    total_files = 0
    total_mismatched = 0

    for label, dirpath in dirs:
        if not dirpath.is_dir():
            print(f"  {label}: directory {dirpath} not found, skipping")
            continue

        if args.entries:
            files = []
            for e in args.entries:
                name = e if e.endswith(".html") else e + ".html"
                p = dirpath / name
                if p.exists():
                    files.append(p)
                else:
                    print(f"  {label}: {name} not found")
            files.sort()
        else:
            files = sorted(dirpath.glob("BDB*.html"))

        dir_files = 0
        dir_mismatched = 0

        for f in files:
            mismatches = check_file(f)
            dir_files += 1
            if mismatches:
                dir_mismatched += 1
                if not args.summary:
                    entry = f.stem
                    for tag, o, c in mismatches:
                        print(f"  {label} {entry}: <{tag}> opens={o} closes={c}")

        total_files += dir_files
        total_mismatched += dir_mismatched

        if args.summary or not args.entries:
            print(f"{label}: {dir_mismatched} mismatched / {dir_files} files")

    if total_mismatched > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
