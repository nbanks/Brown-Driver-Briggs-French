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
                         fmt_kb, query_llm, run_pipeline, save_result)

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))
from validate_html import validate_file, validate_html
from split_entry import split_html, split_txt

ENTRIES_DIR = ROOT / "Entries"
ENTRIES_FR_DIR = ROOT / "Entries_fr"
TXT_FR_DIR = ROOT / "Entries_txt_fr"
ERRATA_DIR = Path(".")
RESULTS_FILE = Path("/tmp/llm_html_assemble_results.txt")
PROMPT_FILE = SCRIPT_DIR / "llm_html_assemble.md"

# Column widths for aligned CSV output
COL_FILENAME = 16
COL_STATUS = 6


# ---------------------------------------------------------------------------
# LLM response parsing
# ---------------------------------------------------------------------------

def check_llm_errata(raw: str) -> str | None:
    """Check if LLM flagged the input as errata. Returns reason or None."""
    for line in raw.strip().splitlines():
        line = line.strip()
        if line.startswith(">>> ERRATA"):
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


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def build_prompt(template: str, orig_html: str, french_txt: str) -> str:
    """Build the assembly prompt from template and inputs."""
    return (template
            .replace("{{ORIGINAL_HTML}}", orig_html)
            .replace("{{FRENCH_TXT}}", french_txt))


CHUNK_NOTE_TEMPLATE = (
    "\n\n## Mode morceau ({idx}/{total})\n\n"
    "Vous recevez un **morceau** d'une entrée, pas l'entrée complète. "
    "Produisez le HTML uniquement pour ce morceau — n'ajoutez pas "
    "`<html>`, `<head>` ni `<hr>` sauf s'ils apparaissent dans le "
    "HTML original ci-dessous.\n"
)


def build_chunk_prompt(template: str, html_chunk: str, txt_chunk: str,
                       chunk_idx: int, total_chunks: int) -> str:
    """Build a prompt for one chunk of a split entry."""
    chunk_note = CHUNK_NOTE_TEMPLATE.format(idx=chunk_idx + 1,
                                            total=total_chunks)
    base = (template
            .replace("{{ORIGINAL_HTML}}", html_chunk)
            .replace("{{FRENCH_TXT}}", txt_chunk))
    return base + chunk_note


def _build_retry_suffix(history: list[tuple[str, list[str]]],
                        is_chunk: bool = False) -> str:
    """Build the error-feedback suffix from all previous attempts.

    history is a list of (output, errors) tuples, one per failed attempt.
    Appending each attempt sequentially keeps the prefix stable for caching.
    """
    no_errata = "" if is_chunk else ", ne signalez PAS comme ERRATA"
    scope = " pour ce morceau" if is_chunk else ""
    parts = []

    for i, (output, errors) in enumerate(history, 1):
        error_lines = "\n".join(f"- {msg}" for msg in errors)
        label = f"Tentative {i}" if len(history) > 1 else "Tentative précédente"
        parts.extend([
            "",
            f"## ⚠️ {label} — erreurs{no_errata}",
            "",
            f"### Erreurs de validation",
            f"```\n{error_lines}\n```",
            "",
            f"### HTML produit (incorrect)",
            f"```html\n{output}\n```",
        ])

    parts.extend([
        "",
        f"Produisez le HTML complet corrigé{scope},"
        " en évitant **toutes** les erreurs listées ci-dessus.",
    ])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Errata helper
# ---------------------------------------------------------------------------

def _write_errata(bdb_id: str, message: str, file_lock: threading.Lock):
    """Append an errata line to the appropriate errata-N.txt file."""
    bdb_num = "".join(c for c in bdb_id if c.isdigit())
    last_digit = bdb_num[-1] if bdb_num else "0"
    errata_path = ERRATA_DIR / f"errata-{last_digit}.txt"
    with file_lock:
        with open(errata_path, "a") as f:
            f.write(f"{bdb_id} html  {message}\n")


# ---------------------------------------------------------------------------
# Entry file listing
# ---------------------------------------------------------------------------

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
                print(f"warning: {bdb_id} skipped, missing: "
                      f"{', '.join(missing)}", file=sys.stderr)
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


