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
import os
import queue
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from llm_common import (ContextOverflow, _USE_COLOR, _color_text,
                         check_clean_cache, check_server, combined_hash,
                         fmt_kb, format_eta_suffix, load_clean_cache,
                         query_llm, run_pipeline, save_result,
                         update_clean_cache)

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))
from validate_html import validate_file, validate_html
from split_entry import split_html, split_txt

ENTRIES_DIR = ROOT / "Entries"
ENTRIES_FR_DIR = ROOT / "Entries_fr"
TXT_FR_DIR = ROOT / "Entries_txt_fr"
ERRATA_FILE = Path("errata.txt")
CLEAN_CACHE = Path("llm_html_clean.txt")
_TMP_DIR = Path("/tmp/llm-html")
RESULTS_FILE = _TMP_DIR / "results.txt"
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


# Sentinel comments marking artificial wrapper boundaries.
_WRAP_HEAD = "<!-- @@CHUNK-WRAPPER-HEAD@@ -->"
_WRAP_TAIL = "<!-- @@CHUNK-WRAPPER-TAIL@@ -->"


def wrap_chunk(html: str) -> tuple[str, str, str]:
    """Balance unmatched <html>/<p> tags so the LLM sees matched pairs.

    Only adds the missing counterpart when one end is present but not
    the other.  Middle chunks (neither tag) are left alone.

    Returns (wrapped_html, prefix_added, suffix_added).
    The prefix/suffix strings are empty if nothing was added.
    """
    s = html.strip()
    low = s.lower()

    has_html_open = s.startswith("<html")
    has_html_close = low.rstrip().endswith("</html>")
    p_imbalance = (low.count("<p>") + low.count("<p ")) - low.count("</p>")

    # Build prefix for missing openers (outermost first)
    prefix = ""
    if has_html_close and not has_html_open:
        prefix += "<html>\n"
    if p_imbalance < 0:  # more </p> than <p>
        prefix += "<p>\n"

    # Build suffix for missing closers (innermost first)
    suffix = ""
    if p_imbalance > 0:  # more <p> than </p>
        suffix += "\n</p>"
    if has_html_open and not has_html_close:
        suffix += "\n</html>"

    if prefix:
        html = prefix + _WRAP_HEAD + "\n" + html
    if suffix:
        html = html + "\n" + _WRAP_TAIL + suffix

    return html, prefix, suffix


def unwrap_chunk(output: str, prefix: str, suffix: str) -> str:
    """Strip the artificial wrapper from LLM output.

    Looks for sentinel comments first; falls back to regex stripping.
    """
    if prefix:
        idx = output.find(_WRAP_HEAD)
        if idx >= 0:
            output = output[idx + len(_WRAP_HEAD):]
            if output.startswith("\n"):
                output = output[1:]
        else:
            # Sentinel dropped — strip each tag we prepended
            for tag in re.findall(r'<[^>]+>', prefix):
                output = re.sub(r'^\s*' + re.escape(tag) + r'\s*',
                                '', output)

    if suffix:
        idx = output.find(_WRAP_TAIL)
        if idx >= 0:
            output = output[:idx].rstrip()
        else:
            # Sentinel dropped — strip each tag we appended
            for tag in reversed(re.findall(r'</[^>]+>', suffix)):
                output = re.sub(r'\s*' + re.escape(tag) + r'\s*$',
                                '', output)

    return output


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
    "Produisez le HTML complet pour ce morceau, y compris les balises "
    "`<html>`, `</html>` etc. telles qu'elles apparaissent dans le HTML "
    "original ci-dessus. Reproduisez exactement la structure fournie.\n"
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

    max_errors = 5
    for i, (output, errors) in enumerate(history, 1):
        shown = errors[:max_errors]
        error_lines = "\n".join(f"- {msg}" for msg in shown)
        if len(errors) > max_errors:
            error_lines += f"\n- ... et {len(errors) - max_errors} autres erreurs"
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

def _write_errata(bdb_id: str, message: str, file_lock: threading.Lock,
                  chunk_idx: int | None = None, total_chunks: int | None = None):
    """Append an errata line to errata.txt.

    When chunk_idx is given, writes 'BDB1234:2/3 html ...' so that
    --skip-errata can operate at chunk level.  Without it, writes
    'BDB1234 html ...' (whole-file errata).
    """
    if chunk_idx is not None and total_chunks is not None:
        tag = f"{bdb_id}:{chunk_idx + 1}/{total_chunks}"
    else:
        tag = bdb_id
    with file_lock:
        with open(ERRATA_FILE, "a") as f:
            f.write(f"{tag} html  {message}\n")


