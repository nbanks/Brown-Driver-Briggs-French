/* BDB Review — client-side logic */

// Restore reviewer name from localStorage (overrides default "LLM")
(function() {
    var saved = localStorage.getItem('bdb-reviewer');
    if (saved && saved !== 'LLM') {
        var el = document.getElementById('reviewer');
        if (el && (!el.value || el.value === 'LLM')) el.value = saved;
    }
})();

var editStates = {};
var modified = false;

function toggle(id) {
    var el = document.getElementById(id);
    if (el) el.classList.toggle('open');
}

function toggleSection(id) {
    var el = document.getElementById(id);
    if (!el) return;
    var btn = el.parentNode.querySelector('.btn-toggle');
    if (el.style.display === 'none') {
        el.style.display = '';
        if (btn) btn.textContent = 'Hide';
    } else {
        el.style.display = 'none';
        if (btn) btn.textContent = 'Show';
    }
}

function toggleChunk(n) {
    var body = document.getElementById('chunk-body-' + n);
    var toggle = document.getElementById('toggle-' + n);
    if (!body) return;
    if (body.style.display === 'none') {
        body.style.display = '';
        if (toggle) toggle.innerHTML = '&#9660;';
    } else {
        body.style.display = 'none';
        if (toggle) toggle.innerHTML = '&#9654;';
    }
}

function toggleEdit(n) {
    var txtSection = document.getElementById('txt-section-' + n);
    var enView = document.getElementById('en-view-' + n);
    var enEdit = document.getElementById('en-edit-' + n);
    var frView = document.getElementById('fr-view-' + n);
    var frEdit = document.getElementById('fr-edit-' + n);
    if (!txtSection || !enView || !enEdit) return;

    var section = txtSection.closest('.chunk-section');
    var btn = section ? section.querySelector('.btn-edit') : null;

    if (editStates[n]) {
        // Exit edit mode: update view text, hide txt section
        enView.querySelector('pre').textContent = enEdit.value;
        frView.querySelector('pre').textContent = frEdit.value;
        enView.style.display = '';
        enEdit.style.display = 'none';
        frView.style.display = '';
        frEdit.style.display = 'none';
        txtSection.style.display = 'none';
        if (btn) { btn.classList.remove('active'); btn.textContent = 'Edit'; }
        editStates[n] = false;
    } else {
        // Enter edit mode: show txt section with textareas
        txtSection.style.display = '';
        enView.style.display = 'none';
        enEdit.style.display = '';
        frView.style.display = 'none';
        frEdit.style.display = '';
        if (btn) { btn.classList.add('active'); btn.textContent = 'Done'; }
        editStates[n] = true;
        frEdit.focus();
    }
}

// Verdict dropdown changed — update styling and (llm)/(human) label
var STATUS_BG = {CORRECT:'#dcfce7', ERROR:'#fee2e2', WARN:'#fef9c3', SKIPPED:'#e0f2fe'};
var STATUS_FG = {CORRECT:'#1a7d1a', ERROR:'#b91c1c', WARN:'#a16207', SKIPPED:'#4a8a8a'};

function verdictChanged(el) {
    var bar = el.closest('.chunk-title-bar');
    var sel = bar.querySelector('.verdict-select');
    var sevInput = bar.querySelector('.severity-input');
    var sourceEl = bar.querySelector('.verdict-source');
    if (sel) {
        var v = sel.value;
        sel.style.background = STATUS_BG[v] || '#eee';
        sel.style.color = STATUS_FG[v] || '#333';
    }
    // Update (llm)/(human) indicator
    if (sel && sourceEl) {
        var llmStatus = sel.getAttribute('data-llm-status');
        var llmSev = parseInt(sel.getAttribute('data-llm-severity')) || 0;
        var curSev = sevInput ? (parseInt(sevInput.value) || 0) : 0;
        if (sel.value !== llmStatus || curSev !== llmSev) {
            sourceEl.textContent = '(human)';
            sourceEl.className = 'verdict-source source-human';
        } else {
            sourceEl.textContent = '(llm)';
            sourceEl.className = 'verdict-source source-llm';
        }
    }
    markModified();
}