# ---------------------------------------------------------------------------
# Unified chunk processing
# ---------------------------------------------------------------------------
#
# Everything is treated as a list of chunks. A whole entry is just 1 chunk.
# Each chunk is validated in-memory with the full validate_html. Only failing
# chunks are retried. The assembled result is written to disk at the end.
#
# Chunk = {orig_html, txt_fr, fr_html (output), errors}

def _generate_chunk(bdb_id: str, idx: int, n: int,
                    orig_html: str, txt_fr: str, prev_output: str | None,
                    prev_errors: list[str], template: str,
                    server_url: str, max_retries: int,
                    is_chunked: bool,
                    on_attempt=None, on_chunk=None,
                    debug: bool = False,
                    smart_server: str | None = None,
                    smart_retries: int = 1,
                    ) -> tuple[str | None, float, int, list[str], str | None]:
    """Generate (and retry) one chunk.

    Returns (html, prompt_kb, attempts, remaining_errors, errata).
    remaining_errors is [] on success, or the last validation errors if
    retries were exhausted. errata is a string reason or None.
    """
    output = prev_output
    errors = prev_errors
    prompt_kb_total = 0.0
    history: list[tuple[str, list[str]]] = []  # (output, errors) per attempt
    errata_reason = None

    for attempt in range(1, max_retries + 1):
        # Skip if already clean (warm-start found no errors)
        if output is not None and not errors:
            return output, prompt_kb_total, 0, [], None

        # Build prompt
        if is_chunked:
            base = build_chunk_prompt(template, orig_html, txt_fr, idx, n)
        else:
            base = build_prompt(template, orig_html, txt_fr)

        if errors and output is not None:
            history.append((output, errors))
            prompt = base + _build_retry_suffix(history,
                                                is_chunk=is_chunked)
        else:
            prompt = base

        prompt_kb = len(prompt.encode("utf-8")) / 1024
        prompt_kb_total += prompt_kb

        if on_chunk and attempt == 1:
            on_chunk(idx, n, prompt_kb, is_chunked)

        if on_attempt:
            on_attempt(attempt)

        if debug:
            dbg = f"/tmp/llm-html-debug-{bdb_id}-try{attempt}"
            if is_chunked:
                dbg += f"-chunk{idx}"
            Path(f"{dbg}-prompt.txt").write_text(prompt, encoding="utf-8")

        try:
            if debug and not is_chunked:
                raw, thinking = query_llm(prompt, server_url,
                                          max_tokens=131072,
                                          return_reasoning=True)
            else:
                raw = query_llm(prompt, server_url, max_tokens=131072)
                thinking = None
        except ContextOverflow:
            if is_chunked:
                return output, prompt_kb_total, attempt, errors, None
            return None, prompt_kb_total, attempt, errors, "SKIPPED"

        if debug:
            Path(f"{dbg}-out.txt").write_text(raw, encoding="utf-8")
            if thinking:
                Path(f"{dbg}-think.txt").write_text(
                    thinking, encoding="utf-8")

        errata_reason = check_llm_errata(raw)
        if errata_reason:
            if on_attempt:
                on_attempt(attempt, errata=True)
            if smart_server:
                break  # fall through to smart server
            return None, prompt_kb_total, attempt, [], errata_reason

        output = extract_html(raw)

        errors = validate_html(orig_html, output, txt_fr)
        if not errors:
            return output, prompt_kb_total, attempt, [], None

    # Exhausted retries or errata — try smart server if available
    if smart_server and smart_retries and (errors or errata_reason):
        for smart_attempt in range(1, smart_retries + 1):
            if is_chunked:
                base = build_chunk_prompt(template, orig_html, txt_fr, idx, n)
            else:
                base = build_prompt(template, orig_html, txt_fr)

            if errata_reason and not errors:
                # Normal model flagged errata — tell smart model
                prompt = base + (
                    f"\n\n## ⚠️ Note du modèle précédent\n\n"
                    f"Un modèle moins capable a signalé cette entrée comme"
                    f" ERRATA : « {errata_reason} ».\n"
                    f"Examinez l'entrée et produisez le HTML si possible."
                    f" Si le problème est réel et incontournable,"
                    f" vous pouvez aussi signaler ERRATA.")
                errata_reason = None  # reset so subsequent retries use normal suffix
            else:
                history.append((output, errors))
                prompt = base + _build_retry_suffix(history,
                                                    is_chunk=is_chunked)
            prompt_kb = len(prompt.encode("utf-8")) / 1024
            prompt_kb_total += prompt_kb

            attempt_num = max_retries + smart_attempt
            if on_attempt:
                on_attempt(attempt_num, smart=True)

            if debug:
                dbg = f"/tmp/llm-html-debug-{bdb_id}-smart{smart_attempt}"
                if is_chunked:
                    dbg += f"-chunk{idx}"
                Path(f"{dbg}-prompt.txt").write_text(prompt, encoding="utf-8")

            try:
                raw = query_llm(prompt, smart_server, max_tokens=131072)
            except ContextOverflow:
                break

            if debug:
                Path(f"{dbg}-out.txt").write_text(raw, encoding="utf-8")

            errata_reason = check_llm_errata(raw)
            if errata_reason:
                return None, prompt_kb_total, attempt_num, [], errata_reason

            output = extract_html(raw)
            errors = validate_html(orig_html, output, txt_fr)
            if not errors:
                return output, prompt_kb_total, attempt_num, [], None

    return output, prompt_kb_total, max_retries, errors, None


