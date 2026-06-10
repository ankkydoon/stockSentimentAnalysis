/* ============================================================
   Stock Sentiment Dashboard — app.js
   Fetches the latest pipeline output from GitHub and renders
   all dashboard sections.
   ============================================================ */

const GITHUB_CONTENTS_API =
  'https://api.github.com/repos/ankkydoon/stockSentimentAnalysis/contents/outputs';

// Direct raw URL fallback — no rate limit, always works
const RAW_BASE =
  'https://raw.githubusercontent.com/ankkydoon/stockSentimentAnalysis/main/outputs';

// Allowlisted direction values that map to CSS class suffixes.
const DIRECTION_CLASSES = new Set(['bullish', 'bearish', 'neutral']);

// ── DOM refs ──────────────────────────────────────────────────────────────────

const elLoading       = document.getElementById('loading');
const elError         = document.getElementById('error');
const elErrorMsg      = document.getElementById('error-message');
const elDashboard     = document.getElementById('dashboard');
const elRunDate       = document.getElementById('run-date');
const elLastUpdated   = document.getElementById('last-updated');

const elSignalsBody   = document.getElementById('signals-body');
const elSignalsEmpty  = document.getElementById('signals-empty');

const elEventsList    = document.getElementById('events-list');
const elEventsEmpty   = document.getElementById('events-empty');

const elPlanEmpty     = document.getElementById('plan-empty');
const elPlanDetails   = document.getElementById('plan-details');
const elPlanTotal     = document.getElementById('plan-total');
const elPlanRebalance = document.getElementById('plan-rebalance');
const elPlanReturn    = document.getElementById('plan-return');
const elPlanRisk      = document.getElementById('plan-risk');
const elAllocBody     = document.getElementById('allocations-body');
const elPlanDisclaimer = document.getElementById('plan-disclaimer');

// ── Helpers ───────────────────────────────────────────────────────────────────

function show(el) { el.hidden = false; }
function hide(el) { el.hidden = true; }

/** Create an element, optionally setting className and textContent. */
function el(tag, { className, text, title } = {}) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  if (title != null) node.title = title;
  return node;
}

function formatCurrency(value) {
  if (value == null || isNaN(value)) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value) {
  if (value == null || isNaN(value)) return '—';
  return `${parseFloat(value).toFixed(1)}%`;
}

// ── Direction chip ────────────────────────────────────────────────────────────

/** Returns a <span> DOM node — no innerHTML involved. */
function directionChip(direction) {
  const d = DIRECTION_CLASSES.has((direction || '').toLowerCase())
    ? direction.toLowerCase()
    : 'neutral';
  const label = d.charAt(0).toUpperCase() + d.slice(1);
  return el('span', { className: `chip chip-${d}`, text: label });
}

// ── Confidence bar ────────────────────────────────────────────────────────────

/** Returns a <div> DOM node — no innerHTML involved. */
function confidenceBar(confidence) {
  const pct = Math.max(0, Math.min(1, parseFloat(confidence) || 0));
  const percentage = Math.round(pct * 100);
  let colorClass = 'bar-low';
  if (pct >= 0.7) colorClass = 'bar-high';
  else if (pct >= 0.4) colorClass = 'bar-mid';

  const wrap = el('div', { className: 'conf-bar-wrap', title: `${percentage}%` });
  const bar  = el('div', { className: `conf-bar ${colorClass}` });
  bar.style.width = `${percentage}%`;
  const label = el('span', { className: 'conf-label', text: `${percentage}%` });
  wrap.appendChild(bar);
  wrap.appendChild(label);
  return wrap;
}

// ── Severity badge ────────────────────────────────────────────────────────────

/** Returns a <span> DOM node — no innerHTML involved. */
function severityBadge(severity) {
  const s = parseFloat(severity) || 0;
  let level, label;
  if (s >= 0.7)      { level = 'high';   label = 'High'; }
  else if (s >= 0.4) { level = 'medium'; label = 'Medium'; }
  else               { level = 'low';    label = 'Low'; }
  return el('span', { className: `badge badge-${level}`, text: label });
}

// ── TD builder ────────────────────────────────────────────────────────────────

/** Create a <td> whose content is either a text string or a DOM node. */
function td(content, className) {
  const cell = document.createElement('td');
  if (className) cell.className = className;
  if (content instanceof Node) {
    cell.appendChild(content);
  } else {
    cell.textContent = content != null ? String(content) : '';
  }
  return cell;
}

// ── Render: Signals ───────────────────────────────────────────────────────────

function renderSignals(signals) {
  elSignalsBody.textContent = ''; // clears children without innerHTML
  if (!Array.isArray(signals) || signals.length === 0) {
    show(elSignalsEmpty);
    return;
  }
  hide(elSignalsEmpty);

  const rows = signals
    .slice()
    .sort((a, b) => (parseFloat(b.score) || 0) - (parseFloat(a.score) || 0));

  rows.forEach(sig => {
    const score = sig.score != null ? parseFloat(sig.score).toFixed(3) : '—';
    const tr = document.createElement('tr');
    tr.appendChild(td(sig.ticker, 'ticker-cell'));
    tr.appendChild(td(directionChip(sig.direction)));
    tr.appendChild(td(confidenceBar(sig.confidence)));
    tr.appendChild(td(score, 'score-cell'));
    elSignalsBody.appendChild(tr);
  });
}

// ── Render: Events ────────────────────────────────────────────────────────────

