from django.http import HttpResponse
from django.conf import settings


def index(request):
    """Patent Lookup page — search any patent by number and view details."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Patent Lookup — TriangleIP</title>
<link rel='stylesheet' href='/static/tip_design.css'>
<style>
  .tip-search-box {
    display: flex;
    gap: 10px;
    margin-bottom: 24px;
    align-items: stretch;
  }
  .tip-search-box input {
    flex: 1;
    padding: 10px 14px;
    border: 1px solid var(--tip-border, #d0d5dd);
    border-radius: 8px;
    font-size: 15px;
    font-family: inherit;
    outline: none;
    transition: border-color .2s;
  }
  .tip-search-box input:focus {
    border-color: var(--tip-primary);
    box-shadow: 0 0 0 3px rgba(59,130,246,.15);
  }
  .suggestions-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: #fff;
    border: 1px solid var(--tip-border, #d0d5dd);
    border-radius: 8px;
    max-height: 260px;
    overflow-y: auto;
    z-index: 100;
    box-shadow: 0 8px 24px rgba(0,0,0,.12);
    display: none;
  }
  .suggestions-dropdown.open { display: block; }
  .suggestion-item {
    padding: 10px 14px;
    cursor: pointer;
    border-bottom: 1px solid #f0f0f0;
    font-size: 14px;
  }
  .suggestion-item:last-child { border-bottom: none; }
  .suggestion-item:hover { background: #f5f8ff; }
  .suggestion-item .sug-number { font-weight: 600; color: var(--tip-primary); }
  .suggestion-item .sug-title { color: var(--tip-text-secondary, #666); margin-left: 8px; }
  .search-wrapper { position: relative; flex: 1; }
  .detail-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
    margin-top: 20px;
  }
  .detail-card-label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: .5px;
    color: var(--tip-text-secondary, #666);
    margin-bottom: 4px;
  }
  .detail-card-value {
    font-size: 18px;
    font-weight: 600;
    color: var(--tip-text, #1a1a2e);
    word-break: break-word;
  }
  .status-tag { display: inline-block; }
  .loading-spinner {
    display: inline-block;
    width: 18px; height: 18px;
    border: 2px solid var(--tip-border, #d0d5dd);
    border-top-color: var(--tip-primary);
    border-radius: 50%;
    animation: spin .6s linear infinite;
    margin-right: 8px;
    vertical-align: middle;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .error-card { border-left: 4px solid #e74c3c; }
  .empty-state {
    text-align: center;
    padding: 60px 20px;
    color: var(--tip-text-secondary, #666);
  }
  .empty-state .empty-icon { font-size: 48px; margin-bottom: 16px; opacity: .4; }
  .diagnostics-table td, .diagnostics-table th {
    padding: 6px 12px;
    font-size: 13px;
    text-align: left;
    vertical-align: top;
  }
  .diagnostics-table th {
    white-space: nowrap;
    color: var(--tip-text-secondary, #666);
    font-weight: 500;
  }
</style>
</head>
<body>
<div class='tip-page'>
  <nav class='tip-navbar'>
    <a class='tip-navbar-brand' href='/'>TriangleIP</a>
  </nav>

  <h1 class='tip-page-title'>Patent Lookup</h1>
  <p style="color:var(--tip-text-secondary);margin-bottom:24px;">
    Enter a US application, publication, or patent number to retrieve details.
  </p>

  <!-- Search -->
  <div class='tip-card'>
    <div class='tip-search-box'>
      <div class='search-wrapper'>
        <input
          type='text'
          id='searchInput'
          placeholder='e.g. 16/687,273  |  US8623891  |  EP1514569A1'
          autocomplete='off'
        />
        <div class='suggestions-dropdown' id='suggestionsDropdown'></div>
      </div>
      <button class='tip-btn tip-btn-primary' id='searchBtn' onclick='doSearch()'>
        Search
      </button>
    </div>
  </div>

  <!-- Results area -->
  <div id='resultsArea'>
    <div class='empty-state'>
      <div class='empty-icon'>&#128269;</div>
      <p>Enter a patent number above to get started.</p>
    </div>
  </div>

  <!-- Diagnostics -->
  <div class='tip-card' style='margin-top:32px;'>
    <details>
      <summary style='cursor:pointer;font-weight:600;'>Diagnostics</summary>
      <div style='margin-top:12px;'>
        <div class='tip-table-wrap'>
          <table class='tip-table diagnostics-table' id='diagnosticsTable'>
            <tbody>
              <tr><th>Request</th><td id='diagRequest'>—</td></tr>
              <tr><th>API Calls</th><td id='diagApiCalls'>—</td></tr>
              <tr><th>Input Parameters</th><td id='diagInput'>—</td></tr>
              <tr><th>Output Parameters</th><td id='diagOutput'>—</td></tr>
              <tr><th>Field Mapping</th><td id='diagMapping'>—</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </details>
  </div>
</div>

<script>
const USER_REQUEST = "Let me look up any patent by its number and show me the details \\u2014 title, status, filing date, inventor, and examiner.";

// ── Suggestion autocomplete ──
const searchInput = document.getElementById('searchInput');
const suggestionsDropdown = document.getElementById('suggestionsDropdown');
let suggestTimer = null;

searchInput.addEventListener('input', function() {
  clearTimeout(suggestTimer);
  const q = this.value.trim();
  if (q.length < 5) {
    suggestionsDropdown.classList.remove('open');
    suggestionsDropdown.innerHTML = '';
    return;
  }
  suggestTimer = setTimeout(() => fetchSuggestions(q), 300);
});

searchInput.addEventListener('keydown', function(e) {
  if (e.key === 'Enter') {
    e.preventDefault();
    suggestionsDropdown.classList.remove('open');
    doSearch();
  }
});

async function fetchSuggestions(q) {
  try {
    const resp = await fetch('/tip-api/v1/patent-lookup/suggest?q=' + encodeURIComponent(q) + '&limit=8');
    const json = await resp.json();
    if (!json.status || !json.data || !json.data.results || json.data.results.length === 0) {
      suggestionsDropdown.classList.remove('open');
      suggestionsDropdown.innerHTML = '';
      return;
    }
    let html = '';
    json.data.results.forEach(function(r) {
      html += '<div class="suggestion-item" data-value="' + escHtml(r.id) + '">'
            + '<span class="sug-number">' + escHtml(r.display) + '</span>'
            + '<span class="sug-title">' + escHtml(r.title || '') + '</span>'
            + '</div>';
    });
    suggestionsDropdown.innerHTML = html;
    suggestionsDropdown.classList.add('open');

    suggestionsDropdown.querySelectorAll('.suggestion-item').forEach(function(el) {
      el.addEventListener('click', function() {
        searchInput.value = this.dataset.value;
        suggestionsDropdown.classList.remove('open');
        doSearch();
      });
    });
  } catch (err) {
    // silently ignore suggestion errors
  }
}

document.addEventListener('click', function(e) {
  if (!e.target.closest('.search-wrapper')) {
    suggestionsDropdown.classList.remove('open');
  }
});

// ── Search ──
async function doSearch() {
  const query = searchInput.value.trim();
  if (!query) return;

  const resultsArea = document.getElementById('resultsArea');
  resultsArea.innerHTML = '<div class="tip-card" style="text-align:center;padding:40px;">'
    + '<span class="loading-spinner"></span> Searching&hellip;</div>';

  const apiCalls = [];
  const startTime = Date.now();

  try {
    const resp = await fetch('/tip-api/v1/patent-lookup/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query })
    });
    const elapsed = Date.now() - startTime;
    let json;
    try { json = await resp.json(); } catch(e) { json = null; }

    apiCalls.push({
      method: 'POST',
      path: '/tip-api/v1/patent-lookup/search',
      status: resp.status,
      elapsed: elapsed + 'ms'
    });

    if (!json || !json.status) {
      const msg = (json && json.message) ? json.message : 'Unknown error';
      resultsArea.innerHTML = renderErrorCard('Search failed: ' + msg);
      updateDiagnostics(apiCalls, { query: query }, null, null);
      return;
    }

    const summary = json.data.result.summary;
    renderResults(summary, json.data.quota);
    updateDiagnostics(apiCalls, { query: query }, summary, json.data.quota);

  } catch (err) {
    resultsArea.innerHTML = renderErrorCard('Network error: ' + err.message);
    updateDiagnostics(apiCalls, { query: query }, null, null);
  }
}

// ── Render results ──
function renderResults(s, quota) {
  const statusLabel = s.status || '—';
  let statusClass = 'tip-tag-default';
  const sl = statusLabel.toLowerCase();
  if (sl.includes('patent')) statusClass = 'tip-tag-success';
  else if (sl.includes('pend') || sl.includes('active')) statusClass = 'tip-tag-primary';
  else if (sl.includes('aban')) statusClass = 'tip-tag-error';
  else if (sl.includes('expir')) statusClass = 'tip-tag-warning';

  let quotaHtml = '';
  if (quota) {
    quotaHtml = '<div class="tip-card" style="margin-top:16px;">'
      + '<div class="detail-card-label">API Quota</div>'
      + '<div class="detail-card-value" style="font-size:14px;">'
      + quota.used + ' / ' + quota.limit + ' used &nbsp;'
      + '<span class="tip-tag ' + (quota.remaining < 10 ? 'tip-tag-error' : 'tip-tag-success') + '">'
      + quota.remaining + ' remaining</span>'
      + '</div></div>';
  }

  const html = ''
    + '<div class="tip-card" style="margin-top:20px;">'
    + '  <h2 style="margin:0 0 6px 0;font-size:20px;">' + escHtml(s.title || '—') + '</h2>'
    + '  <div style="margin-bottom:16px;">'
    + '    <span class="tip-tag ' + statusClass + '">' + escHtml(statusLabel) + '</span>'
    + '    <span class="tip-tag tip-tag-default" style="margin-left:6px;">' + escHtml(s.application_type || '—') + '</span>'
    + '  </div>'
    + '</div>'

    + '<div class="detail-grid">'

    + detailCard('Application Number', s.application_number ? formatAppNum(s.application_number) : '—')
    + detailCard('Patent Number', s.patent_number || '—')
    + detailCard('Filing Date', s.filing_date || '—')
    + detailCard('Grant Date', s.grant_date || '—')
    + detailCard('Status Date', s.status_date || '—')
    + detailCard('First Inventor', s.first_inventor_name || '—')
    + detailCard('Examiner', s.examiner_name || '—')
    + detailCard('First Applicant', s.first_applicant_name || '—')
    + detailCard('Group Art Unit', s.group_art_unit || '—')
    + detailCard('Class / Subclass', s.class_subclass || '—')
    + detailCard('Entity Status', s.entity_status || '—')
    + detailCard('Earliest Publication', (s.earliest_publication_number || '—') + (s.earliest_publication_date ? ' (' + s.earliest_publication_date + ')' : ''))

    + '</div>'

    + quotaHtml;

  document.getElementById('resultsArea').innerHTML = html;
}

function detailCard(label, value) {
  return '<div class="tip-card">'
    + '<div class="detail-card-label">' + escHtml(label) + '</div>'
    + '<div class="detail-card-value">' + escHtml(value) + '</div>'
    + '</div>';
}

function formatAppNum(num) {
  // Format like 16687273 -> 16/687,273
  const s = String(num);
  if (s.length <= 2) return s;
  const prefix = s.substring(0, 2);
  const rest = s.substring(2);
  if (rest.length <= 3) return prefix + '/' + rest;
  return prefix + '/' + rest.slice(0, -3) + ',' + rest.slice(-3);
}

function renderErrorCard(msg) {
  return '<div class="tip-card error-card" style="margin-top:20px;">'
    + '<div class="detail-card-label" style="color:#e74c3c;">Error</div>'
    + '<div class="detail-card-value" style="font-size:15px;color:#e74c3c;">' + escHtml(msg) + '</div>'
    + '</div>';
}

// ── Diagnostics ──
function updateDiagnostics(apiCalls, inputParams, summary, quota) {
  document.getElementById('diagRequest').textContent = USER_REQUEST;

  let callsHtml = '';
  apiCalls.forEach(function(c) {
    callsHtml += c.method + ' ' + c.path + ' &rarr; HTTP ' + c.status + ' (' + c.elapsed + ')<br>';
  });
  document.getElementById('diagApiCalls').innerHTML = callsHtml || '—';

  let inputHtml = '<code style="font-size:13px;">';
  if (inputParams) {
    Object.keys(inputParams).forEach(function(k) {
      inputHtml += escHtml(k) + ' = ' + escHtml(String(inputParams[k])) + '<br>';
    });
  }
  inputHtml += '</code>';
  document.getElementById('diagInput').innerHTML = inputHtml;

  let outputHtml = '<code style="font-size:13px;">';
  if (summary) {
    const fields = [
      'application_number','patent_number','title','status','filing_date',
      'grant_date','status_date','application_type','examiner_name',
      'first_inventor_name','first_applicant_name','group_art_unit',
      'class_subclass','entity_status','earliest_publication_number',
      'earliest_publication_date'
    ];
    fields.forEach(function(f) {
      if (summary[f] !== undefined && summary[f] !== null) {
        outputHtml += 'data.result.summary.' + f + ' = ' + escHtml(String(summary[f])) + '<br>';
      }
    });
    if (quota) {
      outputHtml += 'data.quota.used = ' + quota.used + '<br>';
      outputHtml += 'data.quota.limit = ' + quota.limit + '<br>';
      outputHtml += 'data.quota.remaining = ' + quota.remaining + '<br>';
    }
  } else {
    outputHtml = '—';
  }
  outputHtml += '</code>';
  document.getElementById('diagOutput').innerHTML = outputHtml;

  const mapping = [
    ['data.result.summary.title', 'Page heading (title)'],
    ['data.result.summary.status', 'Status tag'],
    ['data.result.summary.application_type', 'Application type tag'],
    ['data.result.summary.application_number', 'Application Number card'],
    ['data.result.summary.patent_number', 'Patent Number card'],
    ['data.result.summary.filing_date', 'Filing Date card'],
    ['data.result.summary.grant_date', 'Grant Date card'],
    ['data.result.summary.status_date', 'Status Date card'],
    ['data.result.summary.first_inventor_name', 'First Inventor card'],
    ['data.result.summary.examiner_name', 'Examiner card'],
    ['data.result.summary.first_applicant_name', 'First Applicant card'],
    ['data.result.summary.group_art_unit', 'Group Art Unit card'],
    ['data.result.summary.class_subclass', 'Class / Subclass card'],
    ['data.result.summary.entity_status', 'Entity Status card'],
    ['data.result.summary.earliest_publication_number', 'Earliest Publication card'],
    ['data.result.summary.earliest_publication_date', 'Earliest Publication card (date)'],
    ['data.quota', 'API Quota card'],
  ];
  let mapHtml = '<table class="tip-table diagnostics-table" style="margin:0;">';
  mapping.forEach(function(m) {
    mapHtml += '<tr><th>' + escHtml(m[0]) + '</th><td>' + escHtml(m[1]) + '</td></tr>';
  });
  mapHtml += '</table>';
  document.getElementById('diagMapping').innerHTML = mapHtml;
}

// ── Helpers ──
function escHtml(str) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}
</script>
</body>
</html>"""
    return HttpResponse(html, content_type='text/html')