def process_entry(bdb_id: str, orig_path: Path, txt_path: Path,
                  template: str, server_url: str, max_retries: int,
                  results_path: Path, file_lock: threading.Lock,
                  on_attempt=None, on_chunk=None,
                  debug: bool = False,
                  smart_server: str | None = None,
                  smart_retries: int = 1,
                  ) -> tuple[str, float, int]:
    """Process one entry. Returns (status, prompt_kb, attempts_used).

    Status is one of: CLEAN, FAILED, ERRATA, SKIPPED.
    """
    orig_html = orig_path.read_text()
    french_txt = txt_path.read_text()

    # Split into chunks (or treat whole entry as 1 chunk)
    html_chunks = split_html(orig_html)
    txt_chunks = split_txt(french_txt)

    is_chunked = (len(html_chunks) >= 2
                  and len(html_chunks) == len(txt_chunks))

    if is_chunked:
        n = len(html_chunks)
        orig_parts = [c["html"] for c in html_chunks]
        txt_parts = [c["txt"] for c in txt_chunks]
    else:
        n = 1
        orig_parts = [orig_html]
        txt_parts = [french_txt]

    outputs = [None] * n
    total_prompt_kb = 0.0
    max_attempts = 0

    # Warm start: if a previous Entries_fr exists with errors, seed chunk 0
    fr_path = ENTRIES_FR_DIR / (bdb_id + ".html")
    prev_output = None
    prev_errors: list[str] = []
    if not is_chunked and fr_path.exists():
        prev_output = fr_path.read_text()
        prev_errors = validate_html(orig_html, prev_output, french_txt)
        if not prev_errors:
            return "CLEAN", 0.0, 0

    # Process each chunk with its own retry loop
    failed_chunk = None
    for idx in range(n):
        chunk_prev = prev_output if idx == 0 and not is_chunked else None
        chunk_errs = prev_errors if idx == 0 and not is_chunked else []

        html, kb, attempts, remaining, errata = _generate_chunk(
            bdb_id, idx, n, orig_parts[idx], txt_parts[idx],
            chunk_prev, chunk_errs, template, server_url, max_retries,
            is_chunked,
            on_attempt=on_attempt, on_chunk=on_chunk, debug=debug,
            smart_server=smart_server, smart_retries=smart_retries)

        total_prompt_kb += kb
        max_attempts = max(max_attempts, attempts)

        if errata == "SKIPPED":
            return "SKIPPED", total_prompt_kb, attempts
        if errata:
            chunk_tag = f" (chunk {idx+1}/{n})" if is_chunked else ""
            _write_errata(bdb_id, f"LLM{chunk_tag}: {errata}", file_lock)
            return "ERRATA", total_prompt_kb, attempts

        outputs[idx] = html

        # If this chunk still has errors after exhausting retries, stop —
        # no point generating later chunks when an earlier one is broken.
        if remaining:
            failed_chunk = idx
            break

    # Assemble whatever we have and write to disk
    parts = [o for o in outputs if o is not None]
    if not parts:
        return "FAILED", total_prompt_kb, max_retries

    assembled = "".join(parts)
    fr_path.write_text(assembled, encoding="utf-8")

    if failed_chunk is not None:
        error_summary = "; ".join(remaining[:5])
        _write_errata(bdb_id,
                      f"chunk {failed_chunk+1}/{n} failed after "
                      f"{max_retries} retries: {error_summary}",
                      file_lock)
        return "FAILED", total_prompt_kb, max_attempts

    # Final validation of assembled result (catches cross-chunk issues)
    all_errors = validate_html(orig_html, assembled, french_txt)
    if not all_errors:
        return "CLEAN", total_prompt_kb, max_attempts

    # Assembled result has errors (cross-chunk issues or chunk-level leftovers)
    error_summary = "; ".join(all_errors[:5])
    if len(all_errors) > 5:
        error_summary += f"; ... (+{len(all_errors) - 5} more)"
    _write_errata(bdb_id,
                  f"{len(all_errors)} issues after {max_retries} retries"
                  f"{' (chunked)' if is_chunked else ''}: {error_summary}",
                  file_lock)
    return "FAILED", total_prompt_kb, max_attempts


