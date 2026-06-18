HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SearchLab</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, -apple-system, sans-serif; background: #f0f2f5; color: #1a1a1a; line-height: 1.5; }

    /* ── Header ── */
    header { background: #0f1117; color: #fff; padding: .75rem 2rem; display: flex; align-items: center; gap: .75rem; }
    header h1 { font-size: 1.05rem; font-weight: 600; letter-spacing: -.02em; }
    header .badge { font-size: .7rem; color: #888; background: #1e2230; padding: .15rem .5rem; border-radius: 999px; }

    /* ── Tabs ── */
    nav.tabs { background: #fff; border-bottom: 1px solid #e0e0e0; display: flex; gap: 0; padding: 0 2rem; }
    nav.tabs button {
      background: none; border: none; cursor: pointer;
      padding: .75rem 1.25rem; font-size: .85rem; font-weight: 500; color: #666;
      border-bottom: 2px solid transparent; margin-bottom: -1px;
      transition: color .15s, border-color .15s;
    }
    nav.tabs button:hover  { color: #333; }
    nav.tabs button.active { color: #4f7cff; border-bottom-color: #4f7cff; font-weight: 600; }

    /* ── Layout ── */
    .main { max-width: 960px; margin: 1.75rem auto; padding: 0 1rem; }
    .panel.hidden { display: none; }

    /* ── Cards ── */
    .card { background: #fff; border-radius: 10px; padding: 1.5rem; margin-bottom: 1.25rem; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
    .card-title { font-size: .68rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #999; margin-bottom: 1rem; }

    /* ── Forms ── */
    .form-row { display: flex; gap: .75rem; flex-wrap: wrap; align-items: flex-end; }
    .field    { flex: 1 1 220px; }
    .field-sm { flex: 0 0 72px; }
    .field-xs { flex: 0 0 56px; }
    label { display: block; font-size: .72rem; font-weight: 600; color: #666; margin-bottom: .28rem; }
    input[type=text], input[type=number], select {
      width: 100%; border: 1.5px solid #d8dbe0; border-radius: 6px;
      padding: .48rem .7rem; font-size: .875rem; outline: none;
      transition: border-color .15s; background: #fff;
    }
    input:focus, select:focus { border-color: #4f7cff; }

    /* ── Buttons ── */
    .btn { background: #4f7cff; color: #fff; border: none; border-radius: 6px; padding: .52rem 1.1rem; font-size: .875rem; font-weight: 600; cursor: pointer; white-space: nowrap; transition: background .15s; }
    .btn:hover    { background: #3a68f5; }
    .btn:disabled { background: #aaa; cursor: not-allowed; }
    .btn-sm  { padding: .3rem .75rem; font-size: .78rem; }
    .btn-ghost { background: none; border: 1.5px solid #d0d3da; color: #555; }
    .btn-ghost:hover { background: #f5f5f5; }
    .btn-danger { background: #e74c3c; }
    .btn-danger:hover { background: #c0392b; }

    /* ── Alerts / banners ── */
    .alert { padding: .65rem 1rem; border-radius: 6px; font-size: .82rem; margin-bottom: 1rem; }
    .alert-warn  { background: #fffbe6; border-left: 3px solid #f0a500; color: #7a5a00; }
    .alert-error { background: #fff3f3; border-left: 3px solid #e74c3c; color: #c0392b; }
    .alert-ok    { background: #f0fff5; border-left: 3px solid #1a8c5a; color: #145c3a; }

    /* ── Spinner ── */
    .spinner { display: none; align-items: center; gap: .5rem; color: #888; font-size: .82rem; margin-top: .75rem; }
    .spinner.active { display: flex; }
    .dot { width: 5px; height: 5px; border-radius: 50%; background: #aaa; animation: bounce .9s infinite; }
    .dot:nth-child(2) { animation-delay: .2s; }
    .dot:nth-child(3) { animation-delay: .4s; }
    @keyframes bounce { 0%,80%,100%{transform:scale(0)} 40%{transform:scale(1)} }

    /* ── RAG answer ── */
    #answer-card { display: none; }
    .answer-text { white-space: pre-wrap; font-size: .875rem; background: #f8f9fb; border-radius: 6px; padding: 1rem; line-height: 1.7; }
    .sources-title { font-size: .68rem; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: #aaa; margin-top: 1rem; margin-bottom: .4rem; }
    .source-row { display: flex; align-items: baseline; gap: .45rem; font-size: .78rem; padding: .18rem 0; color: #555; }
    .source-rank  { color: #4f7cff; font-weight: 700; min-width: 2rem; }
    .source-score { color: #bbb; margin-left: auto; }

    /* ── Tables ── */
    table { width: 100%; border-collapse: collapse; font-size: .8rem; }
    thead th { text-align: left; padding: .4rem .65rem; background: #f4f5f7; color: #666; font-weight: 600; font-size: .72rem; white-space: nowrap; }
    thead th.sortable { cursor: pointer; user-select: none; }
    thead th.sortable:hover { background: #eaebee; }
    tbody td { padding: .38rem .65rem; border-top: 1px solid #f0f0f0; vertical-align: top; }
    tbody tr:hover td { background: #fafafa; }
    .snippet-cell { max-width: 320px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .metric-hi  { color: #1a8c5a; font-weight: 600; }
    .metric-mid { color: #b07d00; }
    .metric-lo  { color: #bbb; }
    .delta-pos  { color: #1a8c5a; }
    .delta-neg  { color: #e74c3c; }

    /* ── Log output ── */
    .log-box { background: #0f1117; color: #c8d0e0; font-family: 'SF Mono', 'Fira Mono', monospace; font-size: .75rem; border-radius: 6px; padding: .75rem 1rem; min-height: 100px; max-height: 320px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; display: none; margin-top: .75rem; }
    .log-box.active { display: block; }

    /* ── Eval controls ── */
    .op-row { display: flex; gap: .5rem; flex-wrap: wrap; margin-top: .75rem; align-items: flex-end; }
    .run-list-table { margin-top: 0; }

    /* ── Metrics controls ── */
    .metrics-control-row { display: flex; gap: .75rem; flex-wrap: wrap; align-items: flex-end; margin-bottom: 1rem; }
    .aggregate-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(90px, 1fr)); gap: .75rem; margin-bottom: 1.25rem; }
    .agg-cell { background: #f8f9fb; border-radius: 6px; padding: .65rem .75rem; text-align: center; }
    .agg-label { font-size: .65rem; color: #999; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; }
    .agg-value { font-size: 1.3rem; font-weight: 700; margin-top: .15rem; }
    .filter-row { display: flex; gap: .5rem; align-items: center; margin-bottom: .5rem; }
    .filter-row input { flex: 1; }

    /* ── Responsive ── */
    @media (max-width: 600px) {
      nav.tabs { padding: 0 .5rem; overflow-x: auto; }
      nav.tabs button { padding: .65rem .75rem; font-size: .78rem; }
    }
  </style>
</head>
<body>

<header>
  <h1>SearchLab</h1>
  <span class="badge">BM25 + RAG &middot; Python</span>
</header>

<nav class="tabs" id="tab-nav">
  <button class="active" data-tab="rag"     onclick="switchTab('rag')">RAG</button>
  <button                data-tab="query"   onclick="switchTab('query')">Query</button>
  <button                data-tab="ingest"  onclick="switchTab('ingest')">Ingest</button>
  <button                data-tab="eval"    onclick="switchTab('eval')">Eval</button>
  <button                data-tab="metrics" onclick="switchTab('metrics')">Metrics</button>
</nav>

<div class="main">

<!-- ════════════════════════════════════════════ RAG ══ -->
<div id="tab-rag" class="panel">
  <div id="api-key-warn" class="alert alert-warn" style="display:none">
    <strong>OPENAI_API_KEY not set.</strong> Start the server with the variable set to use the RAG and Ask features.
  </div>
  <div class="card">
    <div class="card-title">Ask a Question</div>
    <div class="form-row">
      <div class="field-sm" style="flex:0 0 130px">
        <label for="rag-dataset">Dataset</label>
        <select id="rag-dataset">
          <option value="default">Default index</option>
          <option value="nfcorpus">nfcorpus</option>
          <option value="fiqa">FiQA-2018</option>
        </select>
      </div>
      <div class="field">
        <label for="rag-question">Question</label>
        <input type="text" id="rag-question" placeholder="e.g. what is dollar cost averaging" />
      </div>
      <div class="field-xs">
        <label for="rag-topk">Top-K</label>
        <input type="number" id="rag-topk" value="5" min="1" max="20" />
      </div>
      <div class="field">
        <label for="rag-model">Model</label>
        <input type="text" id="rag-model" value="gpt-4o-mini" />
      </div>
      <button class="btn" id="rag-btn" onclick="askRag()">Ask</button>
    </div>
    <div class="spinner" id="rag-spinner"><div class="dot"></div><div class="dot"></div><div class="dot"></div> Running RAG pipeline&hellip;</div>
  </div>
  <div class="card" id="answer-card">
    <div class="card-title">Answer</div>
    <div id="answer-content"></div>
  </div>
</div>

<!-- ════════════════════════════════════════════ QUERY ══ -->
<div id="tab-query" class="panel hidden">
  <div class="card">
    <div class="card-title">BM25 Search</div>
    <div class="form-row">
      <div class="field-sm" style="flex:0 0 130px">
        <label for="q-dataset">Dataset</label>
        <select id="q-dataset">
          <option value="nfcorpus">nfcorpus</option>
          <option value="fiqa">FiQA-2018</option>
        </select>
      </div>
      <div class="field">
        <label for="q-text">Query</label>
        <input type="text" id="q-text" placeholder="e.g. vitamin D deficiency" />
      </div>
      <div class="field-xs">
        <label for="q-topk">Top-K</label>
        <input type="number" id="q-topk" value="5" min="1" max="50" />
      </div>
      <button class="btn" id="q-btn" onclick="runQuery()">Search</button>
    </div>
    <div class="spinner" id="q-spinner"><div class="dot"></div><div class="dot"></div><div class="dot"></div> Searching&hellip;</div>
  </div>
  <div class="card" id="q-results-card" style="display:none">
    <div class="card-title" id="q-results-title">Results</div>
    <div id="q-status"></div>
    <div id="q-table-wrap"></div>
  </div>
</div>

<!-- ════════════════════════════════════════════ INGEST ══ -->
<div id="tab-ingest" class="panel hidden">
  <div class="card">
    <div class="card-title">Ingest PDF</div>
    <p style="font-size:.82rem;color:#666;margin-bottom:1rem">
      Indexes a PDF into the default OpenSearch index (<code>searchlab-v0</code> or <code>$SEARCHLAB_INDEX</code>).
      Enter the path relative to the project root or an absolute path.
    </p>
    <div class="form-row">
      <div class="field">
        <label for="ingest-path">PDF Path</label>
        <input type="text" id="ingest-path" placeholder="test-corpus/sample.pdf" />
      </div>
      <button class="btn" id="ingest-btn" onclick="runIngest()">Ingest</button>
    </div>
    <div class="spinner" id="ingest-spinner"><div class="dot"></div><div class="dot"></div><div class="dot"></div> Ingesting&hellip;</div>
    <div id="ingest-status" style="margin-top:.75rem"></div>
  </div>
</div>

<!-- ════════════════════════════════════════════ EVAL ══ -->
<div id="tab-eval" class="panel hidden">
  <div class="card">
    <div class="card-title">Eval Controls</div>
    <div class="form-row">
      <div class="field-sm" style="flex:0 0 130px">
        <label for="eval-dataset">Dataset</label>
        <select id="eval-dataset">
          <option value="nfcorpus">nfcorpus</option>
          <option value="fiqa">FiQA-2018</option>
        </select>
      </div>
      <div class="field-xs">
        <label for="eval-slice">Slice</label>
        <input type="number" id="eval-slice" value="100" min="1" placeholder="all" title="Limit queries for Download (optional)" />
      </div>
    </div>
    <div class="op-row">
      <button class="btn eval-op-btn" onclick="runEvalOp('download')">Download</button>
      <button class="btn eval-op-btn" onclick="runEvalOp('ingest')">Ingest</button>
      <button class="btn eval-op-btn" onclick="runEvalOp('query')">Query</button>
      <span style="flex:1"></span>
      <div class="field" style="flex:0 0 210px">
        <label for="eval-run-id">Run ID (for Metrics)</label>
        <input type="text" id="eval-run-id" placeholder="e.g. bm25_phase0" />
      </div>
      <button class="btn eval-op-btn" onclick="runEvalOp('metrics')">Compute Metrics</button>
      <button class="btn eval-op-btn" onclick="runEvalOp('ragas')">RAG Eval</button>
    </div>
    <div class="log-box" id="eval-log"></div>
  </div>
  <div class="card">
    <div class="card-title" style="display:flex;justify-content:space-between;align-items:center">
      Available Runs
      <button class="btn btn-sm btn-ghost" onclick="loadEvalRuns()">Refresh</button>
    </div>
    <div id="eval-runs-content">Loading&hellip;</div>
  </div>
</div>

<!-- ════════════════════════════════════════════ METRICS ══ -->
<div id="tab-metrics" class="panel hidden">
  <div class="card">
    <div class="card-title">Metrics Explorer</div>
    <div class="metrics-control-row">
      <div class="field-sm" style="flex:0 0 130px">
        <label for="m-dataset">Dataset</label>
        <select id="m-dataset" onchange="refreshRunDropdown('m-run', 'm-dataset')">
          <option value="">All</option>
          <option value="nfcorpus">nfcorpus</option>
          <option value="fiqa">FiQA-2018</option>
        </select>
      </div>
      <div class="field">
        <label for="m-run">Run</label>
        <select id="m-run"><option value="">&mdash; select &mdash;</option></select>
      </div>
      <button class="btn" onclick="loadMetrics()">Load</button>
    </div>
    <div class="metrics-control-row" style="margin-bottom:0">
      <div class="field-sm" style="flex:0 0 130px">
        <label>Compare with</label>
        <select id="m-dataset2" onchange="refreshRunDropdown('m-run2', 'm-dataset2')">
          <option value="">All</option>
          <option value="nfcorpus">nfcorpus</option>
          <option value="fiqa">FiQA-2018</option>
        </select>
      </div>
      <div class="field">
        <label for="m-run2">Run</label>
        <select id="m-run2"><option value="">&mdash; none &mdash;</option></select>
      </div>
      <button class="btn btn-ghost" onclick="loadCompare()">Compare</button>
    </div>
  </div>

  <div id="metrics-content" style="display:none">
    <div class="card">
      <div class="card-title" id="metrics-run-label">Aggregate Metrics</div>
      <div class="aggregate-grid" id="agg-grid"></div>
      <div class="filter-row">
        <input type="text" id="pq-filter" placeholder="Filter by query ID&hellip;" oninput="filterPerQuery()" />
        <span id="pq-count" style="font-size:.75rem;color:#aaa;white-space:nowrap"></span>
      </div>
      <table id="pq-table">
        <thead id="pq-thead"></thead>
        <tbody id="pq-tbody"></tbody>
      </table>
    </div>
  </div>

  <div id="rag-metrics-content" style="display:none">
    <div class="card">
      <div class="card-title" id="rag-metrics-run-label">RAG Quality Metrics</div>
      <div class="aggregate-grid" id="rag-agg-grid"></div>
      <table id="rag-pq-table">
        <thead id="rag-pq-thead"></thead>
        <tbody id="rag-pq-tbody"></tbody>
      </table>
    </div>
  </div>
</div>

</div><!-- .main -->

<script>
// ── State ────────────────────────────────────────────────────────────
const OPENAI_KEY_SET = __OPENAI_KEY_SET__;
let evalRunning = false;
let evalSource  = null;
let allRuns     = [];
let pqRows      = [];
let pqSortCol   = 'ndcg_cut_10';
let pqSortAsc   = false;

const METRICS_KEYS = [
  { key: 'ndcg_cut_10', label: 'nDCG@10' },
  { key: 'ndcg_cut_5',  label: 'nDCG@5'  },
  { key: 'ndcg_cut_3',  label: 'nDCG@3'  },
  { key: 'ndcg_cut_1',  label: 'nDCG@1'  },
  { key: 'recall_10',   label: 'Recall@10'},
  { key: 'recall_5',    label: 'Recall@5' },
  { key: 'map_cut_10',  label: 'MAP@10'   },
];

const RAG_METRICS_KEYS = [
  { key: 'faithfulness',      label: 'Faithfulness'      },
  { key: 'answer_relevancy',  label: 'Answer Relevancy'  },
  { key: 'context_recall',    label: 'Context Recall'    },
  { key: 'context_precision', label: 'Context Precision' },
];

// ── Tab switching ────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
  document.querySelectorAll('#tab-nav button').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.remove('hidden');
  document.querySelector('[data-tab="' + name + '"]').classList.add('active');
  window.location.hash = '#' + name;
}

// ── Init ─────────────────────────────────────────────────────────────
(function init() {
  if (!OPENAI_KEY_SET) document.getElementById('api-key-warn').style.display = 'block';
  const hash = window.location.hash.replace('#', '') || 'rag';
  switchTab(hash);
  loadEvalRuns();
  document.getElementById('rag-question').addEventListener('keydown', e => { if (e.key === 'Enter') askRag(); });
  document.getElementById('q-text').addEventListener('keydown', e => { if (e.key === 'Enter') runQuery(); });
})();

// ── Helpers ──────────────────────────────────────────────────────────
function enc(s)    { return encodeURIComponent(s); }
function esc(s)    { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function fmt(v)    { return (v == null ? '-' : v.toFixed(3)); }
function metricCls(v) { return v >= 0.3 ? 'metric-hi' : v >= 0.15 ? 'metric-mid' : 'metric-lo'; }

// ── RAG ──────────────────────────────────────────────────────────────
async function askRag() {
  const question = document.getElementById('rag-question').value.trim();
  if (!question) { alert('Please enter a question.'); return; }
  const topK    = document.getElementById('rag-topk').value;
  const model   = document.getElementById('rag-model').value.trim();
  const dataset = document.getElementById('rag-dataset').value;
  const btn     = document.getElementById('rag-btn');
  btn.disabled  = true;
  document.getElementById('rag-spinner').classList.add('active');
  document.getElementById('answer-card').style.display = 'none';
  try {
    const r = await fetch('/rag', {
      method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `question=${enc(question)}&topK=${topK}&model=${enc(model)}&dataset=${enc(dataset)}`
    });
    renderAnswer(await r.json());
  } catch (e) { renderAnswer({ error: 'Network error: ' + e.message }); }
  finally {
    btn.disabled = false;
    document.getElementById('rag-spinner').classList.remove('active');
  }
}

function renderAnswer(data) {
  const card = document.getElementById('answer-card');
  const el   = document.getElementById('answer-content');
  card.style.display = 'block';
  if (data.error) {
    el.innerHTML = `<div class="alert alert-error">${esc(data.error)}</div>`;
    return;
  }
  const indexLabel = data.index ? `<span style="font-size:.7rem;color:#aaa;font-weight:400"> &middot; index: ${esc(data.index)}</span>` : '';
  document.querySelector('#answer-card .card-title').innerHTML = 'Answer' + indexLabel;
  let html = `<div class="answer-text">${esc(data.answer)}</div>`;
  if (data.sources && data.sources.length) {
    html += '<div class="sources-title">Sources</div>';
    data.sources.forEach(s => {
      html += `<div class="source-row">
        <span class="source-rank">[${s.rank}]</span>
        <span>${esc(s.filename)}</span>
        <span style="color:#ddd">&middot;</span>
        <span>p.${s.page}</span>
        <span class="source-score">score ${s.score.toFixed(3)}</span>
      </div>`;
    });
  }
  el.innerHTML = html;
}

// ── BM25 Query ───────────────────────────────────────────────────────
async function runQuery() {
  const q       = document.getElementById('q-text').value.trim();
  const topK    = document.getElementById('q-topk').value;
  const dataset = document.getElementById('q-dataset').value;
  if (!q) { alert('Please enter a query.'); return; }
  const btn = document.getElementById('q-btn');
  btn.disabled = true;
  document.getElementById('q-spinner').classList.add('active');
  document.getElementById('q-results-card').style.display = 'none';
  try {
    const r = await fetch('/api/query', {
      method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `query=${enc(q)}&topK=${topK}&dataset=${enc(dataset)}`
    });
    renderQueryResults(await r.json(), dataset);
  } catch(e) { renderQueryResults({ error: e.message }, dataset); }
  finally { btn.disabled = false; document.getElementById('q-spinner').classList.remove('active'); }
}

function renderQueryResults(data, dataset) {
  const card = document.getElementById('q-results-card');
  card.style.display = 'block';
  const statusEl = document.getElementById('q-status');
  const tableEl  = document.getElementById('q-table-wrap');
  if (data.error) {
    statusEl.innerHTML = `<div class="alert alert-error">${esc(data.error)}</div>`;
    tableEl.innerHTML = '';
    return;
  }
  statusEl.innerHTML = '';
  document.getElementById('q-results-title').textContent =
    `Results &mdash; ${data.hits.length} hit${data.hits.length !== 1 ? 's' : ''} &middot; index: ${data.index}`;
  if (!data.hits.length) {
    tableEl.innerHTML = '<p style="font-size:.82rem;color:#aaa;padding:.5rem 0">No results found.</p>';
    return;
  }
  tableEl.innerHTML = `<table>
    <thead><tr>
      <th style="width:3rem">Rank</th>
      <th style="width:5rem">Score</th>
      <th>Source</th>
      <th style="width:3.5rem">Page</th>
      <th>Snippet</th>
    </tr></thead>
    <tbody>
      ${data.hits.map(h => `<tr>
        <td>${h.rank}</td>
        <td>${h.score.toFixed(4)}</td>
        <td>${esc(h.filename)}</td>
        <td>${h.page}</td>
        <td class="snippet-cell" title="${esc(h.snippet)}">${esc(h.snippet)}</td>
      </tr>`).join('')}
    </tbody>
  </table>`;
}

// ── Ingest ───────────────────────────────────────────────────────────
async function runIngest() {
  const path = document.getElementById('ingest-path').value.trim();
  if (!path) { alert('Please enter a PDF path.'); return; }
  const btn = document.getElementById('ingest-btn');
  btn.disabled = true;
  document.getElementById('ingest-spinner').classList.add('active');
  document.getElementById('ingest-status').innerHTML = '';
  try {
    const r = await fetch('/api/ingest', {
      method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `pdfPath=${enc(path)}`
    });
    const data = await r.json();
    const statusEl = document.getElementById('ingest-status');
    if (data.error) {
      statusEl.innerHTML = `<div class="alert alert-error">${esc(data.error)}</div>`;
    } else {
      statusEl.innerHTML = `<div class="alert alert-ok">
        Indexed <strong>${data.chunksIndexed}</strong> chunks from
        <strong>${esc(data.filename)}</strong> into index <code>${esc(data.index)}</code>.
      </div>`;
    }
  } catch(e) {
    document.getElementById('ingest-status').innerHTML =
      `<div class="alert alert-error">Network error: ${esc(e.message)}</div>`;
  } finally {
    btn.disabled = false;
    document.getElementById('ingest-spinner').classList.remove('active');
  }
}

// ── Eval ─────────────────────────────────────────────────────────────
function setEvalBtns(disabled) {
  evalRunning = disabled;
  document.querySelectorAll('.eval-op-btn').forEach(b => b.disabled = disabled);
}

function runEvalOp(op) {
  if (evalRunning) return;
  const dataset = document.getElementById('eval-dataset').value;
  const slice   = document.getElementById('eval-slice').value.trim();
  const runId   = document.getElementById('eval-run-id').value.trim();

  const log = document.getElementById('eval-log');
  log.textContent = '';
  log.classList.add('active');

  let url = `/api/eval/stream?op=${enc(op)}&dataset=${enc(dataset)}`;
  if (op === 'download' && slice) url += `&slice=${enc(slice)}`;
  if (op === 'ragas'    && slice) url += `&slice=${enc(slice)}`;
  if (op === 'metrics')           url += `&runId=${enc(runId)}`;

  if (evalSource) evalSource.close();
  setEvalBtns(true);

  evalSource = new EventSource(url);

  evalSource.onmessage = e => {
    log.textContent += e.data + '\\n';
    log.scrollTop = log.scrollHeight;
  };

  evalSource.addEventListener('done', () => {
    log.textContent += '\\n\\u2713 Done\\n';
    evalSource.close();
    evalSource = null;
    setEvalBtns(false);
    if (op === 'query') autoDetectLatestRun(dataset);
    loadEvalRuns();
  });

  evalSource.addEventListener('error', e => {
    const msg = e.data || 'Stream error';
    log.textContent += '\\n\\u2717 ' + msg + '\\n';
    evalSource.close();
    evalSource = null;
    setEvalBtns(false);
  });

  evalSource.onerror = () => {
    if (evalSource.readyState === 2) {
      log.textContent += '\\n\\u2717 Connection lost.\\n';
      setEvalBtns(false);
      evalSource = null;
    }
  };
}

async function autoDetectLatestRun(dataset) {
  await loadEvalRuns();
  const rawOnly = allRuns.filter(r => r.hasRaw && !r.hasMetrics && (r.dataset === dataset || !r.dataset));
  if (rawOnly.length) {
    document.getElementById('eval-run-id').value = rawOnly[0].runId;
  }
}

async function loadEvalRuns() {
  try {
    const r = await fetch('/api/eval/runs');
    allRuns = await r.json();
    renderEvalRuns(allRuns);
    refreshRunDropdown('m-run',  'm-dataset');
    refreshRunDropdown('m-run2', 'm-dataset2');
  } catch(e) {
    document.getElementById('eval-runs-content').innerHTML =
      `<div class="alert alert-error">Could not load runs: ${esc(e.message)}</div>`;
  }
}

function renderEvalRuns(runs) {
  const el = document.getElementById('eval-runs-content');
  if (!runs.length) {
    el.innerHTML = '<p style="font-size:.82rem;color:#aaa">No eval runs found in searchlab-eval/results/</p>';
    return;
  }
  el.innerHTML = `<table class="run-list-table">
    <thead><tr><th>Run ID</th><th>Dataset</th><th>Computed At</th><th>Has Metrics</th><th>Has RAG</th><th></th></tr></thead>
    <tbody>
      ${runs.map(r => `<tr>
        <td><code>${esc(r.runId)}</code></td>
        <td>${esc(r.dataset || '&mdash;')}</td>
        <td style="font-size:.72rem;color:#888">${esc(r.computedAt ? r.computedAt.slice(0,19).replace('T',' ') : '&mdash;')}</td>
        <td>${r.hasMetrics ? '&#10003;' : '<span style="color:#ccc">&mdash;</span>'}</td>
        <td>${r.hasRagMetrics ? '&#10003;' : '<span style="color:#ccc">&mdash;</span>'}</td>
        <td>
          ${r.hasMetrics
            ? `<button class="btn btn-sm btn-ghost" onclick="viewRunMetrics('${esc(r.runId)}')">View</button>`
            : (r.hasRaw
              ? `<button class="btn btn-sm btn-ghost" onclick="prefillMetricsRun('${esc(r.runId)}')">Compute</button>`
              : '')}
        </td>
      </tr>`).join('')}
    </tbody>
  </table>`;
}

function prefillMetricsRun(runId) {
  document.getElementById('eval-run-id').value = runId;
}

function viewRunMetrics(runId) {
  switchTab('metrics');
  const run = allRuns.find(r => r.runId === runId);
  if (run && run.dataset) {
    document.getElementById('m-dataset').value = run.dataset === 'nfcorpus' ? 'nfcorpus' : 'fiqa';
    refreshRunDropdown('m-run', 'm-dataset');
  }
  document.getElementById('m-run').value = runId;
  loadMetrics();
}

// ── Metrics ──────────────────────────────────────────────────────────
function refreshRunDropdown(dropId, datasetDropId) {
  const datasetFilter = document.getElementById(datasetDropId).value;
  const drop = document.getElementById(dropId);
  const prev = drop.value;
  drop.innerHTML = '<option value="">&mdash; select &mdash;</option>';
  allRuns.filter(r => r.hasMetrics && (!datasetFilter || r.dataset === datasetFilter))
         .forEach(r => {
           const opt = document.createElement('option');
           opt.value = r.runId;
           opt.textContent = r.runId + (r.computedAt ? '  (' + r.computedAt.slice(0,10) + ')' : '');
           drop.appendChild(opt);
         });
  if (prev) drop.value = prev;
}

async function loadMetrics() {
  const runId = document.getElementById('m-run').value;
  if (!runId) { alert('Please select a run.'); return; }
  try {
    const r = await fetch(`/api/eval/results?runId=${enc(runId)}`);
    const data = await r.json();
    if (data.error) { alert(data.error); return; }
    renderMetrics(data, null);
    const run = allRuns.find(r => r.runId === runId);
    if (run && run.hasRagMetrics) loadRagMetrics(runId);
    else document.getElementById('rag-metrics-content').style.display = 'none';
  } catch(e) { alert('Error loading metrics: ' + e.message); }
}

async function loadCompare() {
  const runId1 = document.getElementById('m-run').value;
  const runId2 = document.getElementById('m-run2').value;
  if (!runId1) { alert('Please select a primary run.'); return; }
  if (!runId2 || runId2 === runId1) { loadMetrics(); return; }
  try {
    const [r1, r2] = await Promise.all([
      fetch(`/api/eval/results?runId=${enc(runId1)}`).then(r => r.json()),
      fetch(`/api/eval/results?runId=${enc(runId2)}`).then(r => r.json()),
    ]);
    if (r1.error || r2.error) { alert(r1.error || r2.error); return; }
    renderMetrics(r1, r2);
  } catch(e) { alert('Error: ' + e.message); }
}

function renderMetrics(data1, data2) {
  document.getElementById('metrics-content').style.display = 'block';
  const run2Id = data2 ? document.getElementById('m-run2').value : null;
  document.getElementById('metrics-run-label').textContent =
    data1.run_id + (run2Id ? ' vs ' + run2Id : '') +
    ' — ' + (data1.dataset || '') +
    (data1.computed_at ? ' · ' + data1.computed_at.slice(0,10) : '');

  renderAggregate(data1.aggregate || {}, data2 ? data2.aggregate || {} : null);
  buildPerQueryData(data1.per_query || {}, data2 ? data2.per_query || {} : null);
  renderPerQuery();
}

function renderAggregate(agg1, agg2) {
  const grid = document.getElementById('agg-grid');
  grid.innerHTML = METRICS_KEYS.map(m => {
    const v1 = agg1[m.key] ?? 0;
    const v2 = agg2 ? (agg2[m.key] ?? 0) : null;
    const delta = v2 != null ? v2 - v1 : null;
    const deltaStr = delta != null
      ? `<div style="font-size:.7rem;margin-top:.1rem" class="${delta >= 0 ? 'delta-pos' : 'delta-neg'}">${delta >= 0 ? '+' : ''}${delta.toFixed(3)}</div>`
      : '';
    return `<div class="agg-cell">
      <div class="agg-label">${m.label}</div>
      <div class="agg-value ${metricCls(v1)}">${v1.toFixed(3)}</div>
      ${v2 != null ? `<div style="font-size:.8rem;color:#888">${v2.toFixed(3)}</div>` : ''}
      ${deltaStr}
    </div>`;
  }).join('');
}

function buildPerQueryData(pq1, pq2) {
  const keys = Object.keys(pq1);
  pqRows = keys.map(qid => {
    const r1 = pq1[qid] || {};
    const r2 = pq2 ? (pq2[qid] || {}) : null;
    return { qid, r1, r2 };
  });
}

function sortPQ(col) {
  if (pqSortCol === col) pqSortAsc = !pqSortAsc;
  else { pqSortCol = col; pqSortAsc = false; }
  renderPerQuery();
}

function filterPerQuery() { renderPerQuery(); }

function renderPerQuery() {
  const filter = (document.getElementById('pq-filter').value || '').toLowerCase();
  const visible = pqRows.filter(r => !filter || r.qid.toLowerCase().includes(filter));
  const sorted  = [...visible].sort((a, b) => {
    const va = a.r1[pqSortCol] ?? 0;
    const vb = b.r1[pqSortCol] ?? 0;
    return pqSortAsc ? va - vb : vb - va;
  });

  const hasCompare = pqRows.length && pqRows[0].r2 != null;
  document.getElementById('pq-count').textContent = `${visible.length} / ${pqRows.length} queries`;

  const thSort = key => {
    const arrow = pqSortCol === key ? (pqSortAsc ? ' ▲' : ' ▼') : '';
    return `<th class="sortable" onclick="sortPQ('${key}')">${METRICS_KEYS.find(m=>m.key===key)?.label || key}${arrow}</th>`;
  };

  document.getElementById('pq-thead').innerHTML = `<tr>
    <th>Query ID</th>
    ${METRICS_KEYS.map(m => thSort(m.key)).join('')}
    ${hasCompare ? '<th colspan="' + METRICS_KEYS.length + '" style="background:#f0f8ff;color:#4f7cff">Δ (run2 − run1)</th>' : ''}
  </tr>`;

  document.getElementById('pq-tbody').innerHTML = sorted.map(({qid, r1, r2}) => {
    const cells1 = METRICS_KEYS.map(m => {
      const v = r1[m.key] ?? 0;
      return `<td class="${metricCls(v)}">${v.toFixed(3)}</td>`;
    }).join('');
    const cells2 = hasCompare ? METRICS_KEYS.map(m => {
      const d = (r2[m.key] ?? 0) - (r1[m.key] ?? 0);
      return `<td class="${d > 0.001 ? 'delta-pos' : d < -0.001 ? 'delta-neg' : 'metric-lo'}" style="background:#f8fbff">${d >= 0 ? '+' : ''}${d.toFixed(3)}</td>`;
    }).join('') : '';
    return `<tr><td><code>${esc(qid)}</code></td>${cells1}${cells2}</tr>`;
  }).join('');
}

// ── RAG Metrics ──────────────────────────────────────────────────────
async function loadRagMetrics(runId) {
  try {
    const r = await fetch(`/api/eval/rag-results?runId=${enc(runId)}`);
    const data = await r.json();
    if (data.error) return;
    renderRagMetrics(data);
  } catch(e) { /* silently skip if no rag scores */ }
}

function renderRagMetrics(data) {
  document.getElementById('rag-metrics-content').style.display = 'block';
  document.getElementById('rag-metrics-run-label').textContent =
    'RAG Quality — ' + (data.run_id || '') +
    (data.computed_at ? ' · ' + data.computed_at.slice(0,10) : '');

  const agg = data.aggregate || {};
  document.getElementById('rag-agg-grid').innerHTML = RAG_METRICS_KEYS.map(m => {
    const v = agg[m.key];
    if (v == null) return '';
    return `<div class="agg-cell">
      <div class="agg-label">${m.label}</div>
      <div class="agg-value ${metricCls(v)}">${v.toFixed(3)}</div>
    </div>`;
  }).join('');

  const pq = data.per_query || {};
  const measures = data.measures || [];
  const rows = Object.entries(pq);

  document.getElementById('rag-pq-thead').innerHTML = `<tr>
    <th>Query ID</th>
    ${RAG_METRICS_KEYS.filter(m => measures.includes(m.key)).map(m => `<th>${m.label}</th>`).join('')}
  </tr>`;

  document.getElementById('rag-pq-tbody').innerHTML = rows.map(([qid, scores]) => {
    const cells = RAG_METRICS_KEYS
      .filter(m => measures.includes(m.key))
      .map(m => {
        const v = scores[m.key] ?? null;
        return v != null
          ? `<td class="${metricCls(v)}">${v.toFixed(3)}</td>`
          : '<td class="metric-lo">-</td>';
      }).join('');
    return `<tr><td><code>${esc(qid)}</code></td>${cells}</tr>`;
  }).join('');
}
</script>
</body>
</html>"""


def render(openai_key_set: bool) -> str:
    return HTML_TEMPLATE.replace("__OPENAI_KEY_SET__", str(openai_key_set).lower())
