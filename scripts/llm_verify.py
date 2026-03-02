#!/usr/bin/env python3
"""Verify French translations using a local LLM via llama.cpp server.

Supports three modes (--mode txt/json/html) with appropriate defaults for
directories, prompts, and results files. Results are stored in aligned CSV
format, one line per verification unit:

    BDB1234.txt,              CORRECT, 2026-02-19T14:32:01, a1b2c3d4, "Traduction correcte."
    BDB5678.txt:1/3,          CORRECT, 2026-02-19T14:32:05, e5f6g7h8, "header: OK"
    BDB5678.txt:2/3,          ERROR,   2026-02-19T14:32:10, e5f6g7h8, "stem Qal: 'of king' non traduit"
    BDB5678.txt:3/3,          CORRECT, 2026-02-19T14:32:15, e5f6g7h8, "footer: OK"

For txt mode, entries that split into 2+ aligned chunks (via split_entry)
are verified chunk-by-chunk, producing one row per chunk. Non-chunked
entries produce a single row with the plain filename as key.
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from llm_common import (ContextOverflow, _RESET, _STATUS_COLORS, _USE_COLOR,
                         check_server, file_hash, fmt_kb,
                         load_results, query_llm, run_pipeline, save_result)

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))
from split_entry import split_txt

# Per-mode defaults: (french_dir, english_dir, prompt_file, results_file, extensions)
MODE_DEFAULTS = {
    "txt": (
        "Entries_txt_fr", "Entries_txt",
        "llm_verify_txt.md", "llm_verify_txt_results.txt",
        (".txt",),
    ),
    "json": (
        "json_output_fr", "json_output",
        "llm_verify_json.md", "llm_verify_json_results.txt",
        (".json",),
    ),
    "html": (
        "Entries_fr", "Entries",
        "llm_verify_html.md", "llm_verify_html_results.txt",
        (".html",),
    ),
}

# Column widths for aligned CSV output.
# BDB10012.txt:2/5 = 18 chars, pad to 20
COL_FILENAME = 20
COL_VERDICT = 7


def build_prompt(template: str, english: str, french: str) -> str:
    """Fill template placeholders with English and French texts."""
    return template.replace("{{ENGLISH}}", english).replace("{{FRENCH}}", french)


# Verdict severity ordering for picking the worst
_VERDICT_RANK = {"CORRECT": 0, "WARN": 1, "ERROR": 2}


def _chunk_key(filename: str, idx: int, total: int) -> str:
    """CSV key for a chunk row, e.g. 'BDB7516.txt:2/5'."""
    return f"{filename}:{idx + 1}/{total}"


def _chunk_note_prefix(chunk: dict) -> str:
    """Short prefix for the explanation, e.g. 'stem Qal: ' or 'header: '."""
    ctype = chunk.get("type", "")
    name = chunk.get("name", "")
    if name:
        return f"{ctype} {name}: "
    if ctype:
        return f"{ctype}: "
    return ""


_VERDICT_SHORT = {"CORRECT": "✓", "WARN": "⚠", "ERROR": "✗", "SKIPPED": "–"}


def verify_chunked(template: str, english: str, french: str,
                   filename: str,
                   server_url: str,
                   on_chunk=None,
                   on_verdict=None,
                   debug: bool = False,
                   ) -> list[tuple[str, str, str, float]] | None:
    """Verify an entry chunk-by-chunk if both sides split consistently.

    Returns a list of (csv_key, verdict, explanation, prompt_kb) tuples —
    one per verified chunk. Returns None if chunking isn't applicable
    (fall back to whole-entry).

    on_chunk(idx, total, prompt_kb): called before each LLM query.
    on_verdict(verdict): called after each chunk verdict.
    """
    en_chunks = split_txt(english)
    fr_chunks = split_txt(french)

    # Need matching chunk counts and at least 2 to be worth chunking
    if len(en_chunks) != len(fr_chunks) or len(en_chunks) < 2:
        return None

    results = []
    total = len(en_chunks)

    for idx, (en_c, fr_c) in enumerate(zip(en_chunks, fr_chunks)):
        en_txt = en_c["txt"]
        fr_txt = fr_c["txt"]

        # Skip chunks that are purely structural (empty or markers only)
        en_stripped = en_txt.strip()
        fr_stripped = fr_txt.strip()
        if not en_stripped or not fr_stripped:
            continue
        # Skip very short chunks (just a "---" separator)
        if en_stripped == "---" and fr_stripped == "---":
            continue

        key = _chunk_key(filename, idx, total)
        prefix = _chunk_note_prefix(en_c)

        prompt = build_prompt(template, en_txt, fr_txt)
        prompt_kb = len(prompt.encode("utf-8")) / 1024

        if on_chunk:
            on_chunk(idx, total, prompt_kb)

        stem = filename.rsplit(".", 1)[0]  # BDB50
        dbg_base = f"/tmp/llm-verify/debug-{stem}-chunk{idx}"

        if debug:
            Path(f"{dbg_base}-prompt.txt").write_text(prompt, encoding="utf-8")

        try:
            raw = query_llm(prompt, server_url)
        except ContextOverflow:
            results.append((key, "SKIPPED", f"{prefix}too large", prompt_kb, -1))
            if on_verdict:
                on_verdict("SKIPPED")
            continue

        if debug:
            Path(f"{dbg_base}-out.txt").write_text(raw, encoding="utf-8")

        verdict, explanation, severity = parse_response(raw)
        results.append((key, verdict, f"{prefix}{explanation}", prompt_kb, severity))
        if on_verdict:
            on_verdict(verdict)

    return results


def _extract_severity(token: str, verdict: str) -> int:
    """Extract severity score from the token after the verdict word.

    Expected: 'ERROR 7' or 'CORRECT 0'. Returns -1 if not found.
    """
    rest = token[len(verdict):].strip()
    if rest:
        # Take first word, strip non-digits
        num = rest.split()[0].strip(".,;")
        if num.isdigit():
            return min(int(num), 10)
    return -1


def parse_response(raw: str) -> tuple[str, str, int]:
    """Extract (verdict, explanation, severity) from LLM response.

    Expected format:
        Some analysis text here...
        >>> CORRECT 0

    The verdict line starts with ">>> " followed by CORRECT/WARN/ERROR and
    an optional severity score (0-10). Returns severity=-1 if not provided.
    Falls back to scanning for bare verdict words if no ">>> " prefix found.
    """
    if not raw.strip():
        return "OVERFLOW", "", -1
    lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
    explanation_lines = []
    # First pass: look for ">>> VERDICT" (preferred format)
    for line in lines:
        if line.startswith(">>>"):
            token = line[3:].strip().upper().strip("*").strip()
            for v in ("CORRECT", "ERROR", "WARN"):
                if token.startswith(v):
                    severity = _extract_severity(token, v)
                    explanation = "\n".join(explanation_lines).strip()
                    return v, explanation, severity
        explanation_lines.append(line)
    # Fallback: scan from the end to find the last bare verdict word.
    for line in reversed(lines):
        upper = line.upper().strip("*").strip()
        for v in ("CORRECT", "ERROR", "WARN"):
            if upper.startswith(v):
                severity = _extract_severity(upper, v)
                explanation = "\n".join(l for l in lines if l.strip() != line).strip()
                return v, explanation, severity
    return f"UNKNOWN({raw.strip()[:40]})", raw.strip(), -1


def get_file_pairs(fr_dir: Path, en_dir: Path, extensions: tuple[str, ...],
                   digits: list[int] | None) -> list[tuple[str, Path, Path]]:
    """Get sorted list of (filename, english_path, french_path) pairs."""
    pairs = []
    for fr_path in sorted(fr_dir.iterdir()):
        if not fr_path.name.endswith(extensions):
            continue
        if digits is not None:
            num_str = "".join(c for c in fr_path.stem if c.isdigit())
            if num_str and int(num_str[-1]) not in digits:
                continue
        en_path = en_dir / fr_path.name
        if en_path.exists():
            pairs.append((fr_path.name, en_path, fr_path))
    return pairs


def main():
    parser = argparse.ArgumentParser(
        description="Verify French BDB translations using a local LLM (llama.cpp server).",
        epilog="""Examples:
  %(prog)s                              # check txt translations (default)
  %(prog)s --mode json                  # check JSON translations
  %(prog)s --mode html                  # check HTML translations
  %(prog)s --mode txt 0 3 7            # only BDB numbers ending in 0, 3, 7
  %(prog)s --mode json --count          # how many JSON files left to check
  %(prog)s --mode txt -n 50            # stop after 50 files
  %(prog)s --server http://localhost:9090  # non-default server port

