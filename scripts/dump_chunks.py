#!/usr/bin/env python3
"""Dump individual chunks of a BDB entry for manual reassembly.

When llm_html_assemble.py fails on large entries, use this tool to extract
a single chunk (HTML + txt_fr) so a human or LLM agent can do the reassembly
manually, one chunk at a time.

Usage:
    python3 scripts/dump_chunks.py BDB1045              # list chunks
    python3 scripts/dump_chunks.py BDB1045 0            # dump chunk 0 (header)
    python3 scripts/dump_chunks.py BDB1045 1            # dump chunk 1
    python3 scripts/dump_chunks.py BDB1045 1 --html     # HTML only
    python3 scripts/dump_chunks.py BDB1045 1 --txt      # txt_fr only

Full file paths are also supported (auto-detects entry type):
    python3 scripts/dump_chunks.py Entries/BDB1045.html          # list chunks
    python3 scripts/dump_chunks.py Entries_fr/BDB1045.html 3     # dump chunk 3
    python3 scripts/dump_chunks.py Entries_txt_fr/BDB1045.txt 2  # dump chunk 2
"""

import argparse
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from split_entry import split_html, split_txt

# Map directory names to their roles
DIR_ROLES = {
    "Entries": "html_orig",
    "Entries_fr": "html_fr",
    "Entries_txt": "txt_orig",
    "Entries_txt_fr": "txt_fr",
}


def resolve_entry(entry_arg):
    """Resolve entry argument to (bdb_id, html_path, txt_fr_path, txt_en_path, source_hint).

    entry_arg can be:
      - A BDB ID like "BDB1045" or "1045"
      - A file path like "Entries/BDB1045.html" or "Entries_txt_fr/BDB1045.txt"
    """
    path = Path(entry_arg)

    # Check if it looks like a file path (has a suffix or directory separator)
    if path.suffix or '/' in entry_arg:
        # Extract BDB ID from filename
        m = re.search(r'(BDB\d+)', path.stem)
        if not m:
            print(f"Error: cannot extract BDB ID from {entry_arg}",
                  file=sys.stderr)
            sys.exit(1)
        bdb_id = m.group(1)

        # Determine source hint from parent directory
        parent = path.parent.name
        source_hint = DIR_ROLES.get(parent)
    else:
        bdb_id = entry_arg
        if not bdb_id.startswith("BDB"):
            bdb_id = "BDB" + bdb_id
        source_hint = None

    html_path = ROOT / "Entries" / (bdb_id + ".html")
    html_fr_path = ROOT / "Entries_fr" / (bdb_id + ".html")
    txt_path = ROOT / "Entries_txt_fr" / (bdb_id + ".txt")
    txt_en_path = ROOT / "Entries_txt" / (bdb_id + ".txt")

    return bdb_id, html_path, html_fr_path, txt_path, txt_en_path, source_hint


def main():
    parser = argparse.ArgumentParser(
        description="Dump chunks of a BDB entry for manual reassembly.")
    parser.add_argument("entry",
                        help="BDB entry ID (e.g. BDB1045) or file path "
                             "(e.g. Entries_fr/BDB1045.html)")
    parser.add_argument("chunk", nargs="?", type=int, default=None,
                        help="Chunk index to dump (0-based). Omit to list all.")
    parser.add_argument("--html", action="store_true",
                        help="Show only the HTML chunk")
    parser.add_argument("--txt", action="store_true",
                        help="Show only the txt_fr chunk")
    args = parser.parse_args()

    bdb_id, html_path, html_fr_path, txt_path, txt_en_path, source_hint = \
        resolve_entry(args.entry)

    if not html_path.exists():
        print(f"Error: {html_path} not found", file=sys.stderr)
        sys.exit(1)

    # Decide which HTML to chunk based on source hint
    if source_hint == "html_fr" and html_fr_path.exists():
        html_source = html_fr_path
    else:
        html_source = html_path

    html_text = html_source.read_text(encoding="utf-8")
    html_chunks = split_html(html_text)

    # Decide which txt to show based on source hint
    if source_hint == "txt_orig" and txt_en_path.exists():
        txt_source = txt_en_path
    else:
        txt_source = txt_path

    txt_text = txt_source.read_text(encoding="utf-8") if txt_source.exists() else None
    txt_chunks = split_txt(txt_text) if txt_text else []

    matched = (len(html_chunks) >= 2
               and len(html_chunks) == len(txt_chunks))

    if args.chunk is None:
        # List mode
        print(f"{bdb_id}: {len(html_chunks)} HTML chunks, "
              f"{len(txt_chunks)} txt chunks"
              f"{' (matched)' if matched else ' (MISMATCH)' if txt_chunks else ''}")
        print(f"  HTML source: {html_source}")
        print(f"  HTML: {len(html_text) // 1024}KB total")
        if txt_text:
            print(f"  txt source: {txt_source}")
            print(f"  txt: {len(txt_text) // 1024}KB total")
        print()
        for i, c in enumerate(html_chunks):
            kb = len(c["html"]) // 1024
            txt_kb = len(txt_chunks[i]["txt"]) // 1024 if matched and i < len(txt_chunks) else "?"
            print(f"  [{i}] type={c['type']:8s}  html={kb}KB  txt={txt_kb}KB")
        return

    idx = args.chunk
    if idx < 0 or idx >= len(html_chunks):
        print(f"Error: chunk {idx} out of range (0..{len(html_chunks)-1})",
              file=sys.stderr)
        sys.exit(1)

    show_both = not args.html and not args.txt

    if args.html or show_both:
        if show_both:
            print(f"=== HTML chunk {idx}/{len(html_chunks)} "
                  f"(type={html_chunks[idx]['type']}) ===")
        print(html_chunks[idx]["html"])

    if args.txt or show_both:
        if not matched:
            print("Warning: chunk counts don't match, showing full txt",
                  file=sys.stderr)
            if txt_text:
                if show_both:
                    print(f"\n=== txt (full, unmatched) ===")
                print(txt_text)
        elif idx < len(txt_chunks):
            if show_both:
                print(f"\n=== txt chunk {idx}/{len(txt_chunks)} "
                      f"(type={txt_chunks[idx]['type']}) ===")
            print(txt_chunks[idx]["txt"])


if __name__ == "__main__":
    main()
