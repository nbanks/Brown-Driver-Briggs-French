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


def save_result(results_path: Path, filename: str, status: str,
                timestamp: str, fhash: str, note: str = "",
                col_filename: int = 16, col_status: int = 7,
                max_note_len: int = 1024, lock: "threading.Lock | None" = None):
    """Append one result line in aligned CSV format."""
    fn_field = f"{filename},".ljust(col_filename + 1)
    st_field = f"{status},".ljust(col_status + 1)
    line = f"{fn_field} {st_field} {timestamp}, {fhash}"
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
              max_tokens: int = 2048) -> str:
    """Send a chat completion request and return the content.

    Uses /v1/chat/completions. On thinking models, if content is empty,
    falls back to scanning reasoning_content for a verdict keyword.
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
            if content:
                return content
            # Thinking model may exhaust tokens on reasoning with no content.
            reasoning = (msg.get("reasoning_content") or "").strip().upper()
            for v in ("ERROR", "WARN", "CORRECT"):
                if v in reasoning:
                    last_pos = reasoning.rfind(v)
                    return reasoning[last_pos:last_pos + len(v)]
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


def run_pipeline(items, process_fn, *, name_fn=None, parallel=1, shuffle=False,
                 limit=0, label="files"):
    """Execute process_fn over items with progress, ETA, and graceful shutdown.

    items: list of work items (any type — passed to process_fn).
    process_fn(i, total, item) -> (display_name, status, prompt_kb[, note])
        Called for each item. i is 1-based index, total is len(work list).
        Returns a tuple for display. Optional 4th element is a short note
        shown after the status (e.g. "retry 2/3").
    name_fn(item) -> str: optional callback to extract a display name from an
        item. In sequential mode this is called *before* process_fn so the
        filename is visible while the LLM is working.
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
    elapsed_times = []  # all individual times, for avg display
    completed = 0
    print_lock = threading.Lock()
    shutdown_requested = threading.Event()
    futures = {}

    # The first `parallel` entries fill the prompt cache and are much slower.
    # Exclude them from ETA once we have enough cached-speed samples.
    warmup = parallel

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
            completed += 1
            elapsed_times.append(elapsed)
            counts[status] = counts.get(status, 0) + 1

            # ETA: use all times initially, drop warmup batch once we
            # have post-warmup samples (prompt cache is hot by then).
            if completed > warmup:
                cached_times = elapsed_times[warmup:]
                avg = sum(cached_times) / len(cached_times)
            else:
                avg = sum(elapsed_times) / len(elapsed_times)
            items_left = total - completed
            remaining = avg / max(parallel, 1) * items_left
            eta_m, eta_s = divmod(int(remaining), 60)
            eta_h, eta_m = divmod(eta_m, 60)
            if eta_h:
                eta_str = f"{eta_h}h{eta_m:02d}m"
            else:
                eta_str = f"{eta_m}m{eta_s:02d}s"

            status_str = status
            if note:
                status_str += f" {note}"
            suffix = (f"  {status_str:<7s} {elapsed:6.1f}s "
                      f"avg={avg:5.1f}s ETA {eta_str}")
            if show_progress:
                # Sequential mode: prefix + attempt numbers already on line
                print(suffix)
            else:
                # Parallel mode: print full line
                if prompt_kb > 0:
                    prefix = f"{i}/{total} {display_name:<16s} {prompt_kb:5.0f}KB"
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
