"""HTML rendering for dashboard and entry detail pages."""

import html
import re

from serve.api import (STATUS_COLORS, STATUS_BG, STATUS_RANK,
                        MODE_CONFIG, SORT_MODES, ALL_HEBREW_LETTERS)


def _esc(text):
    return html.escape(text or '', quote=True)


def _page_head(title, mode='txt'):
    return f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(title)}</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<nav class="topbar">
  <a href="/dashboard?mode=txt" class="nav-link {'active' if mode == 'txt' else ''}">TXT Reviews</a>
  <a href="/dashboard?mode=json" class="nav-link {'active' if mode == 'json' else ''}">JSON Reviews</a>
</nav>
'''


def _page_foot():
    return '</body></html>'


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def render_dashboard(entries, total, verdict_counts, letters,
                     mode='txt', verdict_filter=None,
                     digit_filter=None, letter_filter=None, sort='severity',
                     page=1, per_page=100):
    parts = [_page_head(f'BDB Review — {mode.upper()}', mode)]

    # Summary line
    parts.append('<div class="summary">')
    parts.append(f'<h2>LLM Verify Results — {mode.upper()}</h2>')
    for s in ('ERROR', 'WARN', 'CORRECT', 'SKIPPED'):
        c = verdict_counts.get(s, 0)
        if c:
            color = STATUS_COLORS.get(s, '#333')
            parts.append(f'<span style="color:{color};font-weight:bold">{s}: {c}</span>')
    parts.append(f'<span>Total: {total} entries</span>')
    parts.append('</div>')

    # Filter bar with search
    parts.append('<div class="filter-bar">')
    parts.append('<form method="get" action="/dashboard" id="filter-form">')
    parts.append(f'<input type="hidden" name="mode" value="{mode}">')

    # Verdict
    parts.append('<label>Verdict: <select name="verdict">')
    parts.append('<option value="">All</option>')
    for v in ('ERROR', 'WARN', 'CORRECT', 'SKIPPED'):
        sel = 'selected' if verdict_filter and v in verdict_filter else ''
        parts.append(f'<option value="{v}" {sel}>{v}</option>')
    parts.append('</select></label>')

    # Digit
    parts.append('<label>Digit: <select name="digit">')
    parts.append('<option value="">All</option>')
    for d in range(10):
        sel = 'selected' if digit_filter is not None and d in digit_filter else ''
        parts.append(f'<option value="{d}" {sel}>{d}</option>')
    parts.append('</select></label>')

    # Letter — always show all 22 with Hebrew characters
    parts.append('<label>Letter: <select name="letter">')
    parts.append('<option value="">All</option>')
    for name, char in ALL_HEBREW_LETTERS:
        sel = 'selected' if letter_filter and name in letter_filter else ''
        parts.append(f'<option value="{_esc(name)}" {sel}>{char}</option>')
    parts.append('</select></label>')

    # Sort
    parts.append('<label>Sort: <select name="sort">')
    for key, label in SORT_MODES.items():
        sel = 'selected' if sort == key else ''
        parts.append(f'<option value="{key}" {sel}>{label}</option>')
    parts.append('</select></label>')

    parts.append('<button type="submit">Filter</button>')
    parts.append('</form>')

    # Search input (separate from filter form)
    parts.append(f'<form class="search-form" method="get" action="/search">')
    parts.append(f'<input type="hidden" name="mode" value="{mode}">')
    parts.append('<input type="text" name="q" placeholder="BDB number..." '
                 'class="search-input">')
    parts.append('<button type="submit">Go</button>')
    parts.append('</form>')

    parts.append('</div>')

    # Table
    parts.append('<table class="entry-table"><thead><tr>')
    parts.append('<th>Entry</th><th>Status</th><th>Chunks</th></tr></thead><tbody>')

    uid = 0
    for e in entries:
        stem = e['stem']
        ws = e['worst_status']
        wsev = e['worst_severity']
        hw = e['head_word']

        color = STATUS_COLORS.get(ws, '#333')
        sev_str = f' {wsev}' if wsev > 0 else ''
        status_cell = f'<span style="color:{color};font-weight:bold">{_esc(ws)}{sev_str}</span>'
        if e.get('has_note'):
            if e.get('human_note'):
                dot_color, dot_title = '#16a34a', 'human review'
            else:
                dot_color, dot_title = '#eab308', 'LLM review'
            status_cell += f' <span class="review-dot" style="background:{dot_color}" title="{dot_title}"></span>'

        hw_html = f' <span class="hw">{_esc(hw)}</span>' if hw else ''
        entry_cell = (f'<a class="entry-link" href="/review/{stem}?mode={mode}">{stem}</a>'
                      f'{hw_html}'
                      f'<a class="en-link" href="/Entries/{stem}.html" target="_blank">En</a>'
                      f'<a class="fr-link" href="/Entries_fr/{stem}.html" target="_blank">Fr</a>')

        chunks_sorted = sorted(e['chunks'].items(),
                                key=lambda kv: _chunk_sort_key(kv[0]))
        badges_html = ''
        details_html = ''
        for ckey, cdata in chunks_sorted:
            uid += 1
            cs = cdata['status']
            sev = cdata['severity']
            reason = cdata['reason']
            bg = STATUS_BG.get(cs, '#f0f0f0')
            fg = STATUS_COLORS.get(cs, '#333')

            # Label from chunk key
            if ':' in ckey:
                chunk_part = ckey.split(':')[1]
                clabel = chunk_part
            else:
                clabel = '1'

            if sev > 0 and cs != 'CORRECT':
                clabel += f' ({sev})'

            preview = _analysis_preview(reason)

            badges_html += (
                f'<span class="badge" style="background:{bg};color:{fg}" '
                f'onclick="toggle(\'d{uid}\')">'
                f'{_esc(clabel)}'
                f'<span class="tip">{_esc(preview)}</span>'
                f'</span>')

            # Detail dropdown with EN/FR previews
            detail_border = STATUS_COLORS.get(cs, '#ccc')
            clean = _clean_explanation(reason)

            # Get chunk previews from entry data
            en_prev = e.get('chunk_previews', {}).get('en', {})
            fr_prev = e.get('chunk_previews', {}).get('fr', {})
            # Extract chunk index from key (e.g. "BDB1234.txt:2/5" -> 2)
            chunk_idx = _chunk_index_from_key(ckey)

            preview_html = ''
            en_p = en_prev.get(chunk_idx, '')
            fr_p = fr_prev.get(chunk_idx, '')
            if en_p or fr_p:
                if en_p:
                    preview_html += f'<div class="detail-preview en-preview">{_esc(en_p)}</div>'
                if fr_p:
                    preview_html += f'<div class="detail-preview fr-preview">{_esc(fr_p)}</div>'

            details_html += (
                f'<div class="detail" id="d{uid}" '
                f'style="border-left-color:{detail_border}">'
                f'{preview_html}'
                f'<div class="detail-analysis">{_esc(clean)}</div>'
                f'</div>')

        parts.append(f'<tr><td>{entry_cell}</td><td>{status_cell}</td>'
                     f'<td>{badges_html}{details_html}</td></tr>')

    parts.append('</tbody></table>')

    # Pagination
    total_pages = max(1, (total + per_page - 1) // per_page)
    if total_pages > 1:
        parts.append('<div class="pagination">')
        bp = _build_params(mode, verdict_filter, digit_filter,
                           letter_filter, sort)
        if page > 1:
            parts.append(f'<a href="/dashboard?{bp}&page={page-1}">&laquo; Prev</a>')
        parts.append(f'<span>Page {page}/{total_pages}</span>')
        if page < total_pages:
            parts.append(f'<a href="/dashboard?{bp}&page={page+1}">Next &raquo;</a>')
        parts.append('</div>')

    parts.append('<script>function toggle(id){var e=document.getElementById(id);'
                 'if(e)e.classList.toggle("open");}</script>')
    parts.append(_page_foot())
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Entry detail
# ---------------------------------------------------------------------------

def render_entry(stem, chunks, note, llm_chunks, mode='txt', head_word='',
                 next_stem=None, html_content=None, html_chunks=None,
                 is_stale=False, chunk_consistency=None):
    """Render entry detail page.

    html_chunks: list of {label, type, en_html, fr_html} for per-chunk HTML.
    is_stale: True if txt_fr is newer than Entries_fr HTML.
    chunk_consistency: list of per-chunk {en: {match, diff_count}, fr: ...}.
    """
    parts = [_page_head(f'{stem} — Review', mode)]

    # Header with source links
    parts.append(f'<div class="entry-header">')
    parts.append(f'<h1>{_esc(stem)} <span class="hw">{_esc(head_word)}</span>'
                 f' <a class="en-link" href="/Entries/{stem}.html" target="_blank">En</a>'
                 f' <a class="fr-link" href="/Entries_fr/{stem}.html" target="_blank">Fr</a>'
                 f'</h1>')
    parts.append(f'<div class="entry-nav">')
    parts.append(f'<a href="/dashboard?mode={mode}">&laquo; Dashboard</a>')
    if next_stem:
        parts.append(f' | <a href="/review/{next_stem}?mode={mode}">Next unreviewed &raquo;</a>')
    parts.append(f'</div></div>')

    # Staleness banner
    if is_stale:
        parts.append('<div class="banner-warn">'
                     '&#9888; HTML out of date — txt_fr is newer than Entries_fr</div>')

    # Modified banner (hidden until JS detects edits)
    parts.append('<div id="modified-banner" class="banner-warn" style="display:none">'
                 'Translations modified — save to persist changes</div>')

    # Per-chunk sections with HTML rendering
    total_chunks = len(chunks)

    for i, chunk in enumerate(chunks):
        chunk_num = i + 1
        ctype = chunk.get('type', 'whole')
        label = chunk.get('label', str(chunk_num))

        # LLM diagnosis for this chunk (original values from results file)
        cfg = MODE_CONFIG[mode]
        if total_chunks > 1:
            chunk_key = f'{stem}{cfg["ext"]}:{chunk_num}/{total_chunks}'
        else:
            chunk_key = f'{stem}{cfg["ext"]}'
        llm_diag = llm_chunks.get(chunk_key, {})
        llm_status = llm_diag.get('status', '')
        llm_severity = llm_diag.get('severity', 0)
        diag_reason = llm_diag.get('reason', '')

        # Check for human verdict overrides
        chunk_verdicts = note.get('chunk_verdicts', {})
        cv = chunk_verdicts.get(str(chunk_num))
        is_human = False
        if cv and (cv['status'] != llm_status or cv['severity'] != llm_severity):
            diag_status = cv['status']
            diag_severity = cv['severity']
            is_human = True
        else:
            diag_status = llm_status
            diag_severity = llm_severity

        # CORRECT chunks collapsed by default
        is_ok = (diag_status == 'CORRECT')
        collapsed_class = ' collapsed' if is_ok else ''
        body_display = 'display:none' if is_ok else ''

        parts.append(f'<div class="chunk-section{collapsed_class}" data-chunk="{chunk_num}">')

        # Chunk title bar
        parts.append(f'<div class="chunk-title-bar">')
        parts.append(f'<span class="chunk-label" onclick="toggleChunk({chunk_num})">'
                     f'{_esc(label)}: {_esc(ctype)}</span>')

        # Status badge — clickable dropdown to change verdict + severity
        if diag_status:
            ds_bg = STATUS_BG.get(diag_status, '#eee')
            ds_fg = STATUS_COLORS.get(diag_status, '#666')
            # Editable verdict dropdown (styled as badge)
            parts.append(f'<select class="verdict-select" data-chunk="{chunk_num}" '
                         f'data-llm-status="{_esc(llm_status)}" '
                         f'data-llm-severity="{llm_severity}" '
                         f'style="background:{ds_bg};color:{ds_fg}" '
                         f'onchange="verdictChanged(this)">')
            for vs in ('ERROR', 'WARN', 'CORRECT', 'SKIPPED'):
                sel = 'selected' if diag_status == vs else ''
                parts.append(f'<option value="{vs}" {sel}>{vs}</option>')
            parts.append('</select>')
            # Severity input
            parts.append(f'<input type="number" class="severity-input" data-chunk="{chunk_num}" '
                         f'value="{diag_severity}" min="0" max="10" '
                         f'onchange="verdictChanged(this)">')
            # (llm) or (human) indicator
            source_label = '(human)' if is_human else '(llm)'
            source_class = 'source-human' if is_human else 'source-llm'
            parts.append(f'<span class="verdict-source {source_class}" '
                         f'id="source-{chunk_num}">{source_label}</span>')
        else:
            # No LLM diagnosis — show empty
            parts.append('<span class="badge" style="background:#eee;color:#999">—</span>')

        # Edit button
        parts.append(f'<button class="btn-edit" onclick="toggleEdit({chunk_num})">Edit</button>')

        # Collapse/expand arrow
        arrow = '&#9654;' if is_ok else '&#9660;'
        parts.append(f'<span class="chunk-toggle" id="toggle-{chunk_num}" '
                     f'onclick="toggleChunk({chunk_num})">{arrow}</span>')

        parts.append('</div>')  # chunk-title-bar

        parts.append(f'<div class="chunk-body" id="chunk-body-{chunk_num}" style="{body_display}">')

        # Per-chunk rendered HTML (if available)
        # Build per-chunk consistency badges for EN/FR
        cc_badges = {'en': '', 'fr': ''}
        if chunk_consistency and i < len(chunk_consistency):
            cc = chunk_consistency[i]
            for lang in ('en', 'fr'):
                info = cc.get(lang)
                if info is None:
                    pass
                elif info['match']:
                    cc_badges[lang] = (' <span class="consistency-ok chunk-consistency">'
                                       'txt=html</span>')
                else:
                    dc = info['diff_count']
                    diff_id = f'cc-{lang}-{chunk_num}'
                    diffs = info.get('diffs', [])
                    diff_lines = ''.join(f'<div>{_esc(d)}</div>' for d in diffs)
                    cc_badges[lang] = (
                        f' <span class="consistency-diff chunk-consistency clickable" '
                        f'onclick="toggle(\'{diff_id}\')">'
                        f'txt&#8800;html ({dc} diff{"s" if dc != 1 else ""})</span>'
                        f'<div class="consistency-details" id="{diff_id}">'
                        f'{diff_lines}</div>')

        if html_chunks and i < len(html_chunks):
            hc = html_chunks[i]
            en_h = hc.get('en_html', '')
            fr_h = hc.get('fr_html', '')
            if en_h or fr_h:
                parts.append(f'<div class="html-render-inline side-by-side" '
                             f'id="html-view-{chunk_num}">')
                if en_h:
                    parts.append('<div class="side-panel">')
                    parts.append(f'<div class="side-label">English (HTML){cc_badges["en"]}</div>')
                    parts.append(f'<div class="html-frame">{_sanitize_entry_html(en_h)}</div>')
                    parts.append('</div>')
                if fr_h:
                    parts.append('<div class="side-panel">')
                    parts.append(f'<div class="side-label">French (HTML){cc_badges["fr"]}</div>')
                    parts.append(f'<div class="html-frame">{_sanitize_entry_html(fr_h)}</div>')
                    parts.append('</div>')
                parts.append('</div>')

        # Side by side txt — hidden by default, shown when Edit clicked
        parts.append(f'<div class="txt-section" id="txt-section-{chunk_num}" style="display:none">')
        parts.append('<div class="side-by-side">')

        # English txt
        parts.append('<div class="side-panel">')
        parts.append('<div class="side-label">English (txt)</div>')
        parts.append(f'<div class="text-view" id="en-view-{chunk_num}">'
                     f'<pre>{_esc(chunk["en_text"])}</pre></div>')
        parts.append(f'<textarea class="text-edit" id="en-edit-{chunk_num}" '
                     f'style="display:none">{_esc(chunk["en_text"])}</textarea>')
        parts.append('</div>')

        # French txt
        parts.append('<div class="side-panel">')
        parts.append('<div class="side-label">French (txt)</div>')
        parts.append(f'<div class="text-view" id="fr-view-{chunk_num}">'
                     f'<pre>{_esc(chunk["fr_text"])}</pre></div>')
        parts.append(f'<textarea class="text-edit" id="fr-edit-{chunk_num}" '
                     f'style="display:none">{_esc(chunk["fr_text"])}</textarea>')
        parts.append('</div>')

        parts.append('</div>')  # side-by-side
        parts.append('</div>')  # txt-section

        # LLM diagnosis
        if diag_reason:
            parts.append(f'<div class="llm-diagnosis">')
            parts.append(f'<strong>LLM Diagnosis ({diag_status}'
                         f'{" " + str(diag_severity) if diag_severity > 0 else ""}):</strong> '
                         f'{_esc(_clean_explanation(diag_reason))}')
            parts.append(f'</div>')

        parts.append('</div>')  # chunk-body
        parts.append('</div>')  # chunk-section

    # Notes panel
    parts.append('<div class="notes-panel">')
    parts.append('<h2>Notes</h2>')

    parts.append('<div class="note-fields">')
    parts.append(f'<label>Notes:<br>'
                 f'<textarea id="note-text" rows="6">{_esc(note.get("text", ""))}</textarea>'
                 f'</label>')

    reviewer_val = note.get('reviewer', '') or 'LLM'
    parts.append(f'<label>Reviewer: '
                 f'<input type="text" id="reviewer" value="{_esc(reviewer_val)}" '
                 f'placeholder="Your name">'
                 f'</label>')

    parts.append('</div>')

    parts.append(f'<div class="note-actions">')
    parts.append(f'<button class="btn-save" onclick="saveAll(\'{stem}\', \'{mode}\')">Save All</button>')
    if next_stem:
        parts.append(f'<a href="/review/{next_stem}?mode={mode}" class="btn-next">'
                     f'Next Unreviewed &raquo;</a>')
    parts.append(f'</div>')

    parts.append('<div id="save-status"></div>')
    parts.append('</div>')

    parts.append(f'<script>var TOTAL_CHUNKS = {total_chunks};</script>')
    parts.append('<script src="/static/review.js"></script>')
    parts.append(_page_foot())
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chunk_sort_key(ckey):
    """Sort key for chunk keys like 'BDB1234.txt:2/5'."""
    if ':' in ckey:
        part = ckey.split(':')[1]
        m = re.match(r'(\d+)', part)
        if m:
            return int(m.group(1))
    return 0


def _chunk_index_from_key(ckey):
    """Extract 1-based chunk index from key like 'BDB1234.txt:2/5'."""
    if ':' in ckey:
        part = ckey.split(':')[1]
        m = re.match(r'(\d+)', part)
        if m:
            return int(m.group(1))
    return 1


def _clean_explanation(explanation):
    """Strip leading quote and section prefix."""
    text = explanation.strip().strip('"')
    m = re.match(r'^(header|sense|stem|footer):\s*', text, re.IGNORECASE)
    if m:
        text = text[m.end():]
    return text


def _analysis_preview(explanation):
    """Short preview for tooltip."""
    text = _clean_explanation(explanation)
    m = re.match(r'Analyse\s*:\s*', text)
    if m:
        text = text[m.end():]
    if len(text) > 120:
        text = text[:117] + '...'
    return text


def _sanitize_entry_html(raw_html):
    """Prepare BDB entry HTML for safe inline rendering."""
    text = re.sub(r'<html[^>]*>|</html>', '', raw_html, flags=re.IGNORECASE)
    text = re.sub(r'<head[^>]*>.*?</head>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<body[^>]*>|</body>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<link[^>]*>', '', text, flags=re.IGNORECASE)
    return f'<div class="entry-html-content">{text}</div>'


def _build_params(mode, verdict_filter, digit_filter,
                  letter_filter, sort):
    """Build query string params for pagination links."""
    params = [f'mode={mode}']
    if verdict_filter:
        for v in sorted(verdict_filter):
            params.append(f'verdict={v}')
    if digit_filter is not None:
        for d in sorted(digit_filter):
            params.append(f'digit={d}')
    if letter_filter:
        for ltr in sorted(letter_filter):
            params.append(f'letter={ltr}')
    if sort != 'severity':
        params.append(f'sort={sort}')
    return '&'.join(params)
