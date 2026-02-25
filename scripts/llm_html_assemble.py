#!/usr/bin/env python3
"""Generate French HTML entries using a local LLM via llama.cpp server.

Combines Entries/ (original HTML) with Entries_txt_fr/ (French text) to produce
Entries_fr/ (French HTML). Validates each output with validate_html and retries
on failure, feeding errors back to the LLM.

Results are stored in llm_html_assemble_results.txt (aligned CSV format).

Usage:
    python3 scripts/llm_html_assemble.py              # all entries with txt_fr
    python3 scripts/llm_html_assemble.py 0 3 7         # digits 0, 3, 7
    python3 scripts/llm_html_assemble.py -n 50         # stop after 50
    python3 scripts/llm_html_assemble.py --count        # show remaining count
    python3 scripts/llm_html_assemble.py -j 4          # 4 parallel requests
    python3 scripts/llm_html_assemble.py --max-retries 5
    python3 scripts/llm_html_assemble.py --force        # regenerate even if clean
"""

import argparse
import re
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from llm_common import (ContextOverflow, check_server, combined_hash,
                         load_results, query_llm, run_pipeline, save_result)

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent

# Import validate_html for validation
sys.path.insert(0, str(SCRIPT_DIR))
from validate_html import validate_file

ENTRIES_DIR = ROOT / "Entries"
ENTRIES_FR_DIR = ROOT / "Entries_fr"
TXT_FR_DIR = ROOT / "Entries_txt_fr"
ERRATA_DIR = Path(".")
RESULTS_FILE = ROOT / "llm_html_assemble_results.txt"
PROMPT_FILE = SCRIPT_DIR / "llm_html_assemble.md"

# Column widths for aligned CSV output
COL_FILENAME = 16
COL_STATUS = 6


def check_llm_errata(raw: str) -> str | None:
    """Check if LLM flagged the input as errata. Returns reason or None."""
    for line in raw.strip().splitlines():
        line = line.strip()
        if line.startswith(">>> ERRATA"):
            # Extract reason after ">>> ERRATA:" or ">>> ERRATA"
            rest = line[len(">>> ERRATA"):].lstrip(":").strip()
            return rest or "LLM flagged translation error"
    return None


def extract_html(raw: str) -> str:
    """Extract HTML from LLM response, stripping markdown fences if present."""
    raw = raw.strip()
    m = re.match(r"^```(?:html)?\s*\n(.*?)```\s*$", raw, re.DOTALL)
    if m:
        return m.group(1).strip()
    if raw.startswith("```") and raw.endswith("```"):
        return raw[3:-3].strip()
    return raw


def build_prompt(template: str, orig_html: str, french_txt: str) -> str:
    """Build the assembly prompt from template and inputs."""
    return (template
            .replace("{{ORIGINAL_HTML}}", orig_html)
            .replace("{{FRENCH_TXT}}", french_txt))


def build_retry_prompt(template: str, orig_html: str, french_txt: str,
                       prev_output: str, errors: list[tuple[str, str]]) -> str:
    """Build a retry prompt with previous errors appended."""
    base = build_prompt(template, orig_html, french_txt)
    error_lines = "\n".join(f"- {msg}" for _, msg in errors)
    return (f"{base}\n\n---\n"
            f"Your previous output had these validation errors:\n"
            f"{error_lines}\n\n"
            f"Here was your previous (incorrect) output for reference:\n"
            f"```\n{prev_output[:4000]}\n```\n\n"
            f"Please fix these issues and output the corrected HTML.")


def get_entries(digits: list[int] | None) -> list[tuple[str, Path, Path]]:
    """Get sorted list of (bdb_id, orig_html_path, txt_fr_path)."""
    entries = []
    for txt_path in sorted(TXT_FR_DIR.iterdir()):
        if not txt_path.name.endswith(".txt"):
            continue
        bdb_id = txt_path.stem
        if digits is not None:
            num_str = "".join(c for c in bdb_id if c.isdigit())
            if num_str and int(num_str[-1]) not in digits:
                continue
        orig_path = ENTRIES_DIR / (bdb_id + ".html")
        if orig_path.exists():
            entries.append((bdb_id, orig_path, txt_path))
    return entries


