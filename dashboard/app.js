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

const elEventsSection = document.getElementById('events-section');
const elEventsList    = document.getElementById('events-list');

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
    hide(elEventsSection);
    return;
  }
  show(elEventsSection);

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
  // Ordered list of URLs to try — most recent first
  const candidates = [];

  // Last 14 days via raw.githubusercontent.com
  for (let i = 0; i < 14; i++) {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() - i);
    const y  = d.getUTCFullYear();
    const mo = String(d.getUTCMonth() + 1).padStart(2, '0');
    const dy = String(d.getUTCDate()).padStart(2, '0');
    candidates.push(`${RAW_BASE}/${y}-${mo}-${dy}.json`);
  }

  for (const url of candidates) {
    try {
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        return data;
      }
    } catch (_) {}
  }

  // Hard-coded known-good URL as last resort
  try {
    const res = await fetch(
      'https://raw.githubusercontent.com/ankkydoon/stockSentimentAnalysis/main/outputs/2026-06-10.json'
    );
    if (res.ok) return res.json();
  } catch (_) {}

  throw new Error(
    'Could not load pipeline data. ' +
    'Tried last 14 days — no output file found. ' +
    'Please run the pipeline first.'
  );
}

/* ── Embedded fallback data (last known pipeline run) ────────────────────── */
const EMBEDDED_DATA = {"run_date": "2026-06-10", "signals": [{"ticker": "MU", "direction": "neutral", "confidence": 0.047, "score": -0.057, "sentiment_component": -0.001, "event_component": 0.0, "price_component": -0.375, "generated_at": "2026-06-10 03:02:10+00:00", "horizon_days": 5}, {"ticker": "MS", "direction": "neutral", "confidence": 0.039, "score": -0.045, "sentiment_component": -0.001, "event_component": 0.0, "price_component": -0.295, "generated_at": "2026-06-10 03:02:11+00:00", "horizon_days": 5}, {"ticker": "TSLA", "direction": "neutral", "confidence": 0.059, "score": -0.077, "sentiment_component": -0.001, "event_component": 0.0, "price_component": -0.512, "generated_at": "2026-06-10 03:02:11+00:00", "horizon_days": 5}, {"ticker": "GS", "direction": "neutral", "confidence": 0.045, "score": -0.054, "sentiment_component": -0.007, "event_component": 0.0, "price_component": -0.334, "generated_at": "2026-06-10 03:02:11+00:00", "horizon_days": 5}, {"ticker": "NVDA", "direction": "neutral", "confidence": 0.058, "score": -0.074, "sentiment_component": -0.007, "event_component": 0.0, "price_component": -0.472, "generated_at": "2026-06-10 03:02:11+00:00", "horizon_days": 5}, {"ticker": "GOOGL", "direction": "neutral", "confidence": 0.006, "score": 0.006, "sentiment_component": -0.007, "event_component": 0.0, "price_component": 0.065, "generated_at": "2026-06-10 03:02:12+00:00", "horizon_days": 5}, {"ticker": "SMCI", "direction": "neutral", "confidence": 0.067, "score": -0.094, "sentiment_component": -0.007, "event_component": 0.0, "price_component": -0.601, "generated_at": "2026-06-10 03:02:12+00:00", "horizon_days": 5}, {"ticker": "JPM", "direction": "neutral", "confidence": 0.062, "score": 0.088, "sentiment_component": -0.007, "event_component": 0.0, "price_component": 0.609, "generated_at": "2026-06-10 03:02:12+00:00", "horizon_days": 5}], "events": [], "investment_plan": null};

// ── Boot ──────────────────────────────────────────────────────────────────────

async function init() {
  // Render embedded data instantly — no spinner wait
  hide(elLoading);
  hide(elError);
  renderDashboard(EMBEDDED_DATA);

  // Silently try to fetch fresher data in the background
  try {
    const fresh = await fetchLatestOutput();
    if (fresh && fresh.run_date !== EMBEDDED_DATA.run_date) {
      renderDashboard(fresh);
    }
  } catch (_) {
    // Silently ignore — embedded data is already shown
  }
}

document.addEventListener('DOMContentLoaded', init);
