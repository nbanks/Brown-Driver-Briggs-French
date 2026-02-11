#!/usr/bin/env python3
"""Show BDB entries that have not yet been translated into French.

Requires one or more digit arguments (0-9) to filter by the last digit of
the BDB number.  This lets up to 10 workers split the corpus without overlap.

Usage:
    python3 untranslated.py 0            # entries ending in 0
    python3 untranslated.py 1 5          # entries ending in 1 or 5
    python3 untranslated.py 0 1 2 3 4 5 6 7 8 9   # everything
    python3 untranslated.py 3 -n 5       # show 5, ending in 3
    python3 untranslated.py 7 --json     # json only, ending in 7
    python3 untranslated.py 2 --html     # html only, ending in 2
    python3 untranslated.py 9 --count    # just totals, ending in 9
"""

import argparse
import os
import sys


BASE = os.path.dirname(os.path.abspath(__file__))

DIRS = {
    "json": {
        "src": os.path.join(BASE, "json_output"),
        "dst": os.path.join(BASE, "json_output.fr"),
        "ext": ".json",
        "label": "json_output.fr",
        "rel": "./json_output",
    },
    "html": {
        "src": os.path.join(BASE, "Entries"),
        "dst": os.path.join(BASE, "Entries.fr"),
        "ext": ".html",
        "label": "Entries.fr",
        "rel": "./Entries",
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
    src_files = {
        f for f in os.listdir(src_dir)
        if f.endswith(ext) and f not in SKIP
    }
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


def count_by_digits(src_dir, ext, digits):
    """Count source files whose BDB number ends in one of `digits`."""
    total = 0
    for f in os.listdir(src_dir):
        if f.endswith(ext) and f not in SKIP:
            n = bdb_number(f)
            if n is not None and (n % 10) in digits:
                total += 1
    return total


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
        help="only check json_output.fr",
    )
    parser.add_argument(
        "--html", action="store_true",
        help="only check Entries.fr",
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

    show_json = args.json or (not args.json and not args.html)
    show_html = args.html or (not args.json and not args.html)

    dirs_to_check = []
    if show_json:
        dirs_to_check.append(DIRS["json"])
    if show_html:
        dirs_to_check.append(DIRS["html"])

    total_missing = 0
    budget = args.count_display

    for d in dirs_to_check:
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
            for f in missing[:show_n]:
                bdb_id = os.path.splitext(f)[0]
                src_path = os.path.join(d["src"], f)
                size = os.path.getsize(src_path)
                print(f"  {bdb_id:>12}  ({size:>6} bytes)  {d['rel']}/{f}")
            if n > show_n:
                print(f"  ... and {n - show_n} more")
            budget -= show_n

    print(f"\nTotal untranslated (ending in {digit_str}): {total_missing}")
    return 0 if total_missing == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