function markModified() {
    if (!modified) {
        modified = true;
        var banner = document.getElementById('modified-banner');
        if (banner) banner.style.display = '';
    }
}

// Detect text modifications
document.addEventListener('input', function(e) {
    if (e.target.classList.contains('text-edit')) {
        markModified();
    }
});

function saveAll(stem, mode) {
    var statusEl = document.getElementById('save-status');
    statusEl.textContent = 'Saving...';
    statusEl.className = '';

    var reviewer = document.getElementById('reviewer').value.trim();
    if (!reviewer || reviewer === 'LLM') {
        statusEl.textContent = 'Please enter your name in the Reviewer field before saving.';
        statusEl.className = 'save-err';
        document.getElementById('reviewer').focus();
        return;
    }
    localStorage.setItem('bdb-reviewer', reviewer);

    var chunksEn = null;
    var chunksFr = null;

    // Only collect text chunks if any were actually edited
    var anyTextEdited = Object.keys(editStates).some(function(k) { return editStates[k]; });
    if (anyTextEdited && typeof TOTAL_CHUNKS !== 'undefined') {
        chunksEn = [];
        chunksFr = [];
        for (var i = 1; i <= TOTAL_CHUNKS; i++) {
            var enEdit = document.getElementById('en-edit-' + i);
            var frEdit = document.getElementById('fr-edit-' + i);
            chunksEn.push(enEdit ? enEdit.value : '');
            chunksFr.push(frEdit ? frEdit.value : '');
        }
    }

    // Collect per-chunk verdict overrides (only if changed from LLM)
    var chunkVerdicts = {};
    var vselects = document.querySelectorAll('.verdict-select');
    for (var i = 0; i < vselects.length; i++) {
        var vsel = vselects[i];
        var cn = vsel.getAttribute('data-chunk');
        var sev = vsel.closest('.chunk-title-bar').querySelector('.severity-input');
        var curStatus = vsel.value;
        var curSev = sev ? parseInt(sev.value) || 0 : 0;
        var llmStatus = vsel.getAttribute('data-llm-status');
        var llmSev = parseInt(vsel.getAttribute('data-llm-severity')) || 0;
        // Only store if different from LLM
        if (curStatus !== llmStatus || curSev !== llmSev) {
            chunkVerdicts[cn] = {
                status: curStatus,
                severity: curSev
            };
        }
    }

    var payload = {
        stem: stem,
        mode: mode,
        note_text: document.getElementById('note-text').value,
        reviewer: reviewer,
        chunks_en: chunksEn,
        chunks_fr: chunksFr,
        chunk_verdicts: Object.keys(chunkVerdicts).length > 0 ? chunkVerdicts : null
    };

    fetch('/api/save', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.ok) {
            modified = false;
            // If text files were modified, reload to refresh consistency checks
            if (data.modified && data.modified.length > 0) {
                window.location.reload();
                return;
            }
            statusEl.textContent = 'Saved.';
            statusEl.className = 'save-ok';
            var banner = document.getElementById('modified-banner');
            if (banner) banner.style.display = 'none';
        } else {
            statusEl.textContent = 'Error: ' + (data.error || 'unknown');
            statusEl.className = 'save-err';
        }
    })
    .catch(function(err) {
        statusEl.textContent = 'Error: ' + err;
        statusEl.className = 'save-err';
    });
}

// Keyboard shortcuts: Ctrl+S save, Ctrl+Right next
document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        var saveBtn = document.querySelector('.btn-save');
        if (saveBtn) saveBtn.click();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'ArrowRight') {
        e.preventDefault();
        var nextLink = document.querySelector('.btn-next');
        if (nextLink) window.location = nextLink.href;
    }
});
