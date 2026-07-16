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

    /* ── Compare tab ── */
    th.group-th { text-align: center; border-left: 1px solid #e6e6e6; }
    tbody tr.cmp-row { cursor: pointer; }
    tr.cmp-expand-row td { background: #f8f9fb; padding: 1rem 1.25rem; border-top: none; }
    .cmp-content-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
    .cmp-content-col h4 { font-size: .68rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: #999; margin-bottom: .35rem; }
    .cmp-question { font-size: .85rem; margin-bottom: .9rem; padding: .5rem .75rem; background: #eef2ff; border-radius: 6px; }
    .only-section-title { font-size: .75rem; font-weight: 700; color: #888; margin: .25rem 0 .4rem; }
    .cmp-judgement-link { color: #4f7cff; text-decoration: none; }
    .cmp-judgement-link:hover { text-decoration: underline; }
    tr.cmp-judgement-row td { background: #f5f7ff; padding: .75rem 1.25rem; border-top: none; }
    .cmp-judgement-panel h4 { font-size: .68rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: #999; margin-bottom: .35rem; }
    @media (max-width: 700px) { .cmp-content-grid { grid-template-columns: 1fr; } }

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
  <button                data-tab="compare" onclick="switchTab('compare')">Compare</button>
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

<!-- ════════════════════════════════════════════ COMPARE ══ -->
<div id="tab-compare" class="panel hidden">
  <div class="card">
    <div class="card-title">Compare Runs</div>
    <div class="metrics-control-row">
      <div class="field-sm" style="flex:0 0 90px">
        <label for="cmp-type">Type</label>
        <select id="cmp-type" onchange="onCompareTypeChange()">
          <option value="ir">IR</option>
          <option value="rag">RAG</option>
        </select>
      </div>
      <div class="field-sm" style="flex:0 0 130px">
        <label for="cmp-dataset">Dataset</label>
        <select id="cmp-dataset" onchange="refreshCompareRunDropdowns()">
          <option value="">&mdash; select &mdash;</option>
        </select>
      </div>
      <div class="field">
        <label for="cmp-run-a">Run A</label>
        <select id="cmp-run-a"><option value="">&mdash; select &mdash;</option></select>
      </div>
      <div class="field">
        <label for="cmp-run-b">Run B</label>
        <select id="cmp-run-b"><option value="">&mdash; select &mdash;</option></select>
      </div>
      <button class="btn" onclick="runCompare()">Compare</button>
      <div class="field-sm" style="flex:0 0 150px">
        <label for="cmp-metric-filter">Metric</label>
        <select id="cmp-metric-filter" onchange="onCompareMetricFilterChange()" disabled>
          <option value="">All metrics</option>
        </select>
      </div>
      <div class="field-sm" style="flex:0 0 160px">
        <label for="cmp-row-filter">Rows</label>
        <select id="cmp-row-filter" onchange="onCompareRowFilterChange()" disabled>
          <option value="all">All</option>
          <option value="improved">Improved in B</option>
          <option value="regressed">Regressed in B</option>
        </select>
      </div>
    </div>
    <div id="cmp-status" style="margin-top:.5rem"></div>
  </div>

  <div id="cmp-content" style="display:none">
    <div class="card" id="cmp-agg-card">
      <div class="card-title">Aggregate</div>
      <table id="cmp-agg-table">
        <thead><tr><th>Measure</th><th>A</th><th>B</th><th>Δ</th></tr></thead>
        <tbody id="cmp-agg-tbody"></tbody>
      </table>
    </div>
    <div class="card">
      <div class="card-title" id="cmp-title">Comparison</div>
      <table id="cmp-table">
        <thead id="cmp-thead"></thead>
        <tbody id="cmp-tbody"></tbody>
      </table>
    </div>
    <div class="card" id="cmp-only-card" style="display:none">
      <div class="card-title">Coverage Mismatch</div>
      <div id="cmp-only-content"></div>
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

const ALL_METRIC_LABELS = {};
METRICS_KEYS.forEach(m => ALL_METRIC_LABELS[m.key] = m.label);
RAG_METRICS_KEYS.forEach(m => ALL_METRIC_LABELS[m.key] = m.label);
function metricLabel(key) { return ALL_METRIC_LABELS[key] || key; }

const PRIMARY_MEASURE = { ir: 'ndcg_cut_10', rag: 'faithfulness' };

let cmpData         = null;
let cmpType         = 'ir';
let cmpSortKey      = { measure: 'ndcg_cut_10', part: 'delta' };
let cmpSortAsc      = true;
let cmpExpandedKey  = null;
let cmpMetricFilter = '';
let cmpRowFilter    = 'all';
let cmpExpandedDocs = new Set();
const cmpDocCache   = new Map();
const cmpHighlightCache = new Map();
let cmpOpenJudgements = new Set();
const cmpJudgementCache = new Map();

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
    refreshCompareDatasetDropdown();
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

// ── Compare ──────────────────────────────────────────────────────────
function onCompareTypeChange() {
  cmpType = document.getElementById('cmp-type').value;
  cmpSortKey = { measure: PRIMARY_MEASURE[cmpType], part: 'delta' };
  cmpSortAsc = true;
  cmpData = null;
  cmpExpandedDocs = new Set();
  cmpOpenJudgements = new Set();
  document.getElementById('cmp-content').style.display = 'none';
  document.getElementById('cmp-status').innerHTML = '';
  resetCompareMetricFilter();
  resetCompareRowFilter();
  refreshCompareDatasetDropdown();
}

function resetCompareMetricFilter() {
  cmpMetricFilter = '';
  const sel = document.getElementById('cmp-metric-filter');
  sel.innerHTML = '<option value="">All metrics</option>';
  sel.value = '';
  sel.disabled = true;
}

function onCompareMetricFilterChange() {
  cmpMetricFilter = document.getElementById('cmp-metric-filter').value;
  renderCompareTable(cmpData);
  renderCompareOnly(cmpData);
}

function resetCompareRowFilter() {
  cmpRowFilter = 'all';
  const sel = document.getElementById('cmp-row-filter');
  sel.value = 'all';
  sel.disabled = true;
}

function onCompareRowFilterChange() {
  cmpRowFilter = document.getElementById('cmp-row-filter').value;
  renderCompareTable(cmpData);
}

// The metric whose delta drives the improved/regressed filter: the metric-column dropdown's
// current selection, or the type's primary measure when that dropdown is on "All metrics".
function activeFilterMetric() {
  return cmpMetricFilter || PRIMARY_MEASURE[cmpType];
}

function refreshCompareDatasetDropdown() {
  const flagKey = cmpType === 'ir' ? 'hasMetrics' : 'hasRagMetrics';
  const datasets = [...new Set(allRuns.filter(r => r[flagKey] && r.dataset).map(r => r.dataset))].sort();
  const sel = document.getElementById('cmp-dataset');
  const prev = sel.value;
  sel.innerHTML = '<option value="">&mdash; select &mdash;</option>' +
    datasets.map(d => `<option value="${esc(d)}">${esc(d)}</option>`).join('');
  if (datasets.includes(prev)) sel.value = prev;
  refreshCompareRunDropdowns();
}

function refreshCompareRunDropdowns() {
  const flagKey = cmpType === 'ir' ? 'hasMetrics' : 'hasRagMetrics';
  const dataset = document.getElementById('cmp-dataset').value;
  const candidates = allRuns
    .filter(r => r[flagKey] && (!dataset || r.dataset === dataset))
    .sort((a, b) => (b.computedAt || '').localeCompare(a.computedAt || ''));
  ['cmp-run-a', 'cmp-run-b'].forEach(id => {
    const sel = document.getElementById(id);
    const prev = sel.value;
    sel.innerHTML = '<option value="">&mdash; select &mdash;</option>' +
      candidates.map(r => `<option value="${esc(r.runId)}">${esc(r.runId)}${r.computedAt ? '  (' + esc(r.computedAt.slice(0,10)) + ')' : ''}</option>`).join('');
    if (candidates.some(r => r.runId === prev)) sel.value = prev;
  });
}

async function runCompare() {
  const type = cmpType;
  const runA = document.getElementById('cmp-run-a').value;
  const runB = document.getElementById('cmp-run-b').value;
  const statusEl = document.getElementById('cmp-status');
  statusEl.innerHTML = '';
  if (!runA || !runB) { statusEl.innerHTML = '<div class="alert alert-error">Please select both Run A and Run B.</div>'; return; }
  if (runA === runB) { statusEl.innerHTML = '<div class="alert alert-error">Run A and Run B must be different.</div>'; return; }
  document.getElementById('cmp-content').style.display = 'none';
  try {
    const r = await fetch(`/api/eval/compare?type=${enc(type)}&runA=${enc(runA)}&runB=${enc(runB)}`);
    const data = await r.json();
    if (data.error) { statusEl.innerHTML = `<div class="alert alert-error">${esc(data.error)}</div>`; return; }
    cmpData = data;
    cmpSortKey = { measure: PRIMARY_MEASURE[type], part: 'delta' };
    cmpSortAsc = true;
    cmpExpandedKey = null;
    cmpExpandedDocs = new Set();
    cmpOpenJudgements = new Set();
    cmpMetricFilter = '';
    const filterSel = document.getElementById('cmp-metric-filter');
    filterSel.innerHTML = '<option value="">All metrics</option>' +
      data.measures.map(m => `<option value="${esc(m)}">${esc(metricLabel(m))}</option>`).join('');
    filterSel.value = '';
    filterSel.disabled = false;
    cmpRowFilter = 'all';
    const rowFilterSel = document.getElementById('cmp-row-filter');
    rowFilterSel.value = 'all';
    rowFilterSel.disabled = false;
    renderCompare();
  } catch(e) {
    statusEl.innerHTML = `<div class="alert alert-error">Network error: ${esc(e.message)}</div>`;
  }
}

function renderCompare() {
  const data = cmpData;
  document.getElementById('cmp-content').style.display = 'block';
  document.getElementById('cmp-title').textContent = `${data.run_a} vs ${data.run_b} — ${data.dataset}`;
  renderCompareAggregate(data);
  renderCompareTable(data);
  renderCompareOnly(data);
}

// Always shows all shared measures, independent of the per-query metric-column filter
// (F11) — that filter narrows the per-query table, not this summary block.
function renderCompareAggregate(data) {
  const measures = data.measures || [];
  document.getElementById('cmp-agg-tbody').innerHTML = measures.map(m => {
    const va = data.aggregate_a?.[m], vb = data.aggregate_b?.[m], d = data.aggregate_delta?.[m];
    return `<tr><td>${esc(metricLabel(m))}</td>` +
      `<td class="${va != null ? metricCls(va) : 'metric-lo'}">${fmt(va)}</td>` +
      `<td class="${vb != null ? metricCls(vb) : 'metric-lo'}">${fmt(vb)}</td>` +
      `<td class="${deltaCls(d)}">${d != null ? (d >= 0 ? '+' : '') + d.toFixed(3) : '-'}</td></tr>`;
  }).join('');
}

function rowKey(row) { return cmpType === 'ir' ? row.query_id : row.index; }

function deltaCls(d) {
  if (d == null || Math.abs(d) < 0.01) return 'metric-lo';
  return d > 0 ? 'delta-pos' : 'delta-neg';
}

function sortCompare(measure, part) {
  if (cmpSortKey.measure === measure && cmpSortKey.part === part) cmpSortAsc = !cmpSortAsc;
  else { cmpSortKey = { measure, part }; cmpSortAsc = true; }
  renderCompareTable(cmpData);
}

function toggleCompareRow(key) {
  const wasExpanded = String(cmpExpandedKey) === String(key);
  cmpExpandedKey = wasExpanded ? null : key;
  renderCompareTable(cmpData);
  // Expanding an IR row's source list needs qrels to mark judged doc_ids (Amendment 5) —
  // fetch in the background so marking works even if the Judgement panel is never opened.
  if (!wasExpanded && cmpType === 'ir') {
    const row = cmpData.rows.find(r => String(rowKey(r)) === String(key));
    if (row) ensureJudgementLoaded(row);
  }
}

function judgementLink(key) {
  return `<a href="#" class="cmp-judgement-link" style="font-size:.68rem;margin-left:.4rem;white-space:nowrap"
    onclick="event.stopPropagation();toggleJudgement('${esc(String(key))}');return false">Judgement</a>`;
}

function renderQueryCell(row) {
  const key = rowKey(row);
  if (cmpType === 'ir') {
    const qid = `<code>${esc(row.query_id ?? '')}</code>${judgementLink(key)}`;
    const text = row.query_text
      ? `<div style="font-size:.72rem;color:#666;margin-top:.15rem">${esc(row.query_text)}</div>`
      : '';
    return qid + text;
  }
  const text = row.query_text
    ? `<div style="font-size:.82rem">${esc(row.query_text)}${judgementLink(key)}</div>`
    : `<div style="font-size:.82rem;color:#bbb">(no question)${judgementLink(key)}</div>`;
  const mismatch = row.query_text_mismatch
    ? `<div class="alert alert-warn" style="margin-top:.25rem;padding:.2rem .5rem;font-size:.68rem">` +
      `Question differs between runs — showing Run A&rsquo;s.<br>A: "${esc(row.content_a?.question ?? '')}"<br>B: "${esc(row.content_b?.question ?? '')}"</div>`
    : '';
  return text + mismatch;
}

// Display-only row filter (no re-fetch, no effect on sort or on only-in-A/B sections):
// judges each row by whichever metric currently drives the metric-column dropdown, using
// the same |delta| < 0.01 grey-zone threshold as deltaCls().
function passesRowFilter(row) {
  if (cmpRowFilter === 'all') return true;
  const d = row.delta[activeFilterMetric()];
  if (d == null) return false;
  return cmpRowFilter === 'improved' ? d > 0.01 : d < -0.01;
}

function renderCompareTable(data) {
  const measures = cmpMetricFilter ? [cmpMetricFilter] : data.measures;
  const rows = data.rows.filter(passesRowFilter);
  const colCount = 1 + measures.length * 3;

  rows.sort((r1, r2) => {
    const pick = row => cmpSortKey.part === 'delta' ? row.delta[cmpSortKey.measure] : row[cmpSortKey.part][cmpSortKey.measure];
    const v1 = pick(r1), v2 = pick(r2);
    const a = v1 == null ? -Infinity : v1;
    const b = v2 == null ? -Infinity : v2;
    return cmpSortAsc ? a - b : b - a;
  });

  const groupHeader = `<th rowspan="2">Query</th>` +
    measures.map(m => `<th colspan="3" class="group-th">${esc(metricLabel(m))}</th>`).join('');
  const subHeader = measures.map(m => {
    const sortTh = (part, label) => {
      const active = cmpSortKey.measure === m && cmpSortKey.part === part;
      const arrow = active ? (cmpSortAsc ? ' ▲' : ' ▼') : '';
      return `<th class="sortable" onclick="sortCompare('${m}','${part}')">${label}${arrow}</th>`;
    };
    return sortTh('a', 'A') + sortTh('b', 'B') + sortTh('delta', 'Δ');
  }).join('');
  document.getElementById('cmp-thead').innerHTML = `<tr>${groupHeader}</tr><tr>${subHeader}</tr>`;

  const tbody = document.getElementById('cmp-tbody');
  if (!rows.length) {
    const msg = data.rows.length && cmpRowFilter !== 'all'
      ? 'No rows match the current filter.'
      : 'No overlapping queries between these two runs.';
    tbody.innerHTML = `<tr><td colspan="${colCount}" style="text-align:center;color:#aaa;padding:1.5rem">${msg}</td></tr>`;
    return;
  }

  tbody.innerHTML = rows.map(row => {
    const key = rowKey(row);
    const cells = measures.map(m => {
      const va = row.a[m], vb = row.b[m], d = row.delta[m];
      return `<td class="${va != null ? metricCls(va) : 'metric-lo'}">${fmt(va)}</td>` +
             `<td class="${vb != null ? metricCls(vb) : 'metric-lo'}">${fmt(vb)}</td>` +
             `<td class="${deltaCls(d)}">${d != null ? (d >= 0 ? '+' : '') + d.toFixed(3) : '-'}</td>`;
    }).join('');
    const mainRow = `<tr class="cmp-row" onclick="toggleCompareRow('${esc(String(key))}')">
      <td>${renderQueryCell(row)}</td>${cells}
    </tr>`;
    const judgementRow = cmpOpenJudgements.has(String(key))
      ? `<tr class="cmp-judgement-row"><td colspan="${colCount}">${renderJudgementPanel(row, key)}</td></tr>`
      : '';
    const expanded = String(cmpExpandedKey) === String(key)
      ? `<tr class="cmp-expand-row"><td colspan="${colCount}">${renderCompareRowContent(row)}</td></tr>`
      : '';
    return mainRow + judgementRow + expanded;
  }).join('');
}

async function toggleJudgement(keyStr) {
  if (cmpOpenJudgements.has(keyStr)) {
    cmpOpenJudgements.delete(keyStr);
    renderCompareTable(cmpData);
    return;
  }
  cmpOpenJudgements.add(keyStr);
  renderCompareTable(cmpData);
  const row = cmpData.rows.find(r => String(rowKey(r)) === keyStr);
  if (row) await ensureJudgementLoaded(row);
}

// Shared by toggleJudgement (Judgement panel open) and toggleCompareRow (source-list
// expansion, Amendment 5) so there is one fetch/cache implementation, not two.
async function ensureJudgementLoaded(row) {
  if (cmpType !== 'ir') return; // RAG needs no fetch — renders from cmpData directly
  const dataset = cmpData.dataset;
  const queryId = row.query_id;
  const cacheKey = `${dataset}::${queryId}`;
  if (cmpJudgementCache.has(cacheKey)) return;
  cmpJudgementCache.set(cacheKey, { status: 'loading' });
  renderCompareTable(cmpData);
  try {
    const r = await fetch(`/api/eval/judgement?dataset=${enc(dataset)}&queryId=${enc(queryId)}`);
    const data = await r.json();
    if (!r.ok) {
      cmpJudgementCache.set(cacheKey, { status: 'error', message: data.error || 'Judgements unavailable for this dataset' });
    } else {
      cmpJudgementCache.set(cacheKey, { status: 'ok', judgements: data.judgements || [] });
    }
  } catch (e) {
    cmpJudgementCache.set(cacheKey, { status: 'error', message: `Network error: ${e.message}` });
  }
  renderCompareTable(cmpData);
}

function renderJudgementPanel(row, key) {
  if (cmpType === 'rag') {
    if (row.ground_truth_mismatch) {
      return `<div class="cmp-judgement-panel">
        <h4>Judgement (Ground Truth)</h4>
        <div class="alert alert-warn" style="padding:.35rem .6rem;font-size:.76rem">
          Ground truth differs between runs at this position.
          <div style="margin-top:.3rem"><strong>Run A:</strong> ${esc(row.content_a?.ground_truth ?? '(none)')}</div>
          <div style="margin-top:.2rem"><strong>Run B:</strong> ${esc(row.content_b?.ground_truth ?? '(none)')}</div>
        </div>
      </div>`;
    }
    return `<div class="cmp-judgement-panel">
      <h4>Judgement (Ground Truth)</h4>
      <div style="font-size:.8rem;color:#333">${esc(row.ground_truth ?? '(none)')}</div>
    </div>`;
  }

  const dataset = cmpData.dataset;
  const cacheKey = `${dataset}::${row.query_id}`;
  const cached = cmpJudgementCache.get(cacheKey);
  if (!cached || cached.status === 'loading') {
    return `<div class="cmp-judgement-panel"><h4>Judgement (Qrels)</h4><div style="font-size:.78rem;color:#999">Loading&hellip;</div></div>`;
  }
  if (cached.status === 'error') {
    return `<div class="cmp-judgement-panel"><h4>Judgement (Qrels)</h4><div style="font-size:.78rem;color:#c0392b">${esc(cached.message)}</div></div>`;
  }
  if (!cached.judgements.length) {
    return `<div class="cmp-judgement-panel"><h4>Judgement (Qrels)</h4><div style="font-size:.78rem;color:#999">No judgements recorded for this query.</div></div>`;
  }
  const rowKeyStr = String(key);
  const rowsHtml = cached.judgements.map((j, idx) => {
    const docKeyStr = docKey(rowKeyStr, 'j', idx, j.doc_id);
    let detail = '';
    if (cmpExpandedDocs.has(docKeyStr)) {
      const docCached = cmpDocCache.get(`${dataset}::${j.doc_id}`);
      if (!docCached || docCached.status === 'loading') {
        detail = `<tr><td colspan="2" style="padding:.4rem .75rem;color:#999;font-size:.75rem">Loading&hellip;</td></tr>`;
      } else if (docCached.status === 'error') {
        detail = `<tr><td colspan="2" style="padding:.4rem .75rem;color:#c0392b;font-size:.75rem">${esc(docCached.message)}</td></tr>`;
      } else {
        detail = `<tr><td colspan="2" style="padding:.5rem .75rem;background:#fff">
          ${renderHighlightFragments(dataset, j.doc_id, row.query_text)}
          <div style="font-weight:600;font-size:.78rem;margin-bottom:.2rem">${esc(docCached.title || '(untitled)')}</div>
          <div style="font-size:.76rem;color:#555">${esc(docCached.text || '')}</div>
        </td></tr>`;
      }
    }
    const retrievedBadge = retrievedMark(row, j.doc_id);
    return `<tr class="cmp-doc-row" style="cursor:pointer" onclick="toggleCompareDoc('${esc(rowKeyStr)}','j',${idx},'${esc(j.doc_id)}')">` +
      `<td><code>${esc(j.doc_id)}</code>${retrievedBadge}</td><td>${esc(String(j.score))}</td></tr>${detail}`;
  }).join('');
  return `<div class="cmp-judgement-panel">
    <h4>Judgement (Qrels)</h4>
    <table style="font-size:.78rem"><thead><tr><th>Doc ID</th><th>Score</th></tr></thead><tbody>${rowsHtml}</tbody></table>
  </div>`;
}

function renderCompareRowContent(row) {
  if (cmpType === 'rag') {
    const ca = row.content_a || {};
    const cb = row.content_b || {};
    const contextsHtml = ctxs => (ctxs && ctxs.length)
      ? ctxs.map((c, i) => `<div style="font-size:.78rem;color:#555;padding:.2rem 0">[${i+1}] ${esc(c)}</div>`).join('')
      : '<div style="font-size:.78rem;color:#bbb">(no contexts)</div>';
    const col = (label, content) => `<div class="cmp-content-col">
      <h4>${label} &mdash; Answer</h4>
      <div class="answer-text" style="font-size:.8rem">${esc(content.answer ?? '')}</div>
      <h4 style="margin-top:.75rem">Contexts</h4>
      ${contextsHtml(content.contexts)}
    </div>`;
    return `<div class="cmp-question"><strong>Q:</strong> ${esc(ca.question ?? cb.question ?? '')}</div>
      <div class="cmp-content-grid">${col('Run A', ca)}${col('Run B', cb)}</div>`;
  }

  const rowKeyStr = String(rowKey(row));
  return `<div class="cmp-content-grid">
    <div class="cmp-content-col"><h4>Run A &mdash; Sources</h4>${renderSourceList(row.sources_a, rowKeyStr, 'a', row)}</div>
    <div class="cmp-content-col"><h4>Run B &mdash; Sources</h4>${renderSourceList(row.sources_b, rowKeyStr, 'b', row)}</div>
  </div>`;
}

function docKey(rowKeyStr, side, idx, docId) { return `${rowKeyStr}|${side}|${idx}|${docId}`; }

// Amendment 5: doc_id -> rank in a source list, or null. Shared by the judged-mark lookup
// (source list) and the retrieved-mark lookup (Judgement panel) so there's one find/indexOf.
function sourceRank(sources, docId) {
  if (!sources) return null;
  const found = sources.find(s => s.doc_id === docId);
  return found ? found.rank : null;
}

// Amendment 5: badge for a Judgement-panel doc_id showing which run(s) retrieved it and at
// what rank, using sources_a/sources_b already on the row — no fetch needed.
function retrievedMark(row, docId) {
  const rankA = sourceRank(row.sources_a, docId);
  const rankB = sourceRank(row.sources_b, docId);
  if (rankA == null && rankB == null) return '';
  const parts = [];
  if (rankA != null) parts.push(`A #${rankA}`);
  if (rankB != null) parts.push(`B #${rankB}`);
  return `<span class="delta-pos" style="font-size:.68rem;margin-left:.4rem">Retrieved: ${parts.join(', ')}</span>`;
}

// Amendment 5: badge for a source-list doc_id showing whether it's judged relevant (qrels
// score > 0) or explicitly judged non-relevant (score === 0). No badge if qrels haven't
// resolved yet or the doc_id isn't judged — additive only, same rendering otherwise.
function judgedMark(dataset, queryId, docId) {
  const cached = cmpJudgementCache.get(`${dataset}::${queryId}`);
  if (!cached || cached.status !== 'ok') return '';
  const j = cached.judgements.find(j => j.doc_id === docId);
  if (!j) return '';
  return j.score > 0
    ? `<span class="delta-pos" style="font-size:.68rem;margin-left:.4rem">Judged relevant</span>`
    : `<span class="metric-lo" style="font-size:.68rem;margin-left:.4rem">Judged non-relevant</span>`;
}

function renderSourceList(sources, rowKeyStr, side, row) {
  if (!sources || !sources.length) {
    return '<div style="font-size:.78rem;color:#bbb">No source detail for this run</div>';
  }
  const queryText = row.query_text;
  const rowsHtml = sources.map((s, idx) => {
    const key = docKey(rowKeyStr, side, idx, s.doc_id);
    const expanded = cmpExpandedDocs.has(key);
    let detail = '';
    if (expanded) {
      const cacheKey = `${cmpData.dataset}::${s.doc_id}`;
      const cached = cmpDocCache.get(cacheKey);
      if (!cached || cached.status === 'loading') {
        detail = `<tr><td colspan="3" style="padding:.4rem .75rem;color:#999;font-size:.75rem">Loading&hellip;</td></tr>`;
      } else if (cached.status === 'error') {
        detail = `<tr><td colspan="3" style="padding:.4rem .75rem;color:#c0392b;font-size:.75rem">${esc(cached.message)}</td></tr>`;
      } else {
        detail = `<tr><td colspan="3" style="padding:.5rem .75rem;background:#fff">
          ${renderHighlightFragments(cmpData.dataset, s.doc_id, queryText)}
          <div style="font-weight:600;font-size:.78rem;margin-bottom:.2rem">${esc(cached.title || '(untitled)')}</div>
          <div style="font-size:.76rem;color:#555">${esc(cached.text || '')}</div>
        </td></tr>`;
      }
    }
    const judgedBadge = judgedMark(cmpData.dataset, row.query_id, s.doc_id);
    return `<tr class="cmp-doc-row" style="cursor:pointer" onclick="toggleCompareDoc('${esc(rowKeyStr)}','${side}',${idx},'${esc(s.doc_id)}')">` +
      `<td>${s.rank}</td><td><code>${esc(s.doc_id)}</code>${judgedBadge}</td><td>${s.score.toFixed(3)}</td></tr>${detail}`;
  }).join('');
  return `<table style="font-size:.78rem"><thead><tr><th>Rank</th><th>Doc ID</th><th>Score</th></tr></thead><tbody>${rowsHtml}</tbody></table>`;
}

async function toggleCompareDoc(rowKeyStr, side, idx, docId) {
  const key = docKey(rowKeyStr, side, idx, docId);
  if (cmpExpandedDocs.has(key)) {
    cmpExpandedDocs.delete(key);
    renderCompareTable(cmpData);
    return;
  }
  cmpExpandedDocs.add(key);
  renderCompareTable(cmpData);

  const dataset = cmpData.dataset;
  const fetches = [fetchCompareDocument(dataset, docId)];
  // IR only: highlighting needs a query string to match against, and RAG rows
  // have no per-document search step (see Amendment 4 — highlight is IR-only).
  if (cmpType === 'ir') {
    const row = cmpData.rows.find(r => String(rowKey(r)) === rowKeyStr);
    if (row && row.query_text) {
      fetches.push(fetchCompareHighlight(dataset, docId, row.query_text));
    }
  }
  await Promise.all(fetches);
}

async function fetchCompareDocument(dataset, docId) {
  const cacheKey = `${dataset}::${docId}`;
  if (cmpDocCache.has(cacheKey)) return;
  cmpDocCache.set(cacheKey, { status: 'loading' });
  renderCompareTable(cmpData);
  try {
    const r = await fetch(`/api/eval/document?dataset=${enc(dataset)}&docId=${enc(docId)}`);
    const data = await r.json();
    if (!r.ok) {
      cmpDocCache.set(cacheKey, { status: 'error', message: data.error || 'Document not found' });
    } else {
      cmpDocCache.set(cacheKey, { status: 'ok', title: data.title, text: data.text });
    }
  } catch (e) {
    cmpDocCache.set(cacheKey, { status: 'error', message: `Network error: ${e.message}` });
  }
  renderCompareTable(cmpData);
}

async function fetchCompareHighlight(dataset, docId, queryText) {
  const cacheKey = `${dataset}::${docId}::${queryText}`;
  if (cmpHighlightCache.has(cacheKey)) return;
  cmpHighlightCache.set(cacheKey, { status: 'loading' });
  renderCompareTable(cmpData);
  try {
    const r = await fetch(`/api/eval/highlight?dataset=${enc(dataset)}&docId=${enc(docId)}&query=${enc(queryText)}`);
    const data = await r.json();
    if (!r.ok || data.error) {
      cmpHighlightCache.set(cacheKey, { status: 'error', message: data.error || 'Highlight unavailable' });
    } else {
      cmpHighlightCache.set(cacheKey, { status: 'ok', fragments: data.fragments || [] });
    }
  } catch (e) {
    cmpHighlightCache.set(cacheKey, { status: 'error', message: `Network error: ${e.message}` });
  }
  renderCompareTable(cmpData);
}

function renderHighlightFragments(dataset, docId, queryText) {
  if (!queryText) return '';
  const cacheKey = `${dataset}::${docId}::${queryText}`;
  const cached = cmpHighlightCache.get(cacheKey);
  if (!cached || cached.status === 'loading') {
    return `<div style="font-size:.74rem;color:#999;margin-bottom:.35rem">Loading match highlight&hellip;</div>`;
  }
  if (cached.status === 'error') {
    return `<div style="font-size:.74rem;color:#c0392b;margin-bottom:.35rem">${esc(cached.message)}</div>`;
  }
  if (!cached.fragments.length) {
    return `<div style="font-size:.74rem;color:#999;margin-bottom:.35rem">No live-index match for this query.</div>`;
  }
  // Fragments are OpenSearch's copy of ingested document text, not something this
  // feature controls — escape everything first, then restore only the literal
  // <em>/</em> markers OpenSearch inserts, so no other markup in the source can execute.
  const fragmentsHtml = cached.fragments
    .map(f => esc(f).replaceAll('&lt;em&gt;', '<em>').replaceAll('&lt;/em&gt;', '</em>'))
    .join('<br>');
  return `<div style="font-size:.76rem;color:#333;background:#fffbe6;padding:.3rem .5rem;border-radius:3px;margin-bottom:.4rem">${fragmentsHtml}</div>`;
}

function renderCompareOnly(data) {
  const card = document.getElementById('cmp-only-card');
  const onlyA = data.only_in_a || [];
  const onlyB = data.only_in_b || [];
  if (!onlyA.length && !onlyB.length) { card.style.display = 'none'; return; }
  card.style.display = 'block';

  const measures = cmpMetricFilter ? [cmpMetricFilter] : data.measures;
  const renderList = (items, side) => {
    if (!items.length) return '';
    return `<div class="only-section-title">Only in Run ${side} (${items.length})</div>
      <table style="margin-bottom:1rem">
        <thead><tr><th>Query</th>${measures.map(m => `<th>${esc(metricLabel(m))}</th>`).join('')}</tr></thead>
        <tbody>${items.map(item => {
          const metrics = side === 'A' ? item.a : item.b;
          const cells = measures.map(m => {
            const v = metrics ? metrics[m] : null;
            return `<td class="${v != null ? metricCls(v) : 'metric-lo'}">${fmt(v)}</td>`;
          }).join('');
          const queryCell = cmpType === 'ir'
            ? `<code>${esc(item.query_id ?? item.index)}</code>` +
              (item.query_text ? `<div style="font-size:.72rem;color:#666;margin-top:.15rem">${esc(item.query_text)}</div>` : '')
            : (item.query_text ? esc(item.query_text) : `<code>${esc(item.query_id ?? item.index)}</code>`);
          return `<tr><td>${queryCell}</td>${cells}</tr>`;
        }).join('')}</tbody>
      </table>`;
  };

  document.getElementById('cmp-only-content').innerHTML = renderList(onlyA, 'A') + renderList(onlyB, 'B');
}
</script>
</body>
</html>"""


def render(openai_key_set: bool) -> str:
    return HTML_TEMPLATE.replace("__OPENAI_KEY_SET__", str(openai_key_set).lower())