def process_entry(bdb_id: str, orig_path: Path, txt_path: Path,
                  template: str, server_url: str, max_retries: int,
                  results_path: Path, file_lock: threading.Lock,
                  on_attempt=None) -> tuple[str, float, int]:
    """Process one entry: generate HTML, validate, retry on failure.

    on_attempt(attempt_num): optional callback called at the start of each
        attempt, used to print live progress (e.g. " 1", " 2") in -j 1 mode.

    Returns (final_status, prompt_kb, attempts_used).
    """
    orig_html = orig_path.read_text()
    french_txt = txt_path.read_text()
    fr_path = ENTRIES_FR_DIR / (bdb_id + ".html")

    prompt = build_prompt(template, orig_html, french_txt)
    prompt_kb = len(prompt.encode("utf-8")) / 1024

    output_html = None
    last_errors = []

    for attempt in range(1, max_retries + 1):
        if on_attempt:
            on_attempt(attempt)
        if attempt == 1:
            p = prompt
        else:
            p = build_retry_prompt(template, orig_html, french_txt,
                                   output_html, last_errors)
        try:
            raw = query_llm(p, server_url, max_tokens=16384)
        except ContextOverflow:
            return "SKIPPED", prompt_kb, attempt

        # Check if LLM flagged the French input as errata
        errata_reason = check_llm_errata(raw)
        if errata_reason:
            bdb_num = "".join(c for c in bdb_id if c.isdigit())
            last_digit = bdb_num[-1] if bdb_num else "0"
            errata_path = ERRATA_DIR / f"errata-{last_digit}.txt"
            with file_lock:
                with open(errata_path, "a") as f:
                    f.write(f"{bdb_id} html  LLM: {errata_reason}\n")
            return "ERRATA", prompt_kb, attempt

        output_html = extract_html(raw)
        fr_path.write_text(output_html, encoding="utf-8")

        last_errors = validate_file(
            bdb_id, entries_dir=str(ENTRIES_DIR),
            entries_fr_dir=str(ENTRIES_FR_DIR), txt_fr_dir=str(TXT_FR_DIR))
        if not last_errors:
            return "CLEAN", prompt_kb, attempt

    # Exhausted retries — log to errata
    bdb_num = "".join(c for c in bdb_id if c.isdigit())
    last_digit = bdb_num[-1] if bdb_num else "0"
    errata_path = ERRATA_DIR / f"errata-{last_digit}.txt"
    error_summary = "; ".join(msg for _, msg in last_errors[:5])
    if len(last_errors) > 5:
        error_summary += f"; ... (+{len(last_errors) - 5} more)"
    with file_lock:
        with open(errata_path, "a") as f:
            f.write(f"{bdb_id} html  {len(last_errors)} issues after "
                    f"{max_retries} retries: {error_summary}\n")

    return "ERRATA", prompt_kb, max_retries