def _assemble_and_validate(bdb_id: str, outputs: list[str | None],
                           orig_parts: list[str], orig_html: str,
                           french_txt: str, is_chunked: bool,
                           failed_chunks: list[tuple[int, str]],
                           errata_chunks: list[tuple[int, str]],
                           file_lock: threading.Lock,
                           max_retries: int = 0,
                           max_attempts: int = 0,
                           ) -> str:
    """Assemble chunks, write to disk, log errata.  Returns final status.

    Shared by both sync (process_entry) and async (_finalize_entry) paths.
    """
    n = len(orig_parts)

    # Log errata for individual chunks
    for idx, reason in errata_chunks:
        _write_errata(bdb_id, f"LLM: {reason}", file_lock,
                      chunk_idx=idx if is_chunked else None,
                      total_chunks=n if is_chunked else None)

    if all(o is None for o in outputs):
        return "FAILED"

    parts = [o if o is not None else orig_parts[i]
             for i, o in enumerate(outputs)]
    assembled = "".join(parts)
    fr_path = ENTRIES_FR_DIR / (bdb_id + ".html")
    fr_path.write_text(assembled, encoding="utf-8")

    # Log failed chunks
    for idx, error_summary in failed_chunks:
        _write_errata(bdb_id,
                      f"failed after retries: {error_summary}",
                      file_lock,
                      chunk_idx=idx if is_chunked else None,
                      total_chunks=n if is_chunked else None)

    if failed_chunks or errata_chunks:
        return "FAILED"

    # Final validation of assembled result (catches cross-chunk issues)
    all_errors = validate_html(orig_html, assembled, french_txt)
    if not all_errors:
        return "CLEAN"

    error_summary = "; ".join(all_errors[:5])
    if len(all_errors) > 5:
        error_summary += f"; ... (+{len(all_errors) - 5} more)"
    _write_errata(bdb_id,
                  f"{len(all_errors)} issues after retries"
                  f"{' (chunked)' if is_chunked else ''}: "
                  f"{error_summary}", file_lock)
    return "FAILED"


def _parse_errata_line(line: str) -> tuple[str, int | None, str]:
    """Parse one errata line.  Returns (bdb_id, chunk_idx_or_None, reason)."""
    if " html " not in line:
        return "", None, ""
    tag = line.split()[0]
    reason_start = line.find(" html  ")
    reason = line[reason_start + 7:].strip() if reason_start >= 0 else ""
    if ":" in tag:
        bdb_part, chunk_spec = tag.split(":", 1)
        try:
            return bdb_part, int(chunk_spec.split("/")[0]) - 1, reason
        except ValueError:
            return tag, None, reason
    return tag, None, reason


def _load_errata_map(errata_path: Path,
                     bdb_filter: str | None = None,
                     ) -> dict[str, dict[int | None, str]]:
    """Load errata file into {bdb_id: {chunk_idx|None: reason}}.

    If bdb_filter is given, only returns entries for that one BDB id.
    """
    result: dict[str, dict[int | None, str]] = {}
    if not errata_path.exists():
        return result
    for line in errata_path.read_text().splitlines():
        bdb_id, chunk_idx, reason = _parse_errata_line(line)
        if not bdb_id:
            continue
        if bdb_filter and bdb_id != bdb_filter:
            continue
        result.setdefault(bdb_id, {})[chunk_idx] = reason
    return result


def _save_entry_result(bdb_id: str, status: str, chash: str,
                       max_attempts: int, orig_path: Path, txt_path: Path,
                       results_path: Path, clean_cache_path: Path,
                       file_lock: threading.Lock):
    """Save result line and update clean cache if CLEAN."""
    filename = bdb_id + ".html"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    result_note = f"attempt {max_attempts}" if max_attempts > 1 else ""
    save_result(results_path, filename, status, timestamp, chash,
                result_note, col_filename=COL_FILENAME,
                col_status=COL_STATUS, lock=file_lock)
    if status == "CLEAN":
        fr_path = ENTRIES_FR_DIR / (bdb_id + ".html")
        update_clean_cache(clean_cache_path, bdb_id,
                           orig_path, txt_path, fr_path, file_lock)


# ---------------------------------------------------------------------------
# Async smart-server pipeline
# ---------------------------------------------------------------------------

@dataclass
class SmartJob:
    """A chunk that failed the dumb server and needs smart-server retry."""
    bdb_id: str
    chunk_idx: int
    total_chunks: int
    orig_html: str
    txt_fr: str
    template: str
    is_chunked: bool
    prev_output: str | None
    prev_errors: list[str]
    prev_history: list[tuple[str, list[str]]]
    prev_errata: str | None
    entry_state: "EntryState"


@dataclass
class EntryState:
    """Tracks the assembly state of one entry across main + smart threads."""
    bdb_id: str
    orig_path: Path
    txt_path: Path
    orig_html: str
    french_txt: str
    orig_parts: list[str]
    txt_parts: list[str]
    is_chunked: bool
    outputs: list[str | None]
    pending_smart: int = 0
    main_loop_done: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)
    line_number: int = 0
    total_entries: int = 0
    chash: str = ""
    done_event: threading.Event = field(default_factory=threading.Event)
    final_status: str | None = None
    total_prompt_kb: float = 0.0
    max_attempts: int = 0
    failed_chunks: list = field(default_factory=list)
    errata_chunks: list = field(default_factory=list)
    t0: float = 0.0


def _finalize_entry(state: EntryState, file_lock: threading.Lock,
                    results_path: Path, clean_cache_path: Path):
    """Assemble all chunks, validate, write, save result.

    Called when the last pending smart chunk resolves. May be called from
    the smart thread or (for non-deferred entries) from the main thread.
    """
    state.final_status = _assemble_and_validate(
        state.bdb_id, state.outputs, state.orig_parts,
        state.orig_html, state.french_txt, state.is_chunked,
        state.failed_chunks, state.errata_chunks, file_lock)

    _save_entry_result(state.bdb_id, state.final_status, state.chash,
                       state.max_attempts, state.orig_path, state.txt_path,
                       results_path, clean_cache_path, file_lock)

    state.done_event.set()


