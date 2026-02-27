#!/usr/bin/env python3
"""Convert llm_verify results .txt to a colored HTML report.

Groups chunks into a single row per entry. Click a chunk badge to
expand/collapse its explanation. Hover for analysis preview tooltip.
Dropdown shows chunk content from txt/txt_fr as a title, then the analysis.
Deduplicates: last occurrence of each chunk key wins.
"""

import html
import re
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from split_entry import split_txt

STATUS_COLORS = {
    "CORRECT": "#1a7d1a",
    "ERROR":   "#b91c1c",
    "WARN":    "#a16207",
    "SKIPPED": "#4a8a8a",
}
STATUS_BG = {
    "CORRECT": "#dcfce7",
    "ERROR":   "#fee2e2",
    "WARN":    "#fef9c3",
    "SKIPPED": "#e0f2fe",
}
STATUS_RANK = {"ERROR": 0, "WARN": 1, "SKIPPED": 2, "CORRECT": 3}


def parse_key(filename):
    """Split 'BDB1234.txt:2/5' into ('BDB1234.txt', 2, 5).
    For non-chunked 'BDB1234.txt' returns ('BDB1234.txt', 0, 0)."""
    m = re.match(r'^(.+\.txt):(\d+)/(\d+)$', filename)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))
    return filename, 0, 0


def clean_explanation(explanation):
    """Strip leading quote and section prefix from explanation."""
    text = explanation.strip().strip('"')
    m = re.match(r'^(header|sense|stem|footer):\s*', text, re.IGNORECASE)
    if m:
        text = text[m.end():]
    return text


def analysis_preview(explanation):
    """Short preview of the analysis for tooltip."""
    text = clean_explanation(explanation)
    m = re.match(r'Analyse\s*:\s*', text)
    if m:
        text = text[m.end():]
    if len(text) > 120:
        text = text[:117] + "..."
    return text


def _chunk_preview(chunk_dict, max_chars=120):
    """Extract a meaningful preview from a chunk's text.

    Joins the first few non-empty, non-marker lines up to max_chars.
    """
    txt = chunk_dict.get("txt", "")
    parts = []
    total = 0
    for line in txt.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("@@SPLIT:"):
            continue
        if total > 0:
            parts.append(" ")
            total += 1
        parts.append(stripped)
        total += len(stripped)
        if total >= max_chars:
            break
    result = "".join(parts)
    if len(result) > max_chars:
        result = result[:max_chars - 3] + "..."
    return result


def load_chunk_info(txt_dir, stem, max_chars=120):
    """Split a txt file into chunks and return {1-based index: preview}."""
    path = txt_dir / f"{stem}.txt"
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    chunks = split_txt(text)
    return {i + 1: _chunk_preview(c, max_chars) for i, c in enumerate(chunks)}


def load_head_word(json_dir, stem):
    """Read head_word from json_output/<stem>.json."""
    path = json_dir / f"{stem}.json"
    if not path.exists():
        return ""
    try:
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("head_word", "") or ""
    except Exception:
        return ""