# ---------------------------------------------------------------------------
# CLI and main loop
# ---------------------------------------------------------------------------

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
    parser.add_argument("--prompt", help="Override prompt template file.")
    parser.add_argument("--entries-dir", help="Override Entries/ directory.")
    parser.add_argument("--txt-fr-dir", help="Override Entries_txt_fr/ directory.")
    parser.add_argument("--output-dir", help="Override Entries_fr/ output directory.")
    parser.add_argument("--results", help="Override results file path.")
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
        help="Write prompt/response to /tmp/llm-html-debug-BDBnnn-tryN-{prompt,out}.txt.",
    )
    parser.add_argument(
        "--smart-server", default=None, metavar="URL",
        help="Fallback LLM server for entries that fail all retries.",
    )
    parser.add_argument(
        "--smart-retries", type=int, default=1, metavar="R",
        help="Max retries on the smart server. Default: 1.",
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
    only = [e.removesuffix(".html") for e in args.entries] if args.entries else None
    entries = get_entries(digits, only=only)

    # Load errata entries for --skip-errata
    errata_ids = set()
    if args.skip_errata:
        for i in range(10):
            ep = ERRATA_DIR / f"errata-{i}.txt"
            if ep.exists():
                for line in ep.read_text().splitlines():
                    if " html  LLM" in line:
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
            errors = validate_file(bdb_id, entries_dir=str(ENTRIES_DIR),
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

    print(f"\nProcessing {len(to_process)} entries ...")
    print(f"  Prompt:      {prompt_path.name}")
    print(f"  Log:         {RESULTS_FILE}")
    print(f"  Normal:      {args.server} ({args.max_retries} retries)")
    if args.smart_server:
        print(f"  Smart:       {args.smart_server} ({args.smart_retries} retries)")
    else:
        print(f"  Smart:       N/A")
    print()

    file_lock = threading.Lock()

    sequential = args.parallel <= 1
    smart_n = args.smart_retries if args.smart_server else 0
    max_try_str = (" try " + " ".join(
        str(n) for n in range(1, args.max_retries + 1))
        + "".join(f" S{n}" for n in range(1, smart_n + 1)))
    max_try_width = len(max_try_str)

    def _is_errata_now(bdb_id):
        """Re-check errata files on disk (another process may have added it)."""
        bdb_num = "".join(c for c in bdb_id if c.isdigit())
        last_digit = bdb_num[-1] if bdb_num else "0"
        ep = ERRATA_DIR / f"errata-{last_digit}.txt"
        if ep.exists():
            for line in ep.read_text().splitlines():
                if line.startswith(bdb_id + " ") and " html  LLM" in line:
                    return True
        return False

    def process_one(i, total, item):
        bdb_id, orig_path, txt_path, chash = item
        filename = bdb_id + ".html"

        # Just-in-time guard: another process may have finished this entry
        fr_path = ENTRIES_FR_DIR / (bdb_id + ".html")
        if not args.force and fr_path.exists():
            orig_html = orig_path.read_text()
            french_txt = txt_path.read_text()
            errs = validate_html(orig_html, fr_path.read_text(), french_txt)
            if not errs:
                return filename, "SKIP", 0.0, "(already clean)"
            if args.skip_failed:
                return filename, "SKIP", 0.0, "(already failed)"
        if args.skip_errata and _is_errata_now(bdb_id):
            return filename, "SKIP", 0.0, "(errata)"

        try_chars = 0

        def on_attempt(n, smart=False, errata=False):
            nonlocal try_chars
            if sequential:
                if errata:
                    if args.smart_server:
                        label = " ERRATA?"
                        s = " \033[1;33mERRATA?\033[0m"
                        try_chars += len(label)
                        sys.stdout.write(s)
                        sys.stdout.flush()
                    return
                if n == 1:
                    return  # silent on first attempt
                if smart:
                    label = f" S{n - args.max_retries}"
                    s = f" \033[1;33mS{n - args.max_retries}\033[0m"
                else:
                    label = s = f" try {n}" if n == 2 else f" {n}"
                try_chars += len(label)
                sys.stdout.write(s)
                sys.stdout.flush()

        def on_chunk(idx, total_chunks, chunk_kb, is_chunked):
            nonlocal try_chars
            if not sequential:
                return
            if is_chunked:
                s = f" {idx + 1}/{total_chunks} {fmt_kb(chunk_kb)}KB"
            else:
                s = f" {fmt_kb(chunk_kb)}KB"
            try_chars += len(s)
            sys.stdout.write(s)
            sys.stdout.flush()

        smart_retries = args.smart_retries if args.smart_server else 0
        status, prompt_kb, attempts = process_entry(
            bdb_id, orig_path, txt_path, template,
            args.server, args.max_retries, RESULTS_FILE, file_lock,
            on_attempt=on_attempt, on_chunk=on_chunk, debug=args.debug,
            smart_server=args.smart_server, smart_retries=smart_retries)

        # Pad try column to fixed width so status aligns
        if sequential and try_chars < max_try_width:
            sys.stdout.write(" " * (max_try_width - try_chars))
            sys.stdout.flush()

        total_max = args.max_retries + smart_retries
        result_note = (f"attempt {attempts}/{total_max}"
                       if attempts > 1 else "")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        save_result(RESULTS_FILE, filename, status, timestamp, chash,
                    result_note, col_filename=COL_FILENAME,
                    col_status=COL_STATUS, lock=file_lock)
        display_note = (f"({attempts}/{total_max})"
                        if attempts > 1 else "")
        return filename, status, prompt_kb, display_note

    def file_size_kb(item):
        _, orig_path, _, _ = item
        return orig_path.stat().st_size / 1024

    counts = run_pipeline(to_process, process_one,
                          name_fn=lambda item: item[0] + ".html",
                          size_fn=file_size_kb,
                          parallel=args.parallel,
                          shuffle=args.shuffle, limit=args.max,
                          label="entries")

    print()
    print(f"Done: {sum(counts.values())} entries processed.")
    from llm_common import _color_status
    print(f"  {_color_status('CLEAN')}:   {counts.get('CLEAN', 0)}")
    print(f"  {_color_status('FAILED')}:  {counts.get('FAILED', 0)}")
    print(f"  {_color_status('ERRATA')}:  {counts.get('ERRATA', 0)}")
    print(f"  {_color_status('SKIPPED')}: {counts.get('SKIPPED', 0)}")
    if counts.get('SKIP', 0):
        print(f"  SKIP:    {counts['SKIP']}  (done by another process)")


if __name__ == "__main__":
    main()
