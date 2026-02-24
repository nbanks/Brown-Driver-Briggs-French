#!/usr/bin/env python3
"""Show BDB entries flagged by llm_verify that have not yet been reviewed.

Parses the llm_verify results file for entries with non-CORRECT status (ERROR,
WARN, UNKNOWN, etc.) and lists those that do not yet have a corresponding note
file in Entries_notes/.  This lets a reviewer work through flagged entries
incrementally -- once a note file exists, the entry is considered reviewed.

Requires one or more digit arguments (0-9) to filter by the last digit of the
BDB number, just like untranslated.py.

Usage:
    python3 scripts/review_errors.py 0            # entries ending in 0
    python3 scripts/review_errors.py 1 5          # entries ending in 1 or 5
    python3 scripts/review_errors.py 0 1 2 3 4 5 6 7 8 9   # everything
    python3 scripts/review_errors.py 3 -n 5       # 5 entries ending in 3
    python3 scripts/review_errors.py 4 --count    # just totals, ending in 4
    python3 scripts/review_errors.py 7 --status   # include status & reason
"""

import argparse
import os
import sys


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RESULTS_FILE = os.path.join(BASE, "llm_verify_txt_results.txt")
NOTES_DIR = os.path.join(BASE, "Entries_notes")
TXT_DIR = os.path.join(BASE, "Entries_txt")
TXT_FR_DIR = os.path.join(BASE, "Entries_txt_fr")


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


def parse_results(results_path):
    """Parse llm_verify results file, return dict of {filename: (status, reason)}.

    Only includes non-CORRECT entries."""
    flagged = {}
    try:
        with open(results_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                # Format: BDB1234.txt,            STATUS, timestamp, hash, "reason"
                parts = line.split(",", 4)
                if len(parts) < 2:
                    continue
                filename = parts[0].strip()
                status = parts[1].strip()
                if status == "CORRECT":
                    continue
                reason = parts[4].strip().strip('"') if len(parts) >= 5 else ""
                flagged[filename] = (status, reason)
    except FileNotFoundError:
        print(f"error: results file not found: {results_path}", file=sys.stderr)
        sys.exit(1)
    return flagged


def find_unreviewed(flagged, notes_dir, digits):
    """Return sorted list of flagged filenames that have no note file yet,
    filtered to entries whose BDB number ends in one of `digits`."""
    try:
        reviewed = set(os.listdir(notes_dir))
    except FileNotFoundError:
        reviewed = set()

    unreviewed = []
    for filename in flagged:
        n = bdb_number(filename)
        if n is None or (n % 10) not in digits:
            continue
        if filename not in reviewed:
            unreviewed.append(filename)

    return sorted(unreviewed, key=bdb_sort_key)


def main():
    parser = argparse.ArgumentParser(
        description="List BDB entries flagged by llm_verify that need review.",
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
        "-n", "--count-display", type=int, default=5,
        help="max entries to display (default: 5)",
    )
    parser.add_argument(
        "--count", action="store_true",
        help="only print totals, no file list",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="show status and reason for each entry",
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

    flagged = parse_results(RESULTS_FILE)

    # Count total flagged in this digit range (regardless of review status)
    total_in_range = sum(
        1 for f in flagged
        if bdb_number(f) is not None and (bdb_number(f) % 10) in digits
    )

    unreviewed = find_unreviewed(flagged, NOTES_DIR, digits)
    n = len(unreviewed)
    reviewed = total_in_range - n

    print(
        f"\nFlagged entries (ending in {digit_str}): "
        f"{reviewed}/{total_in_range} reviewed, {n} remaining"
    )

    if args.count or n == 0:
        if n == 0:
            print("All flagged entries have been reviewed.")
        print(f"\nTotal unreviewed (ending in {digit_str}): {n}")
        return 0 if n == 0 else 1

    show_n = min(n, args.count_display)
    for f in unreviewed[:show_n]:
        stem = os.path.splitext(f)[0]
        line = f"  ./Entries_txt/{f}  ./Entries_txt_fr/{f}"
        status, reason = flagged[f]
        if not args.status:
            # Truncate reason for display
            if len(reason) > 2000:
                reason = reason[:2000] + "..."
        line += f"  [{status}] {reason}"
        print(line)
    if n > show_n:
        print(f"  ... and {n - show_n} more")

    print(f"\nTotal unreviewed (ending in {digit_str}): {n}")
    return 0 if n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
