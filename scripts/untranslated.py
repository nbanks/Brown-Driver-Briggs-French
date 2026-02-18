#!/usr/bin/env python3
"""Show BDB entries that have not yet been translated into French.

Requires one or more digit arguments (0-9) to filter by the last digit of
the BDB number.  This lets up to 10 workers split the corpus without overlap.

Checks Entries_txt/ first (the main translation pipeline), then Entries_fr/
(HTML reassembly -- only entries where all prerequisites exist), then
json_output/ as a secondary check.

Usage:
    python3 scripts/untranslated.py 0            # entries ending in 0
    python3 scripts/untranslated.py 1 5          # entries ending in 1 or 5
    python3 scripts/untranslated.py 0 1 2 3 4 5 6 7 8 9   # everything
    python3 scripts/untranslated.py 3 -n 5       # show 5, ending in 3
    python3 scripts/untranslated.py 7 --json     # json only, ending in 7
    python3 scripts/untranslated.py 2 --txt      # txt only, ending in 2
    python3 scripts/untranslated.py 9 --html     # html only, ending in 9
    python3 scripts/untranslated.py 4 --count    # just totals, ending in 4
    python3 scripts/untranslated.py 5 --txt --html --json -n 5  # all modes, 5 each
"""

import argparse
import os
import sys


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Source and destination directories for each translation mode.
DIRS = {
    "txt": {
        "src": os.path.join(BASE, "Entries_txt"),
        "dst": os.path.join(BASE, "Entries_txt_fr"),
        "ext": ".txt",
        "label": "Entries_txt_fr",
        "src_rel": "./Entries_txt",
        "dst_rel": "./Entries_txt_fr",
    },
    "html": {
        "src": os.path.join(BASE, "Entries"),
        "dst": os.path.join(BASE, "Entries_fr"),
        "txt_dir": os.path.join(BASE, "Entries_txt"),
        "txt_fr_dir": os.path.join(BASE, "Entries_txt_fr"),
        "ext": ".html",
        "label": "Entries_fr",
        "src_rel": "./Entries",
        "dst_rel": "./Entries_fr",
        "txt_rel": "./Entries_txt",
        "txt_fr_rel": "./Entries_txt_fr",
    },
    "json": {
        "src": os.path.join(BASE, "json_output"),
        "dst": os.path.join(BASE, "json_output_fr"),
        "ext": ".json",
        "label": "json_output_fr",
        "src_rel": "./json_output",
        "dst_rel": "./json_output_fr",
    },
}

SKIP = {"style.css"}


def bdb_number(filename):
    """Extract the numeric BDB id from a filename, or None."""
    name = os.path.splitext(filename)[0]
    try:
        return int(name.replace("BDB", ""))
    except ValueError:
        return None


def bdb_sort_key(filename):
    """Sort BDB filenames numerically: BDB1, BDB2, ... BDB10022."""
    n = bdb_number(filename)
    return n if n is not None else float("inf")


def find_missing(src_dir, dst_dir, ext, digits):
    """Return sorted list of filenames present in src but absent from dst,
    filtered to entries whose BDB number ends in one of `digits`."""
    src_files = {f for f in os.listdir(src_dir) if f.endswith(ext) and f not in SKIP}
    try:
        dst_files = set(os.listdir(dst_dir))
    except FileNotFoundError:
        dst_files = set()

    missing = []
    for f in src_files - dst_files:
        n = bdb_number(f)
        if n is not None and (n % 10) in digits:
            missing.append(f)

    return sorted(missing, key=bdb_sort_key)


def find_missing_html(d, digits):
    """Return HTML entries ready for reassembly: the source .html exists,
    both prerequisite files (Entries_txt/*.txt and Entries_txt_fr/*.txt)
    exist, but the output Entries_fr/*.html does not yet exist."""
    src_files = {f for f in os.listdir(d["src"]) if f.endswith(".html") and f not in SKIP}
    try:
        dst_files = set(os.listdir(d["dst"]))
    except FileNotFoundError:
        dst_files = set()
    try:
        txt_files = set(os.listdir(d["txt_dir"]))
    except FileNotFoundError:
        txt_files = set()
    try:
        txt_fr_files = set(os.listdir(d["txt_fr_dir"]))
    except FileNotFoundError:
        txt_fr_files = set()

    missing = []
    blocked = 0
    for f in src_files - dst_files:
        n = bdb_number(f)
        if n is None or (n % 10) not in digits:
            continue
        stem = os.path.splitext(f)[0]
        txt_name = stem + ".txt"
        if txt_name in txt_files and txt_name in txt_fr_files:
            missing.append(f)
        else:
            blocked += 1

    return sorted(missing, key=bdb_sort_key), blocked