def _smart_worker(q: "queue.Queue[SmartJob | None]",
                  smart_server: str, smart_retries: int,
                  max_retries: int, debug: bool,
                  file_lock: threading.Lock,
                  print_lock: threading.Lock,
                  results_path: Path,
                  clean_cache_path: Path,
                  elapsed_times: list,
                  completed_counter: list,
                  shutdown_event: threading.Event,
                  smart_semaphore: threading.Semaphore,
                  current_line_bdb: list | None = None):
    """Background thread consuming SmartJob items from the queue."""
    while True:
        job = q.get()
        if job is None:  # poison pill
            q.task_done()
            break
        if shutdown_event.is_set():
            q.task_done()
            smart_semaphore.release()
            continue

        smart_note = (_errata_note_text(job.prev_errata, is_smart=True)
                      if job.prev_errata and not job.prev_errors else None)

        state = job.entry_state

        def _async_on_attempt(n, smart=False, errata=False):
            if errata or n == 1:
                return
            retry_n = n - max_retries
            if retry_n <= 1:
                return  # silent on first smart attempt
            label = f" try {retry_n}"
            if _USE_COLOR:
                s = f" \033[1;33m{label.lstrip()}\033[0m"
            else:
                s = label
            with print_lock:
                sys.stdout.write(s)
                sys.stdout.flush()

        html, kb, attempts, errors, errata, _ = _try_server(
            job.bdb_id, job.chunk_idx, job.total_chunks,
            job.orig_html, job.txt_fr,
            job.prev_output, job.prev_errors,
            job.prev_history, job.template,
            smart_server, smart_retries, job.is_chunked,
            debug=debug, errata_note=smart_note,
            attempt_offset=max_retries, debug_prefix="smart",
            on_attempt=_async_on_attempt)

        with state.lock:
            state.outputs[job.chunk_idx] = html
            state.total_prompt_kb += kb
            state.max_attempts = max(state.max_attempts, attempts)

            if errata:
                state.errata_chunks.append((job.chunk_idx, errata))
            elif errors:
                state.failed_chunks.append(
                    (job.chunk_idx, "; ".join(errors[:5])))

            state.pending_smart -= 1
            all_resolved = (state.pending_smart == 0
                            and state.main_loop_done)

        if not all_resolved:
            n_done = sum(1 for o in state.outputs if o is not None)
            n_total = len(state.outputs)
            if errors:
                verdict = _color_text("✗", "FAILED")
            elif errata:
                verdict = _color_text("⚠", "ERRATA")
            else:
                verdict = _color_text("✓", "CLEAN")
            same = (current_line_bdb and current_line_bdb[0] == state.bdb_id)
            parts = []
            if not same:
                parts.append(f"← {state.bdb_id}")
            if n_total > 1:
                parts.append(f"{n_done}/{n_total}")
            prefix = " ".join(parts) if parts else "←"
            if _USE_COLOR:
                s = f" \033[1;33m{prefix}\033[0m {verdict}"
            else:
                s = f" {prefix} {verdict}"
            with print_lock:
                sys.stdout.write(s)
                sys.stdout.flush()

        if all_resolved:
            _finalize_entry(state, file_lock, results_path,
                            clean_cache_path)
            elapsed = time.monotonic() - state.t0
            status = state.final_status
            with print_lock:
                completed_counter[0] += 1
                elapsed_times.append(elapsed)
                items_left = state.total_entries - completed_counter[0]
                suffix = format_eta_suffix(
                    status, elapsed, elapsed_times, items_left)
                same = (current_line_bdb
                        and current_line_bdb[0] == state.bdb_id)
                arrow = "←" if same else f"← {state.bdb_id}"
                if _USE_COLOR:
                    arrow = f"\033[1;33m{arrow}\033[0m"
                print(f"  {arrow}{suffix}")

        q.task_done()
        smart_semaphore.release()


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

def _prepare_chunk(orig_html: str, is_chunked: bool):
    """Wrap chunk HTML for LLM processing. Returns (wrapped, prefix, suffix)."""
    if is_chunked:
        return wrap_chunk(orig_html)
    return orig_html, "", ""


