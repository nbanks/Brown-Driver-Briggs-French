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
                         query_llm, run_pipeline, save_result)

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent

# Import validate_html for validation
sys.path.insert(0, str(SCRIPT_DIR))
from validate_html import validate_file

ENTRIES_DIR = ROOT / "Entries"
ENTRIES_FR_DIR = ROOT / "Entries_fr"
TXT_FR_DIR = ROOT / "Entries_txt_fr"
ERRATA_DIR = Path(".")
RESULTS_FILE = Path("/tmp/llm_html_assemble_results.txt")
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
    return (f"{base}\n\n"
            f"## ⚠️ Nouvel essai — corrigez votre HTML précédent, ne signalez PAS comme ERRATA\n\n"
            f"### Erreurs de validation\n"
            f"```\n{error_lines}\n```\n\n"
            f"### Texte français correct (référence)\n"
            f"```\n{french_txt}\n```\n\n"
            f"### Votre HTML précédent (incorrect)\n"
            f"```html\n{prev_output[:4000]}\n```\n\n"
            f"Corrigez les erreurs ci-dessus et produisez un HTML parfait.")


def get_entries(digits: list[int] | None,
                only: list[str] | None = None) -> list[tuple[str, Path, Path]]:
    """Get sorted list of (bdb_id, orig_html_path, txt_fr_path)."""
    entries = []
    if only is not None:
        only_set = set(only)
        for bdb_id in sorted(only_set):
            txt_path = TXT_FR_DIR / (bdb_id + ".txt")
            orig_path = ENTRIES_DIR / (bdb_id + ".html")
            if txt_path.exists() and orig_path.exists():
                entries.append((bdb_id, orig_path, txt_path))
            else:
                missing = []
                if not txt_path.exists():
                    missing.append(str(txt_path))
                if not orig_path.exists():
                    missing.append(str(orig_path))
                print(f"warning: {bdb_id} skipped, missing: {', '.join(missing)}",
                      file=sys.stderr)
        return entries
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
                  on_attempt=None, debug: bool = False) -> tuple[str, float, int]:
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

    # If a previous (failed) attempt exists on disk, use it as context
    # for the first try so the new model can learn from the old output.
    if fr_path.exists():
        prev = fr_path.read_text()
        prev_errors = validate_file(
            bdb_id, entries_dir=str(ENTRIES_DIR),
            entries_fr_dir=str(ENTRIES_FR_DIR), txt_fr_dir=str(TXT_FR_DIR))
        if prev_errors:
            output_html = prev
            last_errors = prev_errors

    for attempt in range(1, max_retries + 1):
        if on_attempt:
            on_attempt(attempt)
        if attempt == 1 and not last_errors:
            p = prompt
        else:
            p = build_retry_prompt(template, orig_html, french_txt,
                                   output_html, last_errors)
        if debug:
            dbg_prefix = f"/tmp/llm-debug-{bdb_id}-try{attempt}"
            Path(f"{dbg_prefix}-prompt.txt").write_text(p, encoding="utf-8")

        try:
            if debug:
                raw, thinking = query_llm(p, server_url, max_tokens=131072,
                                          return_reasoning=True)
            else:
                raw = query_llm(p, server_url, max_tokens=131072)
        except ContextOverflow:
            return "SKIPPED", prompt_kb, attempt

        if debug:
            Path(f"{dbg_prefix}-out.txt").write_text(raw, encoding="utf-8")
            if thinking:
                Path(f"{dbg_prefix}-think.txt").write_text(
                    thinking, encoding="utf-8")

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

    return "FAILED", prompt_kb, max_retries


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
  %(prog)s --count                      # show remaining count
  %(prog)s --entries BDB8226 BDB7519    # specific entries only""",
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
        "--skip-failed", action="store_true", default=False,
        help="Skip entries that previously FAILED validation (default: retry).",
    )
    parser.add_argument(
        "--skip-errata", action="store_true", default=False,
        help="Skip entries that LLM flagged as ERRATA (default: retry).",
    )
    parser.add_argument(
        "--force", action="store_true", default=False,
        help="Regenerate even if existing file validates clean.",
    )
    parser.add_argument(
        "--entries", nargs="+", metavar="BDB_ID",
        help="Process only these specific entries (e.g. BDB8226 BDB7519).",
    )
    parser.add_argument(
        "--debug", action="store_true", default=False,
        help="Write prompt/response to /tmp/llm-debug-BDBnnn-tryN-{prompt,out}.txt.",
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
    entries = get_entries(digits, only=args.entries)

    # Load errata entries for --skip-errata
    errata_ids = set()
    if args.skip_errata:
        for i in range(10):
            ep = ERRATA_DIR / f"errata-{i}.txt"
            if ep.exists():
                for line in ep.read_text().splitlines():
                    if " html  LLM: " in line:
                        errata_ids.add(line.split()[0])

    # Split entries into existing (need validation) and new (no Entries_fr yet)
    existing = []
    new_entries = []
    for bdb_id, orig_path, txt_path in entries:
        fr_path = ENTRIES_FR_DIR / (bdb_id + ".html")
        if not args.force and fr_path.exists():
            existing.append((bdb_id, orig_path, txt_path))
        else:
            new_entries.append((bdb_id, orig_path, txt_path))

    # Validate existing Entries_fr/ files
    counts = {"clean": 0, "invalid": 0, "errata": 0, "new": len(new_entries)}
    skipped_failed = []
    skipped_errata = []
    to_process = []
    n_exist = len(existing)
    if n_exist:
        sys.stdout.write(f"Validating {n_exist} existing Entries_fr ")
        sys.stdout.flush()
        dot_interval = max(1, n_exist // 40)
        for idx, (bdb_id, orig_path, txt_path) in enumerate(existing):
            if idx % dot_interval == 0:
                sys.stdout.write(".")
                sys.stdout.flush()
            chash = combined_hash(orig_path, txt_path)

            if bdb_id in errata_ids:
                counts["errata"] += 1
                skipped_errata.append(bdb_id)
                continue
            errors = validate_file(
                bdb_id, entries_dir=str(ENTRIES_DIR),
                entries_fr_dir=str(ENTRIES_FR_DIR),
                txt_fr_dir=str(TXT_FR_DIR))
            if not errors:
                counts["clean"] += 1
                continue
            counts["invalid"] += 1
            if args.skip_failed:
                skipped_failed.append(bdb_id)
                continue
            to_process.append((bdb_id, orig_path, txt_path, chash))
        print(" done")
    else:
        print("No existing Entries_fr to validate.")

    # Add new entries to processing list
    for bdb_id, orig_path, txt_path in new_entries:
        chash = combined_hash(orig_path, txt_path)
        to_process.append((bdb_id, orig_path, txt_path, chash))

    # Build summary with * marking skipped categories
    clean_s = f"{counts['clean']} clean*"
    invalid_s = f"{counts['invalid']} invalid"
    if args.skip_failed:
        invalid_s += "*"
    errata_s = f"{counts['errata']} errata"
    if args.skip_errata:
        errata_s += "*"
    print(f"Entries_fr: {n_exist}/{len(entries)} exist: "
          f"{clean_s}, {invalid_s}, {errata_s}")
    n_skipped = counts["clean"]
    if args.skip_failed:
        n_skipped += len(skipped_failed)
    if args.skip_errata:
        n_skipped += len(skipped_errata)
    if n_skipped:
        print(f"  * {n_skipped} skipped")

    if args.count:
        print(f"To process: {len(to_process)}")
        sys.exit(0)

    if not to_process:
        print(f"Nothing to process — all {counts['clean']} entries are clean.")
        sys.exit(0)

    check_server(args.server)

    print(f"\nProcessing {len(to_process)} entries via {args.server} ...")
    print(f"  Prompt:      {prompt_path.name}")
    print(f"  Log:         {RESULTS_FILE}")
    print(f"  Max retries: {args.max_retries}")
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
            on_attempt=on_attempt, debug=args.debug)

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

    def prompt_size_kb(item):
        _, orig_path, txt_path, _ = item
        size = (len(template.encode("utf-8"))
                + orig_path.stat().st_size + txt_path.stat().st_size)
        return size / 1024

    counts = run_pipeline(to_process, process_one,
                          name_fn=lambda item: item[0] + ".html",
                          size_fn=prompt_size_kb,
                          parallel=args.parallel,
                          shuffle=args.shuffle, limit=args.max,
                          label="entries")

    print()
    print(f"Done: {sum(counts.values())} entries processed.")
    print(f"  CLEAN:   {counts.get('CLEAN', 0)}")
    print(f"  FAILED:  {counts.get('FAILED', 0)}")
    print(f"  ERRATA:  {counts.get('ERRATA', 0)}")
    print(f"  SKIPPED: {counts.get('SKIPPED', 0)}")


if __name__ == "__main__":
    main()
