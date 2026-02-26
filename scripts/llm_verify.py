#!/usr/bin/env python3
"""Verify French translations using a local LLM via llama.cpp server.

Supports three modes (--mode txt/json/html) with appropriate defaults for
directories, prompts, and results files. Results are stored one line per
file in aligned CSV format (readable as both CSV and plain text):

    BDB1234.txt,            CORRECT, 2026-02-19T14:32:01, a1b2c3d4, "Traduction correcte, refs bibliques ok."
    BDB5678.txt,            ERROR,   2026-02-19T14:32:05, e5f6g7h8, "«of king» non traduit ligne 6."
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from llm_common import (ContextOverflow, check_server, file_hash,
                         load_results, query_llm, run_pipeline, save_result)

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent

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
COL_FILENAME = 13
COL_VERDICT = 7


def build_prompt(template: str, english: str, french: str) -> str:
    return template.replace("{{ENGLISH}}", english).replace("{{FRENCH}}", french)


def parse_response(raw: str) -> tuple[str, str]:
    """Extract (verdict, explanation) from LLM response.

    Expected format:
        Some analysis text here...
        >>> CORRECT

    The verdict line starts with ">>> " followed by CORRECT/WARN/ERROR.
    Falls back to scanning for bare verdict words if no ">>> " prefix found.
    """
    if not raw.strip():
        return "OVERFLOW", ""
    lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
    explanation_lines = []
    # First pass: look for ">>> VERDICT" (preferred format)
    for line in lines:
        if line.startswith(">>>"):
            token = line[3:].strip().upper().strip("*").strip()
            for v in ("CORRECT", "ERROR", "WARN"):
                if token.startswith(v):
                    explanation = "\n".join(explanation_lines).strip()
                    return v, explanation
        explanation_lines.append(line)
    # Fallback: scan from the end to find the last bare verdict word.
    for line in reversed(lines):
        upper = line.upper().strip("*").strip()
        for v in ("CORRECT", "ERROR", "WARN"):
            if upper.startswith(v):
                explanation = "\n".join(l for l in lines if l.strip() != line).strip()
                return v, explanation
    return f"UNKNOWN({raw.strip()[:40]})", raw.strip()


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
    args = parser.parse_args()

    # Apply mode defaults
    fr_dir_name, en_dir_name, prompt_name, results_name, extensions = MODE_DEFAULTS[args.mode]

    fr_dir = ROOT / (args.dir or fr_dir_name)
    en_dir = ROOT / (args.source_dir or en_dir_name)
    results_path = ROOT / (args.results or results_name)
    prompt_path = Path(args.prompt) if args.prompt else SCRIPT_DIR / prompt_name

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

    # Load existing results and figure out what needs checking
    existing = load_results(results_path)

    to_check = []
    for filename, en_path, fr_path in pairs:
        fhash = file_hash(fr_path)
        if filename in existing and existing[filename][2] == fhash:
            continue
        to_check.append((filename, en_path, fr_path, fhash))

    if args.count:
        total = len(pairs)
        done = total - len(to_check)
        print(f"{args.mode}: {total} total, {done} done, {len(to_check)} remaining")
        if existing:
            counts = {"CORRECT": 0, "WARN": 0, "ERROR": 0}
            for v, _, _ in existing.values():
                counts[v] = counts.get(v, 0) + 1
            print(f"  Results so far: {counts.get('CORRECT', 0)} correct, "
                  f"{counts.get('WARN', 0)} warn, {counts.get('ERROR', 0)} error")
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

    def process_one(i, total, item):
        filename, en_path, fr_path, fhash = item
        english = en_path.read_text()
        french = fr_path.read_text()
        prompt = build_prompt(template, english, french)
        prompt_kb = len(prompt.encode("utf-8")) / 1024

        try:
            raw = query_llm(prompt, args.server)
        except ContextOverflow:
            save_result(results_path, filename, "SKIPPED",
                        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                        fhash, "too large for context window",
                        col_filename=COL_FILENAME, col_status=COL_VERDICT,
                        lock=file_lock)
            return filename, "SKIPPED", prompt_kb

        verdict, explanation = parse_response(raw)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        save_result(results_path, filename, verdict, timestamp, fhash,
                    explanation, col_filename=COL_FILENAME,
                    col_status=COL_VERDICT, lock=file_lock)
        return filename, verdict, prompt_kb

    def prompt_size_kb(item):
        """Estimate prompt size in KB before sending to LLM."""
        _, en_path, fr_path, _ = item
        size = (len(template.encode("utf-8"))
                + en_path.stat().st_size + fr_path.stat().st_size)
        return size / 1024

    counts = run_pipeline(to_check, process_one,
                          name_fn=lambda item: item[0],
                          size_fn=prompt_size_kb,
                          parallel=args.parallel,
                          shuffle=args.shuffle, limit=args.max,
                          label="files")

    print()
    print(f"Done: {len(to_check)} files checked.")
    print(f"  CORRECT: {counts.get('CORRECT', 0)}")
    print(f"  WARN:    {counts.get('WARN', 0)}")
    print(f"  ERROR:   {counts.get('ERROR', 0)}")
    other = sum(v for k, v in counts.items() if k not in ("CORRECT", "WARN", "ERROR"))
    if other:
        print(f"  OTHER:   {other}")


if __name__ == "__main__":
    main()