def bdb_stem(base):
    """Extract 'BDB1234' from 'BDB1234.txt'."""
    return base.rsplit(".", 1)[0]


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <results.txt> [output.html]")
        sys.exit(1)

    results_path = Path(sys.argv[1])
    if len(sys.argv) >= 3:
        out_path = Path(sys.argv[2])
    else:
        out_path = results_path.parent / results_path.name.replace(".txt", ".html")

    txt_fr_dir = results_path.parent / "Entries_txt_fr"
    txt_en_dir = results_path.parent / "Entries_txt"
    json_dir = results_path.parent / "json_output"
    lines = results_path.read_text(encoding="utf-8").splitlines()

    # Deduplicate: last occurrence per key wins.
    deduped = OrderedDict()
    for line in lines:
        if not line.strip():
            continue
        parts = line.split(",", 5)
        if len(parts) < 6:
            continue
        key = parts[0].strip()
        status = parts[1].strip()
        severity = parts[2].strip()
        explanation = parts[5].strip().strip('"')
        deduped[key] = (status, severity, explanation)

    # Group by base filename
    entries = OrderedDict()
    for key, (status, severity, explanation) in deduped.items():
        base, chunk_idx, chunk_total = parse_key(key)
        if base not in entries:
            entries[base] = []
        entries[base].append((chunk_idx, chunk_total, status, severity, explanation))

    def worst_status(chunks):
        worst = "CORRECT"
        worst_sev = -1
        for _, _, status, severity, _ in chunks:
            if STATUS_RANK.get(status, 9) < STATUS_RANK.get(worst, 9):
                worst = status
            sev_int = int(severity) if severity.lstrip("-").isdigit() else -1
            if sev_int > worst_sev:
                worst_sev = sev_int
        return worst, worst_sev

    sorted_entries = sorted(entries.items(),
        key=lambda kv: (STATUS_RANK.get(worst_status(kv[1])[0], 9),
                        -worst_status(kv[1])[1], kv[0]))

    entry_counts = {}
    for base, chunks in sorted_entries:
        w, _ = worst_status(chunks)
        entry_counts[w] = entry_counts.get(w, 0) + 1

    summary_parts = []
    for s in ("ERROR", "WARN", "CORRECT", "SKIPPED"):
        if s in entry_counts:
            c = STATUS_COLORS.get(s, "#333")
            summary_parts.append(
                f'<span style="color:{c};font-weight:bold">{s}: {entry_counts[s]}</span>')

    uid = 0
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>LLM Verify Results</title>
<style>
body {{ background: #fff; color: #222; font-family: 'SF Mono', 'Consolas', monospace; font-size: 13px; margin: 1em 2em; }}
h2 {{ color: #333; }}
table {{ border-collapse: collapse; width: 100%; }}
th {{ text-align: left; padding: 6px 10px; border-bottom: 2px solid #ccc; color: #555;
     position: sticky; top: 0; background: #fff; }}
td {{ padding: 4px 10px; border-bottom: 1px solid #e5e5e5; vertical-align: top; }}
tr:hover {{ background: #f5f5f5; }}
.summary {{ margin-bottom: 1em; font-size: 15px; }}
.summary span {{ margin-right: 2em; }}
.badge {{ display: inline-block; padding: 2px 7px; border-radius: 4px; margin: 1px 2px;
          font-size: 12px; cursor: pointer; font-weight: bold; border: 1px solid transparent;
          position: relative; }}
.badge:hover {{ filter: brightness(0.9); border-color: #999; }}
.badge .tip {{ display: none; position: absolute; bottom: 110%; left: 50%; transform: translateX(-50%);
               background: #333; color: #eee; padding: 4px 8px; border-radius: 4px; font-size: 11px;
               font-weight: normal; white-space: nowrap; max-width: 600px; overflow: hidden;
               text-overflow: ellipsis; z-index: 10; pointer-events: none; }}
.badge:hover .tip {{ display: block; }}
.detail {{ display: none; margin: 6px 0; padding: 8px 12px; background: #f8f8f8;
           border-left: 3px solid #ccc; word-break: break-word;
           font-size: 12px; color: #333; }}
.detail.open {{ display: block; }}
.chunk-title {{ margin-bottom: 4px; border-bottom: 1px solid #ddd; padding-bottom: 3px; }}
.preview-en {{ color: #555; font-style: italic; text-decoration: none; }}
.preview-en:hover {{ text-decoration: underline; }}
.preview-fr {{ color: #2563eb; font-style: italic; text-decoration: none; }}
.preview-fr:hover {{ text-decoration: underline; }}
.entry-link {{ color: #2563eb; text-decoration: none; }}
.entry-link:hover {{ text-decoration: underline; }}
.hw {{ font-size: 15px; direction: rtl; unicode-bidi: isolate; }}
.en-link {{ color: #888; font-size: 11px; text-decoration: none; margin-left: 4px; }}
.en-link:hover {{ color: #555; text-decoration: underline; }}
</style>
<script>
function toggle(id) {{
    var el = document.getElementById(id);
    if (el) el.classList.toggle('open');
}}
</script>
</head><body>
<h2>LLM Verify Results &mdash; {html.escape(results_path.name)}</h2>
<div class="summary">{' '.join(summary_parts)} &nbsp; Total: {len(sorted_entries)} entries</div>
<table>
<tr><th>Entry</th><th>Status</th><th>Chunks</th></tr>
""")
        for base, chunks in sorted_entries:
            w, wsev = worst_status(chunks)
            color = STATUS_COLORS.get(w, "#333")
            stem = bdb_stem(base)

            info_en = load_chunk_info(txt_en_dir, stem, 60)
            info_fr = load_chunk_info(txt_fr_dir, stem, 60)

            sev_str = f" {wsev}" if wsev > 0 else ""
            status_cell = (
                f'<span style="color:{color};font-weight:bold">'
                f'{html.escape(w)}{sev_str}</span>')

            hw = load_head_word(json_dir, stem)
            hw_html = f' <span class="hw">{html.escape(hw)}</span>' if hw else ""
            entry_cell = (
                f'<a class="entry-link" href="Entries_fr/{stem}.html">{html.escape(stem)}</a>'
                f'{hw_html}'
                f'<a class="en-link" href="Entries/{stem}.html">En</a>')

            chunks_sorted = sorted(chunks, key=lambda c: c[0])
            badges_html = ""
            details_html = ""
            for chunk_idx, chunk_total, status, severity, explanation in chunks_sorted:
                uid += 1
                bg = STATUS_BG.get(status, "#f0f0f0")
                fg = STATUS_COLORS.get(status, "#333")
                sev_int = int(severity) if severity.lstrip("-").isdigit() else -1

                clean_text = clean_explanation(explanation)
                tip_preview = analysis_preview(explanation)

                if chunk_total > 0:
                    label = f"{chunk_idx}/{chunk_total}"
                else:
                    label = "1"

                if sev_int > 0 and status != "CORRECT":
                    label += f" ({sev_int})"

                tip_html = f'<span class="tip">{html.escape(tip_preview)}</span>'

                badges_html += (
                    f'<span class="badge" style="background:{bg};color:{fg}" '
                    f'onclick="toggle(\'d{uid}\')">{html.escape(label)}'
                    f'{tip_html}</span>'
                )

                # Detail title: chunk number + En/Fr content previews
                detail_border = STATUS_COLORS.get(status, "#ccc")
                chunk_label = f"{chunk_idx}/{chunk_total}" if chunk_total > 0 else "1"
                lookup_idx = chunk_idx if chunk_idx > 0 else 1
                en_prev = info_en.get(lookup_idx, "")
                fr_prev = info_fr.get(lookup_idx, "")

                fr_url = f"Entries_fr/{stem}.html"
                en_url = f"Entries/{stem}.html"

                title_parts = [
                    f'<span style="color:{fg};font-weight:bold">'
                    f'{html.escape(chunk_label)}</span>'
                ]
                if en_prev:
                    title_parts.append(
                        f'<a class="preview-en" href="{en_url}" target="_blank">'
                        f'{html.escape(en_prev)}</a>')
                if fr_prev:
                    title_parts.append(
                        f'<a class="preview-fr" href="{fr_url}" target="_blank">'
                        f'{html.escape(fr_prev)}</a>')

                title_html = (
                    f'<div class="chunk-title">'
                    f'{"<br>".join(title_parts)}</div>'
                )

                details_html += (
                    f'<div class="detail" id="d{uid}" '
                    f'style="border-left-color:{detail_border}">'
                    f'{title_html}'
                    f'{html.escape(clean_text)}</div>'
                )

            f.write(
                f'<tr>'
                f'<td>{entry_cell}</td>'
                f'<td>{status_cell}</td>'
                f'<td>{badges_html}{details_html}</td>'
                f'</tr>\n'
            )

        f.write("</table></body></html>\n")

    print(f"Wrote {out_path} ({len(sorted_entries)} entries)")


if __name__ == "__main__":
    main()