Modes and their defaults:
  txt:   Entries_txt_fr/ vs Entries_txt/    → llm_verify_txt_results.txt
  json:  json_output_fr/ vs json_output/   → llm_verify_json_results.txt
  html:  Entries_fr/     vs Entries/        → llm_verify_html_results.txt""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "digits", nargs="*", type=int, metavar="DIGIT",
        help="Filter by last digit of BDB number (0-9). Default: all.",
    )
    parser.add_argument(
        "--mode", choices=("txt", "json", "html"), default="txt",
        help="What to verify: txt (default), json, or html.",
    )
    parser.add_argument(
        "--dir",
        help="Override French directory (default: per mode).",
    )
    parser.add_argument(
        "--source-dir",
        help="Override English source directory (default: per mode).",
    )
    parser.add_argument(
        "--results",
        help="Override results file (default: per mode).",
    )
    parser.add_argument(
        "--server", default="http://127.0.0.1:8080",
        help="llama.cpp server URL (default: http://127.0.0.1:8080).",
    )
    parser.add_argument(
        "--prompt",
        help="Override prompt template file (default: per mode).",
    )
    parser.add_argument(
        "--count", action="store_true",
        help="Just show how many files need checking, don't run.",
    )
    parser.add_argument(
        "-n", "--max", type=int, default=0, metavar="N",
        help="Stop after N files (0 = unlimited).",
    )
    parser.add_argument(
        "-j", "--parallel", type=int, default=1, metavar="J",
        help="Number of parallel LLM requests (requires server started with -np J). Default: 1.",
    )
    parser.add_argument(
        "--shuffle", action="store_true", default=False,
        help="Randomize file order.",
    )
    parser.add_argument(
        "--debug", action="store_true", default=False,
        help="Write prompt/response to /tmp/llm-verify/debug-BDBnnn-{prompt,out}.txt.",
    )
    args = parser.parse_args()

    # Apply mode defaults
    fr_dir_name, en_dir_name, prompt_name, results_name, extensions = MODE_DEFAULTS[args.mode]

    fr_dir = ROOT / (args.dir or fr_dir_name)
    en_dir = ROOT / (args.source_dir or en_dir_name)
    results_path = ROOT / (args.results or results_name)
    prompt_path = Path(args.prompt) if args.prompt else SCRIPT_DIR / prompt_name

    # Ensure tmp directory and files are group-writable
    os.umask(0o002)
    if args.debug:
        Path("/tmp/llm-verify").mkdir(mode=0o775, exist_ok=True)

    if not fr_dir.is_dir():
        print(f"error: French directory not found: {fr_dir}", file=sys.stderr)
        sys.exit(1)

    if not en_dir.is_dir():
        print(f"error: English source directory not found: {en_dir}", file=sys.stderr)
        sys.exit(1)

    if not prompt_path.exists():
        print(f"error: prompt template not found: {prompt_path}", file=sys.stderr)
        sys.exit(1)

    template = prompt_path.read_text()

    # Get file pairs
    digits = args.digits if args.digits else None
    pairs = get_file_pairs(fr_dir, en_dir, extensions, digits)

    # Load existing results and figure out what needs checking.
    # Results may have chunk keys like "BDB7516.txt:2/5" or plain filenames.
    # A file is "done" if its plain key matches hash, OR if any chunk key
    # for that filename matches hash (chunk keys share the same hash).
    existing = load_results(results_path)

    def _file_done(filename: str, fhash: str) -> bool:
        """Check if this file (plain or chunked) is already verified."""
        # Plain key match
        if filename in existing and existing[filename][2] == fhash:
            return True
        # Check for any chunk key like "filename:N/M"
        prefix = filename + ":"
        for key, (_, _, khash) in existing.items():
            if key.startswith(prefix) and khash == fhash:
                return True
        return False

    to_check = []
    for filename, en_path, fr_path in pairs:
        fhash = file_hash(fr_path)
        if _file_done(filename, fhash):
            continue
        to_check.append((filename, en_path, fr_path, fhash))

    if args.count:
        total = len(pairs)
        done = total - len(to_check)
        print(f"{args.mode}: {total} total, {done} done, {len(to_check)} remaining")
        if existing:
            counts = {"CORRECT": 0, "WARN": 0, "ERROR": 0}
            n_chunks = 0
            for key, (v, _, _) in existing.items():
                counts[v] = counts.get(v, 0) + 1
                if ":" in key and "/" in key.split(":")[-1]:
                    n_chunks += 1
            chunk_note = f" ({n_chunks} chunk rows)" if n_chunks else ""
            print(f"  Results so far: {counts.get('CORRECT', 0)} correct, "
                  f"{counts.get('WARN', 0)} warn, "
                  f"{counts.get('ERROR', 0)} error{chunk_note}")
        sys.exit(0)

    if not to_check:
        print(f"All {len(pairs)} files already verified (results in {results_path.name}).")
        sys.exit(0)

    check_server(args.server)

    print(f"Checking {len(to_check)} {args.mode} files via {args.server} ...")
    print(f"Prompt:  {prompt_path.name}")
    print(f"Results: {results_path.name}")
    print()

    import threading
    file_lock = threading.Lock()

    sequential = args.parallel <= 1

    def process_one(i, total, item):
        filename, en_path, fr_path, fhash = item
        english = en_path.read_text()
        french = fr_path.read_text()

        def on_chunk(idx, n, prompt_kb):
            if sequential:
                s = f" {idx + 1}/{n} {fmt_kb(prompt_kb)}KB"
                sys.stdout.write(s)
                sys.stdout.flush()

        def on_verdict(verdict):
            if sequential:
                short = _VERDICT_SHORT.get(verdict, "?")
                color = _STATUS_COLORS.get(verdict, "") if _USE_COLOR else ""
                reset = _RESET if color else ""
                sys.stdout.write(f" {color}{short}{reset}")
                sys.stdout.flush()

        # Try chunked verification first (txt mode, 2+ aligned chunks)
        if args.mode == "txt":
            chunk_results = verify_chunked(
                template, english, french, filename, args.server,
                on_chunk=on_chunk, on_verdict=on_verdict,
                debug=args.debug)
            if chunk_results is not None:
                timestamp = datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%S")
                worst = "CORRECT"
                worst_sev = 0
                total_kb = 0.0
                for key, verdict, explanation, kb, severity in chunk_results:
                    total_kb += kb
                    if _VERDICT_RANK.get(verdict, 2) > _VERDICT_RANK.get(worst, 0):
                        worst = verdict
                    if severity > worst_sev:
                        worst_sev = severity
                    save_result(results_path, key, verdict, timestamp,
                                fhash, explanation, severity=severity,
                                col_filename=COL_FILENAME,
                                col_status=COL_VERDICT, lock=file_lock)
                sev_note = str(worst_sev) if worst_sev > 0 else ""
                return filename, worst, total_kb, sev_note

        # Whole-entry fallback (non-chunked txt, json, html)
        prompt = build_prompt(template, english, french)
        prompt_kb = len(prompt.encode("utf-8")) / 1024

        stem = filename.rsplit(".", 1)[0]
        if args.debug:
            Path(f"/tmp/llm-verify/debug-{stem}-prompt.txt").write_text(
                prompt, encoding="utf-8")

        try:
            raw = query_llm(prompt, args.server)
        except ContextOverflow:
            save_result(results_path, filename, "SKIPPED",
                        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                        fhash, "too large for context window",
                        col_filename=COL_FILENAME, col_status=COL_VERDICT,
                        lock=file_lock)
            return filename, "SKIPPED", prompt_kb, ""

        if args.debug:
            Path(f"/tmp/llm-verify/debug-{stem}-out.txt").write_text(
                raw, encoding="utf-8")

        verdict, explanation, severity = parse_response(raw)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        save_result(results_path, filename, verdict, timestamp, fhash,
                    explanation, severity=severity, col_filename=COL_FILENAME,
                    col_status=COL_VERDICT, lock=file_lock)
        sev_note = str(severity) if severity > 0 else ""
        return filename, verdict, prompt_kb, sev_note

    def file_size_kb(item):
        """French file size in KB (shown before LLM call starts)."""
        _, _, fr_path, _ = item
        return fr_path.stat().st_size / 1024

    counts = run_pipeline(to_check, process_one,
                          name_fn=lambda item: item[0],
                          size_fn=file_size_kb,
                          parallel=args.parallel,
                          shuffle=args.shuffle, limit=args.max,
                          label="files")

    print()
    print(f"Done: {len(to_check)} files checked.")
    from llm_common import _color_status
    print(f"  {_color_status('CORRECT')}: {counts.get('CORRECT', 0)}")
    print(f"  {_color_status('WARN')}:    {counts.get('WARN', 0)}")
    print(f"  {_color_status('ERROR')}:   {counts.get('ERROR', 0)}")
    other = sum(v for k, v in counts.items() if k not in ("CORRECT", "WARN", "ERROR"))
    if other:
        print(f"  OTHER:   {other}")


if __name__ == "__main__":
    main()