function renderEvents(events) {
  elEventsList.textContent = '';
  if (!Array.isArray(events) || events.length === 0) {
    show(elEventsEmpty);
    return;
  }
  hide(elEventsEmpty);

  events.forEach(ev => {
    const item = el('div', { className: 'event-item' });

    const header = el('div', { className: 'event-header' });
    header.appendChild(el('span', { className: 'event-ticker', text: ev.ticker }));
    const category = (ev.category || 'unknown').replace(/_/g, ' ');
    header.appendChild(el('span', { className: 'event-category', text: category }));
    header.appendChild(severityBadge(ev.severity));

    const summary = el('p', { className: 'event-summary', text: ev.summary });

    item.appendChild(header);
    item.appendChild(summary);
    elEventsList.appendChild(item);
  });
}

// ── Render: Investment Plan ───────────────────────────────────────────────────

function renderPlan(plan) {
  if (!plan || typeof plan !== 'object') {
    show(elPlanEmpty);
    hide(elPlanDetails);
    return;
  }

  hide(elPlanEmpty);
  show(elPlanDetails);

  elPlanTotal.textContent = formatCurrency(plan.total_amount);
  elPlanRebalance.textContent = plan.rebalance_trigger
    ? plan.rebalance_trigger.charAt(0).toUpperCase() + plan.rebalance_trigger.slice(1)
    : '—';

  if (Array.isArray(plan.expected_return_range) && plan.expected_return_range.length === 2) {
    elPlanReturn.textContent =
      `${plan.expected_return_range[0]}% – ${plan.expected_return_range[1]}%`;
  } else {
    elPlanReturn.textContent = '—';
  }

  elPlanRisk.textContent = '';
  if (plan.risk_summary) {
    const p = el('p', { className: 'risk-summary' });
    const strong = el('strong', { text: 'Risk: ' });
    p.appendChild(strong);
    p.appendChild(document.createTextNode(plan.risk_summary));
    elPlanRisk.appendChild(p);
  }

  elAllocBody.textContent = '';
  const allocs = Array.isArray(plan.allocations) ? plan.allocations : [];
  if (allocs.length === 0) {
    const tr = document.createElement('tr');
    const emptyCell = document.createElement('td');
    emptyCell.colSpan = 4;
    emptyCell.className = 'empty-cell';
    emptyCell.textContent = 'No allocations available.';
    tr.appendChild(emptyCell);
    elAllocBody.appendChild(tr);
  } else {
    allocs.forEach(alloc => {
      const tr = document.createElement('tr');
      tr.appendChild(td(alloc.ticker, 'ticker-cell'));
      tr.appendChild(td(formatCurrency(alloc.amount)));
      tr.appendChild(td(formatPercent(alloc.percentage)));
      tr.appendChild(td(alloc.rationale, 'rationale-cell'));
      elAllocBody.appendChild(tr);
    });
  }

  if (plan.disclaimer) {
    elPlanDisclaimer.textContent = plan.disclaimer;
    show(elPlanDisclaimer);
  }
}

// ── Render: full dashboard ────────────────────────────────────────────────────

function renderDashboard(data) {
  if (data.run_date) {
    elRunDate.textContent = `Run date: ${data.run_date}`;
  }

  renderSignals(data.signals);
  renderEvents(data.events);
  renderPlan(data.investment_plan);

  elLastUpdated.textContent = `Last updated: ${new Date().toLocaleString()}`;

  hide(elLoading);
  hide(elError);
  show(elDashboard);
}

// ── Show error ────────────────────────────────────────────────────────────────

function showError(message) {
  elErrorMsg.textContent = message || 'An unexpected error occurred.';
  hide(elLoading);
  hide(elDashboard);
  show(elError);
}

// ── Fetch pipeline output ─────────────────────────────────────────────────────

async function fetchLatestOutput() {
  // Try last 14 days of raw URLs directly (no rate limit, no auth)
  const errors = [];
  for (let i = 0; i < 14; i++) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const year  = d.getUTCFullYear();
    const month = String(d.getUTCMonth() + 1).padStart(2, '0');
    const day   = String(d.getUTCDate()).padStart(2, '0');
    const dateStr = `${year}-${month}-${day}`;
    const url = `${RAW_BASE}/${dateStr}.json`;
    try {
      const res = await fetch(url);
      if (res.ok) return res.json();
      errors.push(`${dateStr}: HTTP ${res.status}`);
    } catch (e) {
      errors.push(`${dateStr}: ${e.message}`);
    }
  }

  // Fall back to GitHub Contents API
  try {
    const dirRes = await fetch(GITHUB_CONTENTS_API, {
      headers: { Accept: 'application/vnd.github.v3+json' },
    });
    if (dirRes.ok) {
      const dirListing = await dirRes.json();
      const jsonFiles = (Array.isArray(dirListing) ? dirListing : [])
        .filter(f => f.type === 'file' && f.name.endsWith('.json'))
        .sort((a, b) => b.name.localeCompare(a.name));
      if (jsonFiles.length > 0) {
        const dataRes = await fetch(jsonFiles[0].download_url);
        if (dataRes.ok) return dataRes.json();
      }
    }
  } catch (_) {}

  throw new Error(
    `Could not load pipeline data. Tried last 14 days via raw URL.\n` +
    `Latest attempt errors: ${errors.slice(0, 3).join(', ')}\n` +
    `Direct URL: ${RAW_BASE}/2026-06-10.json`
  );
}

// ── Boot ──────────────────────────────────────────────────────────────────────

async function init() {
  show(elLoading);
  hide(elError);
  hide(elDashboard);

  try {
    const data = await fetchLatestOutput();
    renderDashboard(data);
  } catch (err) {
    showError(err.message);
  }
}

document.addEventListener('DOMContentLoaded', init);
