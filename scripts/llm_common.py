"""Shared infrastructure for LLM pipeline scripts (verify, assemble, etc.).

Provides: results file I/O, LLM querying, parallel execution with graceful
shutdown, progress display with ETA.
"""

import hashlib
import random
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("error: 'requests' module not found. Install with: pip install requests",
          file=sys.stderr)
    sys.exit(1)


class ContextOverflow(Exception):
    """Raised when the prompt exceeds the server's context window."""


# ANSI color helpers (disabled when stdout is not a terminal)
_USE_COLOR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

_STATUS_COLORS = {
    "CLEAN":   "\033[32m",  # green
    "CORRECT": "\033[32m",  # green
    "FAILED":  "\033[31m",  # red
    "ERROR":   "\033[31m",  # red
    "ERRATA":  "\033[33m",  # yellow
    "WARN":    "\033[33m",  # yellow
    "SKIPPED": "\033[36m",  # cyan
}
_RESET = "\033[0m"


def _color_status(status: str) -> str:
    """Wrap status text in ANSI color if outputting to a terminal."""
    if _USE_COLOR and status in _STATUS_COLORS:
        return f"{_STATUS_COLORS[status]}{status}{_RESET}"
    return status


def fmt_kb(kb: float) -> str:
    """Format a KB value as an integer string, minimum 1."""
    return str(max(1, round(kb)))