def _try_server(bdb_id: str, idx: int, n: int,
                orig_html: str, txt_fr: str,
                prev_output: str | None, prev_errors: list[str],
                prev_history: list[tuple[str, list[str]]] | None,
                template: str, server_url: str, max_retries: int,
                is_chunked: bool,
                on_attempt=None, on_chunk=None,
                debug: bool = False,
                errata_note: str | None = None,
                attempt_offset: int = 0,
                debug_prefix: str = "try",
                return_history: bool = False,
                return_reasoning: bool = False,
                ) -> tuple[str | None, float, int, list[str], str | None,
                           list[tuple[str, list[str]]]]:
    """Try a server up to max_retries times.

    Unified core for both dumb and smart server attempts.  The caller
    controls labelling (attempt_offset, debug_prefix) and whether history
    is returned.

    errata_note: if set, appended on the first attempt when there's no
    prior output/errors (e.g. a note from a previous model).

    attempt_offset: added to the attempt number for display and return
    value (smart server uses max_dumb_retries as offset).

    Returns (html, prompt_kb, attempt_number, remaining_errors, errata, history).
    """
    output = prev_output
    errors = prev_errors
    prompt_kb_total = 0.0
    history: list[tuple[str, list[str]]] = list(prev_history or [])
    errata_reason = None

    wrapped_html, _wrap_prefix, _wrap_suffix = _prepare_chunk(orig_html, is_chunked)

    for attempt in range(1, max_retries + 1):
        if output is not None and not errors:
            return output, prompt_kb_total, 0, [], None, history

        if is_chunked:
            base = build_chunk_prompt(template, wrapped_html, txt_fr, idx, n)
        else:
            base = build_prompt(template, orig_html, txt_fr)

        if errors and output is not None:
            prev_len = len(output)
            skip_prev = (prev_len > 1.2 * len(orig_html)
                         or (attempt == 1 and prev_len > 5120))
            if skip_prev:
                output = None
                errors = []
                history.clear()
                prompt = base
            else:
                history.append((output, errors))
                prompt = base + _build_retry_suffix(history,
                                                    is_chunk=is_chunked)
        else:
            prompt = base
            if errata_note and attempt == 1:
                prompt += errata_note
                errata_note = None  # only on first attempt

        prompt_kb = len(prompt.encode("utf-8")) / 1024
        prompt_kb_total += prompt_kb

        if on_chunk and attempt == 1:
            on_chunk(idx, n, prompt_kb, is_chunked)

        attempt_num = attempt + attempt_offset
        is_smart = attempt_offset > 0
        if on_attempt:
            on_attempt(attempt_num, smart=is_smart)

        if debug:
            dbg = f"/tmp/llm-html/debug-{bdb_id}-{debug_prefix}{attempt}"
            if is_chunked:
                dbg += f"-chunk{idx}"
            Path(f"{dbg}-prompt.txt").write_text(prompt, encoding="utf-8")

        try:
            if return_reasoning and debug and not is_chunked:
                raw, thinking = query_llm(prompt, server_url,
                                          max_tokens=131072,
                                          return_reasoning=True)
            else:
                raw = query_llm(prompt, server_url, max_tokens=131072)
                thinking = None
        except ContextOverflow:
            return (output, prompt_kb_total, attempt_num, errors,
                    "CONTEXT_OVERFLOW", history)

        if debug:
            Path(f"{dbg}-out.txt").write_text(raw, encoding="utf-8")
            if thinking:
                Path(f"{dbg}-think.txt").write_text(
                    thinking, encoding="utf-8")

        errata_reason = check_llm_errata(raw)
        if errata_reason:
            if on_attempt and not is_smart:
                on_attempt(attempt_num, errata=True)
            return (None, prompt_kb_total, attempt_num, [],
                    errata_reason, history)

        output = extract_html(raw)
        if is_chunked:
            output = unwrap_chunk(output, _wrap_prefix, _wrap_suffix)

        errors = validate_html(orig_html, output, txt_fr)
        if not errors:
            return output, prompt_kb_total, attempt_num, [], None, history

    # Exhausted retries
    return (output, prompt_kb_total, max_retries + attempt_offset,
            errors or [], None, history)


def _errata_note_text(reason: str, is_smart: bool = False) -> str:
    """Build the errata note suffix for a prompt."""
    source = ("Un modèle moins capable" if is_smart
              else "Un modèle précédent")
    return (
        f"\n\n## ⚠️ Note du modèle précédent\n\n"
        f"{source} a signalé cette entrée comme"
        f" ERRATA : « {reason} ».\n"
        f"Examinez l'entrée et produisez le HTML si possible."
        f" Si le problème est réel et incontournable,"
        f" vous pouvez aussi signaler ERRATA.")


def _generate_chunk(bdb_id: str, idx: int, n: int,
                    orig_html: str, txt_fr: str, prev_output: str | None,
                    prev_errors: list[str], template: str,
                    server_url: str, max_retries: int,
                    is_chunked: bool,
                    on_attempt=None, on_chunk=None,
                    debug: bool = False,
                    smart_server: str | None = None,
                    smart_retries: int = 1,
                    prior_errata_reason: str | None = None,
                    ) -> tuple[str | None, float, int, list[str], str | None]:
    """Generate (and retry) one chunk. Delegates to dumb then smart server.

    Returns (html, prompt_kb, attempts, remaining_errors, errata).
    """
    errata_note = (_errata_note_text(prior_errata_reason)
                   if prior_errata_reason else None)
    html, kb, attempts, errors, errata, history = _try_server(
        bdb_id, idx, n, orig_html, txt_fr, prev_output, prev_errors,
        None, template, server_url, max_retries, is_chunked,
        on_attempt=on_attempt, on_chunk=on_chunk, debug=debug,
        errata_note=errata_note, return_reasoning=True)

    # Success or no smart server — return as-is
    if not errors and not errata:
        return html, kb, attempts, errors, errata
    if errata == "CONTEXT_OVERFLOW":
        if not smart_server:
            if is_chunked:
                return html, kb, attempts, errors, None
            return None, kb, attempts, errors, "SKIPPED"
        errata = None  # fall through to smart
    elif not smart_server or not smart_retries:
        return html, kb, attempts, errors, errata

    # Smart server fallback
    smart_note = (_errata_note_text(errata, is_smart=True)
                  if errata and not errors else None)
    s_html, s_kb, s_attempts, s_errors, s_errata, _ = _try_server(
        bdb_id, idx, n, orig_html, txt_fr, html, errors,
        history, template, smart_server, smart_retries, is_chunked,
        on_attempt=on_attempt, debug=debug,
        errata_note=smart_note,
        attempt_offset=max_retries, debug_prefix="smart")

    return s_html, kb + s_kb, s_attempts, s_errors, s_errata


