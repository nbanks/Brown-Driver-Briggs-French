#!/usr/bin/env python3
"""Verify French translations using a local LLM via llama.cpp server.

Supports three modes (--mode txt/json/html) with appropriate defaults for
directories, prompts, and results files. Results are stored one line per
file in aligned CSV format (readable as both CSV and plain text):

    BDB1234.txt,            CORRECT, 2026-02-19T14:32:01, a1b2c3d4, "Traduction correcte, refs bibliques ok."
    BDB5678.txt,            ERROR,   2026-02-19T14:32:05, e5f6g7h8, "«of king» non traduit ligne 6."
"""

import argparse
import hashlib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("error: 'requests' module not found. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

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


def file_hash(path: Path) -> str:
    """Short SHA-256 hex digest (first 8 chars) of file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def load_results(results_path: Path) -> dict[str, tuple[str, str, str]]:
    """Load existing results as {filename: (verdict, timestamp, hash)}.

    Later lines for the same filename overwrite earlier ones (newest wins).
    """
    results = {}
    if not results_path.exists():
        return results
    for line in results_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = [f.strip().strip('"') for f in line.split(",")]
        if len(fields) >= 4:
            results[fields[0]] = (fields[1], fields[2], fields[3])
    return results


# Column widths for aligned CSV output.
# filename: 13 covers BDB10022.html (longest real filename).
# verdict:  7 covers CORRECT (longest verdict).
COL_FILENAME = 13
COL_VERDICT = 7


def save_result(results_path: Path, filename: str, verdict: str, timestamp: str,
                fhash: str, explanation: str = ""):
    """Append one result line in aligned CSV format."""
    fn_field = f"{filename},".ljust(COL_FILENAME + 1)
    vd_field = f"{verdict},".ljust(COL_VERDICT + 1)
    line = f"{fn_field} {vd_field} {timestamp}, {fhash}"
    if explanation:
        clean = explanation.replace("\n", " ").replace("\t", " ").strip()
        clean = clean.replace('"', "'")
        if len(clean) > 200:
            clean = clean[:197] + "..."
        line += f', "{clean}"'
    with open(results_path, "a") as f:
        f.write(line + "\n")


def build_prompt(template: str, english: str, french: str) -> str:
    return template.replace("{{ENGLISH}}", english).replace("{{FRENCH}}", french)


def query_llm(prompt: str, server_url: str, retries: int = 3) -> str:
    """Send a chat completion request and return the content (verdict).

    Uses /v1/chat/completions which separates reasoning_content from
    the final content, so we get a clean verdict even with thinking models.
    Prompt caching still works — llama.cpp matches the common token prefix
    across requests on the same slot.

    # TODO: investigate reducing thinking budget for faster throughput.
    # gpt-oss-20b uses ~1000 thinking tokens per file (~11s at 100 t/s).
    # A non-thinking model or reasoning_effort control could cut this to <1s.
    """
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 16384,
        "temperature": 0,
        "reasoning_effort": "low",  # reduce thinking budget on reasoning models
    }
    for attempt in range(retries):
        try:
            resp = requests.post(f"{server_url}/v1/chat/completions",
                                 json=payload, timeout=300)
            resp.raise_for_status()
            data = resp.json()
            msg = data["choices"][0]["message"]
            content = (msg.get("content") or "").strip()
            if content:
                return content
            # Thinking model may exhaust tokens on reasoning with no content.
            # Try to extract a verdict from reasoning_content as fallback.
            reasoning = (msg.get("reasoning_content") or "").strip().upper()
            for v in ("ERROR", "WARN", "CORRECT"):
                if v in reasoning:
                    last_pos = reasoning.rfind(v)
                    return reasoning[last_pos:last_pos + len(v)]
            return ""
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < retries - 1:
                print(f"  connection error, retrying in 5s... ({e})", file=sys.stderr)
                time.sleep(5)
            else:
                raise


def parse_response(raw: str) -> tuple[str, str]:
    """Extract (verdict, explanation) from LLM response.

    Expected format:
        Some analysis text here...
        >>> CORRECT

    The verdict line starts with ">>> " followed by CORRECT/WARN/ERROR.
    Falls back to scanning for bare verdict words if no ">>> " prefix found.
    Returns (verdict_str, explanation_str).
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
    # Fallback: scan lines from the end for a bare verdict word
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
        # Filter by last digit of BDB number
        if digits is not None:
            num_str = "".join(c for c in fr_path.stem if c.isdigit())
            if num_str and int(num_str[-1]) not in digits:
                continue
        en_path = en_dir / fr_path.name
        if en_path.exists():
            # Skip empty files (skeleton entries)
            if fr_path.stat().st_size == 0:
                continue
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
        "digits", nargs="*", type=int, choices=range(10), metavar="DIGIT",
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
            continue  # already checked and file hasn't changed
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

    # Check that the llama.cpp server is running
    try:
        health = requests.get(f"{args.server}/health", timeout=5)
        health.raise_for_status()
    except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
        print("error: cannot connect to llama.cpp server at " + args.server, file=sys.stderr)
        print("", file=sys.stderr)
        print("Start a server in another terminal first, e.g.:", file=sys.stderr)
        print("  llama mistral-small", file=sys.stderr)
        print("", file=sys.stderr)
        print("Then re-run this script.", file=sys.stderr)
        sys.exit(1)

    limit = args.max if args.max > 0 else len(to_check)
    to_check = to_check[:limit]

    print(f"Checking {len(to_check)} {args.mode} files via {args.server} ...")
    print(f"Prompt:  {prompt_path.name}")
    print(f"Results: {results_path.name}")
    print()

    counts = {"CORRECT": 0, "WARN": 0, "ERROR": 0}
    for i, (filename, en_path, fr_path, fhash) in enumerate(to_check, 1):
        english = en_path.read_text()
        french = fr_path.read_text()
        prompt = build_prompt(template, english, french)

        try:
            raw = query_llm(prompt, args.server)
        except Exception as e:
            print(f"\n  fatal: LLM request failed for {filename}: {e}", file=sys.stderr)
            print(f"  Processed {i - 1}/{len(to_check)} files before error.", file=sys.stderr)
            sys.exit(1)

        verdict, explanation = parse_response(raw)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        save_result(results_path, filename, verdict, timestamp, fhash, explanation)

        counts[verdict] = counts.get(verdict, 0) + 1
        symbol = {"CORRECT": ".", "WARN": "W", "ERROR": "X", "OVERFLOW": "O"}.get(verdict, "?")
        sys.stdout.write(symbol)
        sys.stdout.flush()
        if i % 80 == 0:
            sys.stdout.write(f"  [{i}/{len(to_check)}]\n")
            sys.stdout.flush()

    print()
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
