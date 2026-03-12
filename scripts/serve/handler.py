"""HTTP request handler: route dispatch, JSON body parsing, static files."""

import json
import mimetypes
import os
import re
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from serve import api, views


class ReviewHandler(BaseHTTPRequestHandler):
    project_root = '.'

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')
        params = parse_qs(parsed.query)

        def param(name, default=None):
            vals = params.get(name, [])
            return vals[0] if vals else default

        def param_set(name):
            vals = params.get(name, [])
            return set(vals) if vals else None

        def param_int_set(name):
            vals = params.get(name, [])
            if not vals:
                return None
            return {int(v) for v in vals if v.isdigit()}

        # Routes
        if path == '' or path == '/':
            self._redirect('/dashboard?mode=txt')
            return

        # Search: /search?q=1234 -> redirect to /review/BDB1234
        if path == '/search':
            q = (param('q') or '').strip()
            mode = param('mode', 'txt')
            # Extract digits from query
            digits = re.sub(r'[^0-9]', '', q)
            if digits:
                self._redirect(f'/review/BDB{digits}?mode={mode}')
            else:
                self._redirect(f'/dashboard?mode={mode}')
            return

        if path == '/dashboard':
            mode = param('mode', 'txt')
            if mode not in ('txt', 'json'):
                mode = 'txt'
            verdict = param_set('verdict')
            digit = param_int_set('digit')
            letter = param_set('letter')
            sort = param('sort', 'severity')
            page = int(param('page', '1'))

            entries, total, verdict_counts, letters = \
                api.get_dashboard_data(
                    self.project_root, mode=mode, verdict_filter=verdict,
                    digit_filter=digit,
                    letter_filter=letter, sort=sort, page=page)

            # Load chunk previews for each entry on this page
            for e in entries:
                e['chunk_previews'] = api.load_chunk_previews(
                    self.project_root, e['stem'])

            html_out = views.render_dashboard(
                entries, total, verdict_counts, letters,
                mode=mode, verdict_filter=verdict,
                digit_filter=digit, letter_filter=letter, sort=sort,
                page=page)
            self._html(html_out)
            return

        # Entry detail: /review/BDB1234
        m = re.match(r'^/review/(BDB\d+)$', path)
        if m:
            stem = m.group(1)
            mode = param('mode', 'txt')
            if mode not in ('txt', 'json'):
                mode = 'txt'

            chunks = api.get_chunks(self.project_root, stem, mode)
            note = api.parse_note(self.project_root, stem, mode)
            head_word = api.load_head_word(self.project_root, stem)

            # Get LLM diagnosis chunks
            results = api.parse_results(self.project_root, mode)
            cfg = api.MODE_CONFIG[mode]
            base_key = stem + cfg['ext']
            llm_chunks = {}
            if base_key in results:
                llm_chunks = results[base_key]['chunks']

            next_stem = api.next_unreviewed(self.project_root, stem, mode)

            # Load per-chunk HTML, staleness, and per-chunk consistency (txt mode)
            html_chunks = None
            is_stale = False
            chunk_consistency = None
            if mode == 'txt':
                html_chunks = api.get_html_chunks(self.project_root, stem)
                is_stale = api.check_html_staleness(self.project_root, stem)
                chunk_consistency = api.check_txt_html_consistency_per_chunk(
                    self.project_root, stem)

            html_out = views.render_entry(
                stem, chunks, note, llm_chunks, mode=mode,
                head_word=head_word, next_stem=next_stem,
                html_chunks=html_chunks, is_stale=is_stale,
                chunk_consistency=chunk_consistency)
            self._html(html_out)
            return

        # API: entry data
        m = re.match(r'^/api/entry/(BDB\d+)$', path)
        if m:
            stem = m.group(1)
            mode = param('mode', 'txt')
            chunks = api.get_chunks(self.project_root, stem, mode)
            note = api.parse_note(self.project_root, stem, mode)
            self._json({'stem': stem, 'chunks': chunks, 'note': note})
            return

        # Static files
        if path.startswith('/static/'):
            self._serve_static(path)
            return

        # Passthrough for project files (read-only)
        safe_path = path.lstrip('/')
        for prefix in ('Entries/', 'Entries_fr/', 'Entries_txt/',
                        'Entries_txt_fr/', 'json_output/', 'json_output_fr/',
                        'Placeholders/'):
            if safe_path.startswith(prefix):
                fpath = os.path.join(self.project_root, safe_path)
                if os.path.isfile(fpath):
                    self._serve_file(fpath)
                    return

        self._error(404, 'Not found')

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path == '/api/save':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, ValueError):
                self._error(400, 'Invalid JSON')
                return

            stem = body.get('stem', '')
            mode = body.get('mode', 'txt')
            note_text = body.get('note_text', '')
            reviewer = body.get('reviewer', 'anonymous')
            chunks_en = body.get('chunks_en')
            chunks_fr = body.get('chunks_fr')
            chunk_verdicts = body.get('chunk_verdicts')

            if not stem:
                self._error(400, 'Missing stem')
                return

            try:
                api.save_note(self.project_root, stem, mode, note_text,
                              reviewer, chunk_verdicts=chunk_verdicts)

                modified = []
                if chunks_en is not None or chunks_fr is not None:
                    modified = api.save_translations(
                        self.project_root, stem, mode,
                        chunks_en=chunks_en, chunks_fr=chunks_fr)

                self._json({'ok': True, 'modified': modified})
            except PermissionError as e:
                self._json({'ok': False, 'error': f'Permission denied: {e}'})
            except Exception as e:
                self._json({'ok': False, 'error': str(e)})
            return

        self._error(404, 'Not found')

    # -------------------------------------------------------------------
    # Response helpers
    # -------------------------------------------------------------------

    def _html(self, content):
        data = content.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, url):
        self.send_response(302)
        self.send_header('Location', url)
        self.end_headers()

    def _error(self, code, msg):
        data = f'<h1>{code}</h1><p>{msg}</p>'.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)

    def _serve_static(self, path):
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'static')
        fname = path.replace('/static/', '', 1)
        # Prevent directory traversal
        fname = os.path.basename(fname)
        fpath = os.path.join(static_dir, fname)
        self._serve_file(fpath)

    def _serve_file(self, fpath):
        if not os.path.isfile(fpath):
            self._error(404, 'Not found')
            return
        ctype, _ = mimetypes.guess_type(fpath)
        if ctype is None:
            ctype = 'application/octet-stream'
        with open(fpath, 'rb') as f:
            data = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        """Quieter logging."""
        pass