def count_by_digits(src_dir, ext, digits):
    """Count source files whose BDB number ends in one of `digits`."""
    total = 0
    for f in os.listdir(src_dir):
        if f.endswith(ext) and f not in SKIP:
            n = bdb_number(f)
            if n is not None and (n % 10) in digits:
                total += 1
    return total


def format_missing_simple(f, d):
    """Format: src -> dst (used for txt and json modes)."""
    return f"  {d['src_rel']}/{f} -> {d['dst_rel']}/{f}"


def format_missing_html(f, d):
    """Format: html + txt + txt_fr => dst (used for html mode)."""
    stem = os.path.splitext(f)[0]
    return (
        f"  {d['src_rel']}/{f} + {d['txt_rel']}/{stem}.txt"
        f" + {d['txt_fr_rel']}/{stem}.txt => {d['dst_rel']}/{f}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="List BDB entries not yet translated into French.",
        epilog=(
            "The DIGITS argument filters entries by the last digit of their "
            "BDB number (e.g. '1 5' matches BDB1, BDB5, BDB11, BDB15, ...). "
            "This lets multiple workers split the corpus without overlap."
        ),
    )
    parser.add_argument(
        "digits", nargs="*", metavar="DIGIT",
        help="last digit(s) to include (0-9); at least one required",
    )
    parser.add_argument(
        "-n", "--count-display", type=int, default=20,
        help="max entries to display per directory (default: 20)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="only check json_output_fr",
    )
    parser.add_argument(
        "--txt", action="store_true",
        help="only check Entries_txt_fr",
    )
    parser.add_argument(
        "--html", action="store_true",
        help="only check Entries_fr (HTML reassembly, requires txt_fr prerequisites)",
    )
    parser.add_argument(
        "--count", action="store_true",
        help="only print totals, no file list",
    )
    args = parser.parse_args()

    if not args.digits:
        parser.print_help()
        print("\nerror: at least one DIGIT (0-9) is required", file=sys.stderr)
        return 2

    try:
        digits = {int(d) for d in args.digits}
    except ValueError:
        parser.print_help()
        print("\nerror: digits must be integers 0-9", file=sys.stderr)
        return 2

    if not digits.issubset(set(range(10))):
        parser.print_help()
        print("\nerror: digits must be integers 0-9", file=sys.stderr)
        return 2

    digit_str = ",".join(str(d) for d in sorted(digits))

    any_filter = args.txt or args.json or args.html
    show_txt = args.txt or not any_filter
    show_html = args.html or not any_filter
    show_json = args.json or not any_filter

    modes = []
    if show_txt:
        modes.append("txt")
    if show_html:
        modes.append("html")
    if show_json:
        modes.append("json")

    total_missing = 0
    budget = args.count_display

    for mode in modes:
        d = DIRS[mode]
        if not os.path.isdir(d["src"]):
            print(f"\n{d['label']}: source directory {d['src']} not found, skipping")
            continue

        if mode == "html":
            missing, blocked = find_missing_html(d, digits)
            src_count = count_by_digits(d["src"], d["ext"], digits)
            n = len(missing)
            total_missing += n + blocked
            done = src_count - n - blocked

            status = f"{done}/{src_count} translated, {n} ready"
            if blocked:
                status += f", {blocked} awaiting txt_fr"
            print(f"\n{d['label']} (ending in {digit_str}): {status}")
        else:
            missing = find_missing(d["src"], d["dst"], d["ext"], digits)
            n = len(missing)
            total_missing += n
            src_count = count_by_digits(d["src"], d["ext"], digits)
            done = src_count - n
            print(
                f"\n{d['label']} (ending in {digit_str}): "
                f"{done}/{src_count} translated, {n} remaining"
            )

        if args.count or budget <= 0:
            continue

        show_n = min(n, budget)
        if show_n > 0:
            fmt = format_missing_html if mode == "html" else format_missing_simple
            for f in missing[:show_n]:
                print(fmt(f, d))
            if n > show_n:
                print(f"  ... and {n - show_n} more")
            budget -= show_n

    print(f"\nTotal untranslated (ending in {digit_str}): {total_missing}")
    return 0 if total_missing == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