def main():
    parser = argparse.ArgumentParser(
        description="Generate French HTML entries using a local LLM.",
        epilog="""Examples:
  %(prog)s                              # all entries
  %(prog)s 0 3 7                        # only BDB numbers ending in 0, 3, 7
  %(prog)s -n 50                        # stop after 50 files
  %(prog)s -j 4                         # 4 parallel LLM requests
  %(prog)s --max-retries 5              # up to 5 validation retries
  %(prog)s --force                      # regenerate even if existing is clean
  %(prog)s --count                      # show remaining count""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "digits", nargs="*", type=int, metavar="DIGIT",
        help="Filter by last digit of BDB number (0-9). Default: all.",
    )
    parser.add_argument(
        "--server", default="http://127.0.0.1:8080",
        help="llama.cpp server URL (default: http://127.0.0.1:8080).",
    )
    parser.add_argument(
        "--prompt", help="Override prompt template file.",
    )
    parser.add_argument(
        "--entries-dir", help="Override Entries/ directory.",
    )
    parser.add_argument(
        "--txt-fr-dir", help="Override Entries_txt_fr/ directory.",
    )
    parser.add_argument(
        "--output-dir", help="Override Entries_fr/ output directory.",
    )
    parser.add_argument(
        "--results", help="Override results file path.",
    )
    parser.add_argument(
        "--errata-dir", help="Override directory for errata-N.txt files.",
    )
    parser.add_argument(
        "--count", action="store_true",
        help="Just show how many files need processing, don't run.",
    )
    parser.add_argument(
        "-n", "--max", type=int, default=0, metavar="N",
        help="Stop after N files (0 = unlimited).",
    )
    parser.add_argument(
        "-j", "--parallel", type=int, default=1, metavar="J",
        help="Number of parallel LLM requests. Default: 1.",
    )
    parser.add_argument(
        "--max-retries", type=int, default=3, metavar="R",
        help="Max validation retry attempts per entry. Default: 3.",
    )
    parser.add_argument(
        "--shuffle", action="store_true", default=False,
        help="Randomize file order.",
    )
    parser.add_argument(
        "--force", action="store_true", default=False,
        help="Regenerate even if existing file validates clean.",
    )
    args = parser.parse_args()

    # Apply directory overrides
    global ENTRIES_DIR, ENTRIES_FR_DIR, TXT_FR_DIR, ERRATA_DIR, RESULTS_FILE
    if args.entries_dir:
        ENTRIES_DIR = Path(args.entries_dir)
    if args.txt_fr_dir:
        TXT_FR_DIR = Path(args.txt_fr_dir)
    if args.output_dir:
        ENTRIES_FR_DIR = Path(args.output_dir)
    if args.errata_dir:
        ERRATA_DIR = Path(args.errata_dir)
    if args.results:
        RESULTS_FILE = Path(args.results)

    prompt_path = Path(args.prompt) if args.prompt else PROMPT_FILE
    if not prompt_path.exists():
        print(f"error: prompt template not found: {prompt_path}",
              file=sys.stderr)
        sys.exit(1)
    template = prompt_path.read_text()

    digits = args.digits if args.digits else None
    entries = get_entries(digits)

    # Determine what needs processing
    existing = load_results(RESULTS_FILE)
    to_process = []
    for bdb_id, orig_path, txt_path in entries:
        filename = bdb_id + ".html"
        chash = combined_hash(orig_path, txt_path)

        if not args.force:
            if filename in existing:
                status, _, prev_hash = existing[filename]
                if status == "CLEAN" and prev_hash == chash:
                    continue
        to_process.append((bdb_id, orig_path, txt_path, chash))

    if args.count:
        total = len(entries)
        done = total - len(to_process)
        print(f"{total} total, {done} done, {len(to_process)} remaining")
        if existing:
            counts = {}
            for v, _, _ in existing.values():
                counts[v] = counts.get(v, 0) + 1
            parts = [f"{k}: {v}" for k, v in sorted(counts.items())]
            print(f"  Results so far: {', '.join(parts)}")
        sys.exit(0)

    if not to_process:
        print(f"All {len(entries)} entries already processed "
              f"(results in {RESULTS_FILE.name}).")
        sys.exit(0)

    check_server(args.server)

    print(f"Processing {len(to_process)} entries via {args.server} ...")
    print(f"Prompt:      {prompt_path.name}")
    print(f"Results:     {RESULTS_FILE.name}")
    print(f"Max retries: {args.max_retries}")
    print()

    file_lock = threading.Lock()

    sequential = args.parallel <= 1
    # Max width of " try 1 2 3 ..." column for alignment (includes leading space)
    max_try_str = " try " + " ".join(str(n) for n in range(1, args.max_retries + 1))
    max_try_width = len(max_try_str)

    def process_one(i, total, item):
        bdb_id, orig_path, txt_path, chash = item
        filename = bdb_id + ".html"
        try_chars = 0

        def on_attempt(n):
            """Print attempt number inline (sequential mode only)."""
            nonlocal try_chars
            if sequential:
                s = f" try {n}" if n == 1 else f" {n}"
                try_chars += len(s)
                sys.stdout.write(s)
                sys.stdout.flush()

        status, prompt_kb, attempts = process_entry(
            bdb_id, orig_path, txt_path, template,
            args.server, args.max_retries, RESULTS_FILE, file_lock,
            on_attempt=on_attempt)

        # Pad try column to fixed width so status aligns
        if sequential and try_chars < max_try_width:
            sys.stdout.write(" " * (max_try_width - try_chars))
            sys.stdout.flush()

        result_note = f"attempt {attempts}/{args.max_retries}" if attempts > 1 else ""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        save_result(RESULTS_FILE, filename, status, timestamp, chash,
                    result_note, col_filename=COL_FILENAME,
                    col_status=COL_STATUS, lock=file_lock)
        display_note = f"({attempts}/{args.max_retries})" if attempts > 1 else ""
        return filename, status, prompt_kb, display_note

    counts = run_pipeline(to_process, process_one,
                          name_fn=lambda item: item[0] + ".html",
                          parallel=args.parallel,
                          shuffle=args.shuffle, limit=args.max,
                          label="entries")

    print()
    print(f"Done: {sum(counts.values())} entries processed.")
    print(f"  CLEAN:   {counts.get('CLEAN', 0)}")
    print(f"  ERRATA:  {counts.get('ERRATA', 0)}")
    print(f"  SKIPPED: {counts.get('SKIPPED', 0)}")


if __name__ == "__main__":
    main()