def file_hash(path: Path) -> str:
    """Short SHA-256 hex digest (first 8 chars) of file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def combined_hash(*paths: Path) -> str:
    """Hash of multiple files combined (detects changes to any)."""
    h = hashlib.sha256()
    for p in paths:
        h.update(p.read_bytes())
    return h.hexdigest()[:8]


def load_results(results_path: Path) -> dict[str, tuple[str, str, str]]:
    """Load existing results as {filename: (status, timestamp, hash)}.

    Later lines for the same filename overwrite earlier ones (newest wins).
    Handles both old (4-field) and new (5-field with severity) CSV formats.
    """
    results = {}
    if not results_path.exists():
        return results
    for line in results_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = [f.strip().strip('"') for f in line.split(",")]
        if len(fields) >= 5 and fields[2].strip().lstrip("-").isdigit():
            # New format: filename, status, severity, timestamp, hash[, note]
            results[fields[0]] = (fields[1], fields[3], fields[4])
        elif len(fields) >= 4:
            # Old format: filename, status, timestamp, hash[, note]
            results[fields[0]] = (fields[1], fields[2], fields[3])
    return results


def save_result(results_path: Path, filename: str, status: str,
                timestamp: str, fhash: str, note: str = "",
                severity: int = -1,
                col_filename: int = 16, col_status: int = 7,
                max_note_len: int = 1024, lock: "threading.Lock | None" = None):
    """Append one result line in aligned CSV format."""
    fn_field = f"{filename},".ljust(col_filename + 1)
    st_field = f"{status},".ljust(col_status + 1)
    sev_field = f"{severity:>3d}," if severity >= 0 else "   ,"
    line = f"{fn_field} {st_field} {sev_field} {timestamp}, {fhash}"
    if note:
        clean = note.replace("\n", " ").replace("\t", " ").strip()
        clean = clean.replace('"', "'")
        if len(clean) > max_note_len:
            clean = clean[:max_note_len - 3] + "..."
        line += f', "{clean}"'
    if lock:
        with lock:
            with open(results_path, "a") as f:
                f.write(line + "\n")
    else:
        with open(results_path, "a") as f:
            f.write(line + "\n")


def query_llm(prompt: str, server_url: str, retries: int = 5,
              max_tokens: int = 2048,
              return_reasoning: bool = False) -> str | tuple[str, str]:
    """Send a chat completion request and return the content.

    Uses /v1/chat/completions. On thinking models, if content is empty,
    falls back to scanning reasoning_content for a verdict keyword.

    If return_reasoning is True, returns (content, reasoning_content) tuple.
    """
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "reasoning_effort": "low",
    }
    for attempt in range(retries):
        try:
            resp = requests.post(f"{server_url}/v1/chat/completions",
                                 json=payload, timeout=5400)
            if resp.status_code == 400:
                raise ContextOverflow(
                    f"prompt too large for context window ({len(prompt)} chars)")
            resp.raise_for_status()
            data = resp.json()
            msg = data["choices"][0]["message"]
            content = (msg.get("content") or "").strip()
            reasoning = (msg.get("reasoning_content") or "").strip()
            if content:
                if "<think>" in content:
                    raise RuntimeError(
                        "Server returned <think> tags in content. "
                        "Use --reasoning-budget 0 on the server to disable thinking.")
                if return_reasoning:
                    return content, reasoning
                return content
            # Thinking model may exhaust tokens on reasoning with no content.
            reasoning_upper = reasoning.upper()
            for v in ("ERROR", "WARN", "CORRECT"):
                if v in reasoning_upper:
                    last_pos = reasoning_upper.rfind(v)
                    fallback = reasoning_upper[last_pos:last_pos + len(v)]
                    if return_reasoning:
                        return fallback, reasoning
                    return fallback
            if return_reasoning:
                return "", reasoning
            return ""
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < retries - 1:
                print(f"  connection error, retrying in 5s... ({e})",
                      file=sys.stderr)
                time.sleep(5)
            else:
                raise


def check_server(server_url: str):
    """Check that the LLM server is reachable, exit with message if not."""
    try:
        health = requests.get(f"{server_url}/health", timeout=5)
        health.raise_for_status()
    except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
        print("error: cannot connect to llama.cpp server at " + server_url,
              file=sys.stderr)
        print("Start a server first, e.g.: llama qwen3.5", file=sys.stderr)
        sys.exit(1)


def run_pipeline(items, process_fn, *, name_fn=None, size_fn=None,
                 parallel=1, shuffle=False, limit=0, label="files"):
    """Execute process_fn over items with progress, ETA, and graceful shutdown.

    items: list of work items (any type — passed to process_fn).
    process_fn(i, total, item) -> (display_name, status, prompt_kb[, note])
        Called for each item. i is 1-based index, total is len(work list).
        Returns a tuple for display. Optional 4th element is a short note
        shown after the status (e.g. "retry 2/3").
    name_fn(item) -> str: optional callback to extract a display name from an
        item. In sequential mode this is called *before* process_fn so the
        filename is visible while the LLM is working.
    size_fn(item) -> float: optional callback returning prompt size in KB,
        shown in the sequential-mode prefix before the LLM call starts.
    parallel: number of concurrent workers.
    shuffle: randomize order before processing.
    limit: stop after this many (0 = unlimited).
    label: noun for progress messages ("files", "entries", etc.).

    Returns dict of {status: count}.
    """
    if shuffle:
        random.shuffle(items)
    if limit > 0:
        items = items[:limit]

    if not items:
        return {}

    # Note on thread safety: completed and total_time are nonlocal ints/floats
    # mutated under print_lock. In CPython the GIL makes int/float += atomic,
    # but we hold the lock anyway for the surrounding print logic. True thread
    # parallelism isn't needed here — the LLM server call dominates wall time
    # (>99%), so Python threads just manage concurrent I/O waits.
    counts = {}
    elapsed_times = []  # post-warmup times only, for avg/ETA
    completed = 0
    print_lock = threading.Lock()
    shutdown_requested = threading.Event()
    futures = {}

    # The first `parallel` items fill the prompt cache and are slower.
    # Track them by original index; once all have completed, discard
    # everything accumulated so far and start fresh.
    warmup_indices = set(range(1, parallel + 1))  # 1-based
    warmup_done = (parallel <= 1)  # no warmup needed for single worker
    warmup_pending = set(warmup_indices) if not warmup_done else set()

    def handle_sigint(signum, frame):
        if shutdown_requested.is_set():
            print("\nForced exit.", file=sys.stderr)
            sys.exit(1)
        shutdown_requested.set()
        in_flight = len(futures) if parallel > 1 else 1
        print(f"\n\nCtrl+C received -- waiting for {in_flight} in-flight "
              f"request{'s' if in_flight != 1 else ''} to finish. "
              "Press Ctrl+C again to force quit.", file=sys.stderr)

    signal.signal(signal.SIGINT, handle_sigint)

    total = len(items)

    def do_one(i, item, show_progress=False):
        nonlocal completed

        t0 = time.monotonic()
        result = process_fn(i, total, item)
        elapsed = time.monotonic() - t0
        display_name, status, prompt_kb = result[:3]
        note = result[3] if len(result) > 3 else ""

        with print_lock:
            nonlocal warmup_done
            completed += 1
            counts[status] = counts.get(status, 0) + 1

            # Track warmup: once all initial `parallel` indices finish,
            # discard accumulated times and start fresh.
            if not warmup_done:
                warmup_pending.discard(i)
                if not warmup_pending:
                    warmup_done = True
                    elapsed_times.clear()
            if warmup_done:
                elapsed_times.append(elapsed)

            if elapsed_times:
                avg = sum(elapsed_times) / len(elapsed_times)
            else:
                avg = elapsed
            items_left = total - completed
            remaining = avg / max(parallel, 1) * items_left
            eta_m, eta_s = divmod(int(remaining), 60)
            eta_h, eta_m = divmod(eta_m, 60)
            if eta_h:
                eta_str = f"{eta_h}h{eta_m:02d}m"
            else:
                eta_str = f"{eta_m}m{eta_s:02d}s"

            status_pad = f"{status:<7s}"
            if note:
                status_pad = f"{status} {note}"
                # Pad to at least 7+len(note) so timing still aligns
                status_pad = f"{status_pad:<16s}"
            colored = _color_status(status) + status_pad[len(status):]
            suffix = (f"  {colored} {elapsed:6.1f}s "
                      f"avg={avg:5.1f}s ETA {eta_str}")
            if show_progress:
                # Sequential mode: prefix + attempt numbers already on line
                print(suffix)
            else:
                # Parallel mode: print full line
                if prompt_kb > 0:
                    prefix = f"{i}/{total} {display_name:<16s} {fmt_kb(prompt_kb):>5s}KB"
                else:
                    prefix = f"{i}/{total} {display_name:<16s}"
                print(f"{prefix}{suffix}")

        return display_name, status

    if parallel <= 1:
        for i, item in enumerate(items, 1):
            if shutdown_requested.is_set():
                print(f"\nStopping: {completed}/{total} done.",
                      file=sys.stderr)
                break
            # Print filename before LLM call so user sees what's in progress
            if name_fn:
                prefix = f"{i}/{total} {name_fn(item):<16s}"
                if size_fn:
                    prefix += f" {fmt_kb(size_fn(item)):>5s}KB"
                sys.stdout.write(prefix)
                sys.stdout.flush()
            try:
                do_one(i, item, show_progress=bool(name_fn))
            except Exception as e:
                print(f"\n  fatal: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        with ThreadPoolExecutor(max_workers=parallel) as pool:
            futures.clear()
            it = iter(enumerate(items, 1))

            for _ in range(parallel):
                nxt = next(it, None)
                if nxt is None:
                    break
                i, item = nxt
                fut = pool.submit(do_one, i, item)
                futures[fut] = i

            while futures:
                done = next(as_completed(futures))
                idx = futures.pop(done)
                try:
                    done.result()
                except Exception as e:
                    print(f"\n  fatal: {e}", file=sys.stderr)
                    pool.shutdown(wait=False, cancel_futures=True)
                    sys.exit(1)
                if not shutdown_requested.is_set():
                    nxt = next(it, None)
                    if nxt is not None:
                        i, item = nxt
                        fut = pool.submit(do_one, i, item)
                        futures[fut] = i

    return counts