def process_entry(bdb_id: str, orig_path: Path, txt_path: Path,
                  template: str, server_url: str, max_retries: int,
                  results_path: Path, file_lock: threading.Lock,
                  on_attempt=None, on_chunk=None,
                  on_chunk_done=None,
                  debug: bool = False,
                  smart_server: str | None = None,
                  smart_retries: int = 1,
                  skip_failed: bool = False,
                  skip_incomplete: bool = False,
                  skip_errata_chunks: set[int] | None = None,
                  errata_reasons: dict[int, str] | None = None,
                  smart_queue: "queue.Queue[SmartJob | None] | None" = None,
                  smart_semaphore: threading.Semaphore | None = None,
                  entry_state_out: list | None = None,
                  ) -> tuple[str, float, int]:
    """Process one entry. Returns (status, prompt_kb, attempts_used).

    Status is one of: CLEAN, FAILED, ERRATA, SKIPPED, PENDING.
    PENDING means chunks were enqueued to the smart server background thread.

    When smart_queue is provided and a chunk fails the dumb server, it is
    enqueued for async smart-server processing instead of blocking.

    entry_state_out: if provided, the EntryState is appended so the caller
    can wait on its done_event.

    When skip_failed is True, errored chunks keep their previous output and
    only truly missing chunks are regenerated.

    When skip_incomplete is True, entries with missing chunks (fewer fr chunks
    than orig) are skipped entirely.

    on_chunk_done(verdict): called after each chunk with "✓", "✗", or "⚠".
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

    # Warm start: re-read fr_path just-in-time (another worker may have
    # updated it since the upfront scan that queued this entry).
    fr_path = ENTRIES_FR_DIR / (bdb_id + ".html")
    prev_output = None
    prev_errors: list[str] = []
    chunk_prev_outputs: list[str | None] = [None] * n
    chunk_prev_errors: list[list[str]] = [[] for _ in range(n)]

    if fr_path.exists():
        prev_fr_html = fr_path.read_text()
        if is_chunked:
            fr_chunks = split_html(prev_fr_html)
            n_fr = len(fr_chunks)
            if n_fr != n:
                # Chunk count mismatch — existing file is misaligned,
                # discard it and regenerate from scratch.
                pass
            else:
                fr_parts = [c["html"] for c in fr_chunks]
                # Validate chunks that exist in both orig and fr
                all_clean = True
                for idx in range(n):
                    errs = validate_html(
                        orig_parts[idx], fr_parts[idx], txt_parts[idx])
                    if errs:
                        all_clean = False
                        chunk_prev_outputs[idx] = fr_parts[idx]
                        chunk_prev_errors[idx] = errs
                        if skip_failed:
                            # Keep errored chunk as-is, don't regenerate
                            outputs[idx] = fr_parts[idx]
                    else:
                        outputs[idx] = fr_parts[idx]  # reuse clean chunk
                if skip_incomplete and not all_clean:
                    return "SKIPPED", 0.0, 0
                if all_clean:
                    return "CLEAN", 0.0, 0
        else:
            prev_output = prev_fr_html
            prev_errors = validate_html(orig_html, prev_output, french_txt)
            if not prev_errors:
                return "CLEAN", 0.0, 0
            if skip_failed:
                # Non-chunked entry with errors: keep as-is
                return "SKIPPED", 0.0, 0

    # Async mode: build an EntryState for deferred smart processing
    async_smart = (smart_queue is not None and smart_server
                   and smart_retries > 0)
    state = None
    if async_smart:
        state = EntryState(
            bdb_id=bdb_id, orig_path=orig_path, txt_path=txt_path,
            orig_html=orig_html, french_txt=french_txt,
            orig_parts=orig_parts, txt_parts=txt_parts,
            is_chunked=is_chunked, outputs=outputs,
            t0=time.monotonic())

    # Process each chunk with its own retry loop.
    # Errata/failure on one chunk does NOT stop processing — we continue so
    # that a later retry (possibly with a smarter model) only has to redo the
    # broken chunks.
    failed_chunks = []       # [(idx, error_summary)]
    errata_chunks = []       # [(idx, reason)]
    deferred_count = 0
    _skip_errata = skip_errata_chunks or set()
    for idx in range(n):
        # Skip chunks already clean from a prior run
        if outputs[idx] is not None:
            if on_chunk:
                on_chunk(idx, n, 0, is_chunked)
            if on_chunk_done and is_chunked:
                on_chunk_done("✓")
            continue

        # Skip errata chunks — keep previous output if available
        if idx in _skip_errata:
            if chunk_prev_outputs[idx] is not None:
                outputs[idx] = chunk_prev_outputs[idx]
            if on_chunk:
                on_chunk(idx, n, 0, is_chunked)
            if on_chunk_done and is_chunked:
                on_chunk_done("⚠")
            continue

        chunk_prev = (chunk_prev_outputs[idx] if is_chunked
                      else (prev_output if idx == 0 else None))
        chunk_errs = (chunk_prev_errors[idx] if is_chunked
                      else (prev_errors if idx == 0 else []))

        _errata_reasons = errata_reasons or {}
        chunk_errata = _errata_reasons.get(idx) or _errata_reasons.get(None)

        if async_smart:
            # Dumb server only — enqueue failures to smart queue
            errata_note = (_errata_note_text(chunk_errata)
                           if chunk_errata else None)
            html, kb, attempts, remaining, errata, history = _try_server(
                bdb_id, idx, n, orig_parts[idx], txt_parts[idx],
                chunk_prev, chunk_errs, None, template, server_url,
                max_retries, is_chunked,
                on_attempt=on_attempt, on_chunk=on_chunk, debug=debug,
                errata_note=errata_note, return_reasoning=True)

            total_prompt_kb += kb
            max_attempts = max(max_attempts, attempts)

            if errata == "CONTEXT_OVERFLOW":
                errata = None  # will enqueue to smart
                remaining = remaining or []

            # Dumb succeeded
            if not remaining and not errata:
                outputs[idx] = html
                if on_chunk_done and is_chunked:
                    on_chunk_done("✓")
                continue

            # Dumb failed — enqueue to smart server
            if on_chunk_done and is_chunked:
                on_chunk_done("→S")

            smart_semaphore.acquire()  # back-pressure
            job = SmartJob(
                bdb_id=bdb_id, chunk_idx=idx, total_chunks=n,
                orig_html=orig_parts[idx], txt_fr=txt_parts[idx],
                template=template, is_chunked=is_chunked,
                prev_output=html, prev_errors=remaining or [],
                prev_history=history, prev_errata=errata,
                entry_state=state)
            with state.lock:
                state.pending_smart += 1
            smart_queue.put(job)
            deferred_count += 1
        else:
            # Synchronous mode — use _generate_chunk (dumb + smart inline)
            html, kb, attempts, remaining, errata = _generate_chunk(
                bdb_id, idx, n, orig_parts[idx], txt_parts[idx],
                chunk_prev, chunk_errs, template, server_url, max_retries,
                is_chunked,
                on_attempt=on_attempt, on_chunk=on_chunk, debug=debug,
                smart_server=smart_server, smart_retries=smart_retries,
                prior_errata_reason=chunk_errata)

            total_prompt_kb += kb
            max_attempts = max(max_attempts, attempts)

            if errata == "SKIPPED":
                return "SKIPPED", total_prompt_kb, attempts
            if errata:
                errata_chunks.append((idx, errata))
                if chunk_prev:
                    outputs[idx] = chunk_prev
                if on_chunk_done and is_chunked:
                    on_chunk_done("⚠")
                continue

            outputs[idx] = html

            if remaining:
                failed_chunks.append((idx, "; ".join(remaining[:5])))
                if on_chunk_done and is_chunked:
                    on_chunk_done("✗")
            elif on_chunk_done and is_chunked:
                on_chunk_done("✓")

    # If chunks were deferred to smart, store state and return PENDING
    if deferred_count > 0:
        with state.lock:
            state.total_prompt_kb += total_prompt_kb
            state.max_attempts = max(state.max_attempts, max_attempts)
            state.failed_chunks.extend(failed_chunks)
            state.errata_chunks.extend(errata_chunks)
            state.main_loop_done = True
            # Smart may have already resolved all chunks before we got here
            if state.pending_smart == 0:
                # All smart chunks resolved while main loop was still running.
                # Assemble synchronously — smart thread won't finalize.
                status = _assemble_and_validate(
                    bdb_id, state.outputs, orig_parts, orig_html, french_txt,
                    is_chunked, state.failed_chunks, state.errata_chunks,
                    file_lock)
                return status, total_prompt_kb, max_attempts
        if entry_state_out is not None:
            entry_state_out.append(state)
        return "PENDING", total_prompt_kb, max_attempts

    # Synchronous completion (no smart queue or all chunks succeeded on dumb)
    status = _assemble_and_validate(
        bdb_id, outputs, orig_parts, orig_html, french_txt,
        is_chunked, failed_chunks, errata_chunks, file_lock)
    return status, total_prompt_kb, max_attempts


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
        "--errata-file", help="Override errata file path (default: errata.txt).",
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
        help="Keep errored chunks as-is and only regenerate missing chunks. "
             "Non-chunked entries with errors are skipped entirely.",
    )
    parser.add_argument(
        "--skip-errata", action="store_true", default=False,
        help="Skip entries that LLM flagged as ERRATA (default: retry).",
    )
    parser.add_argument(
        "--skip-incomplete", action="store_true", default=False,
        help="Skip entries with missing chunks (fewer fr chunks than orig). "
             "Without this flag, missing chunks are always generated.",
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
        help="Write prompt/response to /tmp/llm-html/debug-BDBnnn-tryN-{prompt,out}.txt.",
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
    global ENTRIES_DIR, ENTRIES_FR_DIR, TXT_FR_DIR, ERRATA_FILE, RESULTS_FILE
    if args.entries_dir:
        ENTRIES_DIR = Path(args.entries_dir)
    if args.txt_fr_dir:
        TXT_FR_DIR = Path(args.txt_fr_dir)
    if args.output_dir:
        ENTRIES_FR_DIR = Path(args.output_dir)
    if args.errata_file:
        ERRATA_FILE = Path(args.errata_file)
    if args.results:
        RESULTS_FILE = Path(args.results)

    # Ensure tmp directory and files are group-writable
    os.umask(0o002)
    _TMP_DIR.mkdir(mode=0o775, exist_ok=True)

    prompt_path = Path(args.prompt) if args.prompt else PROMPT_FILE
    if not prompt_path.exists():
        print(f"error: prompt template not found: {prompt_path}",
              file=sys.stderr)
        sys.exit(1)
    template = prompt_path.read_text()

    digits = args.digits if args.digits else None
    only = [e.removesuffix(".html") for e in args.entries] if args.entries else None
    entries = get_entries(digits, only=only)

    errata_map = _load_errata_map(ERRATA_FILE)

    # Split entries into existing (need validation) and new (no Entries_fr yet)
    existing = []
    new_entries = []
    for bdb_id, orig_path, txt_path in entries:
        fr_path = ENTRIES_FR_DIR / (bdb_id + ".html")
        if not args.force and fr_path.exists():
            existing.append((bdb_id, orig_path, txt_path))
        else:
            new_entries.append((bdb_id, orig_path, txt_path))

    # Validate existing Entries_fr/ files (using clean cache to skip)
    clean_cache = load_clean_cache(CLEAN_CACHE)
    counts = {"clean": 0, "cached": 0, "invalid": 0, "errata": 0,
              "new": len(new_entries)}
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

            errata_info = errata_map.get(bdb_id, {})
            if None in errata_info and args.skip_errata:
                # Whole-file errata — skip entirely
                counts["errata"] += 1
                skipped_errata.append(bdb_id)
                continue
            if errata_info:
                counts["errata"] += 1
            fr_path = ENTRIES_FR_DIR / (bdb_id + ".html")
            if check_clean_cache(clean_cache, bdb_id,
                                 orig_path, txt_path, fr_path):
                counts["cached"] += 1
                continue
            errors = validate_file(bdb_id, entries_dir=str(ENTRIES_DIR),
                                   entries_fr_dir=str(ENTRIES_FR_DIR),
                                   txt_fr_dir=str(TXT_FR_DIR))
            if not errors:
                counts["clean"] += 1
                update_clean_cache(CLEAN_CACHE, bdb_id,
                                   orig_path, txt_path, fr_path)
                continue
            counts["invalid"] += 1
            # Check chunk-level status to decide if we can skip
            orig_html = orig_path.read_text()
            fr_html = fr_path.read_text()
            n_orig = len(split_html(orig_html))
            n_fr = len(split_html(fr_html))
            has_missing = n_orig > 1 and n_fr < n_orig
            if args.skip_failed and not has_missing:
                continue  # all chunks present, errors skipped
            if args.skip_errata and not has_missing and errata_info:
                # All chunks present — skip if every invalid chunk
                # is covered by an errata entry
                errata_idxs = {k for k in errata_info if k is not None}
                if errata_idxs:
                    # Validate per-chunk to find which are invalid
                    orig_chunks = split_html(orig_html)
                    fr_chunks = split_html(fr_html)
                    txt_chunks = split_txt(txt_path.read_text())
                    invalid_idxs = set()
                    for ci in range(min(n_orig, n_fr)):
                        txt_c = (txt_chunks[ci]["txt"]
                                 if txt_chunks and ci < len(txt_chunks) else None)
                        if validate_html(orig_chunks[ci]["html"],
                                         fr_chunks[ci]["html"], txt_c):
                            invalid_idxs.add(ci)
                    if invalid_idxs and invalid_idxs <= errata_idxs:
                        continue  # all invalid chunks are errata — skip
            to_process.append((bdb_id, orig_path, txt_path, chash))
        print(" done")
    else:
        print("No existing Entries_fr to validate.")

    # Add new entries to processing list
    for bdb_id, orig_path, txt_path in new_entries:
        if args.skip_errata:
            errata_info = errata_map.get(bdb_id, {})
            if None in errata_info:
                counts["errata"] += 1
                skipped_errata.append(bdb_id)
                continue
        chash = combined_hash(orig_path, txt_path)
        to_process.append((bdb_id, orig_path, txt_path, chash))

    # Build summary with * marking skipped categories
    total_clean = counts["clean"] + counts["cached"]
    clean_s = f"{total_clean} clean*"
    if counts["cached"]:
        clean_s += f" ({counts['cached']} cached)"
    invalid_s = f"{counts['invalid']} invalid"
    errata_s = f"{counts['errata']} errata"
    if args.skip_errata:
        errata_s += "*"
    print(f"Entries_fr: {n_exist}/{len(entries)} exist: "
          f"{clean_s}, {invalid_s}, {errata_s}")
    if args.skip_failed:
        print(f"  --skip-failed: errored chunks kept, only missing regenerated")
    if args.skip_incomplete:
        print(f"  --skip-incomplete: entries with missing chunks skipped")
    n_skipped = total_clean
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
    print_lock = threading.Lock()
    current_line_bdb = [""]  # bdb_id currently being printed on the main line

    sequential = args.parallel <= 1
    smart_n = args.smart_retries if args.smart_server else 0
    max_try_str = (" try " + " ".join(
        str(n) for n in range(1, args.max_retries + 1))
        + "".join(f" S{n}" for n in range(1, smart_n + 1)))
    max_try_width = len(max_try_str)

    # --- Async smart-server pipeline setup ---
    MAX_SMART_INFLIGHT = 3
    use_async_smart = bool(args.smart_server and sequential)
    smart_q: queue.Queue[SmartJob | None] | None = None
    smart_sem: threading.Semaphore | None = None
    smart_thread: threading.Thread | None = None
    shutdown_event = threading.Event()
    # Shared mutable counters for the smart thread's display/ETA.
    # Using lists so the smart thread can mutate them under print_lock.
    smart_elapsed_times: list[float] = []
    smart_completed: list[int] = [0]  # [count]
    pending_states: list[EntryState] = []  # entries awaiting smart resolution

    if use_async_smart:
        smart_q = queue.Queue()
        smart_sem = threading.Semaphore(MAX_SMART_INFLIGHT)
        smart_thread = threading.Thread(
            target=_smart_worker,
            args=(smart_q, args.smart_server, args.smart_retries,
                  args.max_retries, args.debug, file_lock, print_lock,
                  RESULTS_FILE, CLEAN_CACHE,
                  smart_elapsed_times, smart_completed,
                  shutdown_event, smart_sem, current_line_bdb),
            daemon=True)
        smart_thread.start()
        print(f"  Async smart: enabled (max {MAX_SMART_INFLIGHT} in-flight)")

    def _errata_now(bdb_id) -> dict[int | None, str]:
        """Re-check errata file for one entry (another process may have
        added entries)."""
        m = _load_errata_map(ERRATA_FILE, bdb_filter=bdb_id)
        return m.get(bdb_id, {})

    def process_one(i, total, item):
        bdb_id, orig_path, txt_path, chash = item
        filename = bdb_id
        current_line_bdb[0] = bdb_id

        # Just-in-time guard: another process may have finished this entry
        fr_path = ENTRIES_FR_DIR / (bdb_id + ".html")
        if not args.force and fr_path.exists():
            orig_html = orig_path.read_text()
            fr_html = fr_path.read_text()
            french_txt = txt_path.read_text()
            errs = validate_html(orig_html, fr_html, french_txt)
            if not errs:
                return filename, "SKIP", 0.0, "(already clean)"
            if args.skip_failed:
                n_orig = len(split_html(orig_html))
                n_fr = len(split_html(fr_html))
                if not (n_orig > 1 and n_fr < n_orig):
                    return filename, "SKIP", 0.0, "(skip-failed)"
        jit_errata = _errata_now(bdb_id) if args.skip_errata else errata_map.get(bdb_id, {})
        errata_skip: set[int] = set()
        errata_reasons: dict[int, str] = {}
        skip_errata_chunks = args.skip_errata
        if jit_errata:
            if None in jit_errata and args.skip_errata:
                return filename, "SKIP", 0.0, "(errata)"
            for k, reason in jit_errata.items():
                if k is None:
                    continue
                if skip_errata_chunks:
                    errata_skip.add(k)
                errata_reasons[k] = reason

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

        _VERDICT_COLORS = {"✓": "\033[32m", "✗": "\033[31m",
                           "⚠": "\033[33m", "→S": "\033[1;33m"}

        def on_chunk_done(verdict):
            nonlocal try_chars
            if not sequential:
                return
            if _USE_COLOR and verdict in _VERDICT_COLORS:
                s_display = f" {_VERDICT_COLORS[verdict]}{verdict}\033[0m"
            else:
                s_display = f" {verdict}"
            try_chars += len(f" {verdict}")
            sys.stdout.write(s_display)
            sys.stdout.flush()

        smart_retries = args.smart_retries if args.smart_server else 0
        entry_state_out: list[EntryState] = []
        status, prompt_kb, attempts = process_entry(
            bdb_id, orig_path, txt_path, template,
            args.server, args.max_retries, RESULTS_FILE, file_lock,
            on_attempt=on_attempt, on_chunk=on_chunk,
            on_chunk_done=on_chunk_done, debug=args.debug,
            smart_server=args.smart_server, smart_retries=smart_retries,
            skip_failed=args.skip_failed,
            skip_incomplete=args.skip_incomplete,
            skip_errata_chunks=errata_skip or None,
            errata_reasons=errata_reasons or None,
            smart_queue=smart_q if use_async_smart else None,
            smart_semaphore=smart_sem,
            entry_state_out=entry_state_out)

        if status == "PENDING" and entry_state_out:
            # Store state for post-pipeline join; set metadata for display
            state = entry_state_out[0]
            state.chash = chash
            state.line_number = i
            state.total_entries = total
            pending_states.append(state)

        # Pad try column to fixed width so status aligns
        if sequential and try_chars < max_try_width:
            sys.stdout.write(" " * (max_try_width - try_chars))
            sys.stdout.flush()

        if status == "PENDING":
            # Don't save result yet — smart thread will handle it
            return filename, status, prompt_kb, ""

        _save_entry_result(bdb_id, status, chash, attempts,
                           orig_path, txt_path, RESULTS_FILE,
                           CLEAN_CACHE, file_lock)
        return filename, status, prompt_kb, ""

    def file_size_kb(item):
        _, orig_path, _, _ = item
        return orig_path.stat().st_size / 1024

    counts = run_pipeline(to_process, process_one,
                          name_fn=lambda item: item[0],
                          size_fn=file_size_kb,
                          parallel=args.parallel,
                          shuffle=args.shuffle, limit=args.max,
                          label="entries",
                          print_lock=print_lock)

    # --- Wait for async smart server to finish ---
    if smart_thread is not None:
        n_pending = counts.get("PENDING", 0)
        if n_pending:
            print(f"\nWaiting for {n_pending} entries on smart server...")
        smart_q.put(None)  # poison pill — worker drains queue then exits
        smart_thread.join()

        # Reconcile PENDING into final statuses
        pending_count = counts.pop("PENDING", 0)
        for state in pending_states:
            st = state.final_status or "FAILED"
            counts[st] = counts.get(st, 0) + 1

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
