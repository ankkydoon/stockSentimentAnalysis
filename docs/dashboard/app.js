/* ============================================================
   Stock Sentiment Dashboard — app.js
   Fetches the latest pipeline output from GitHub and renders
   all dashboard sections.
   ============================================================ */

// Allowlisted direction values that map to CSS class suffixes.
const DIRECTION_CLASSES = new Set(['bullish', 'bearish', 'neutral']);

// ── DOM refs ──────────────────────────────────────────────────────────────────

const elLoading       = document.getElementById('loading');
const elError         = document.getElementById('error');
const elErrorMsg      = document.getElementById('error-message');
const elDashboard     = document.getElementById('dashboard');
const elRunDate       = document.getElementById('run-date');
const elLastUpdated   = document.getElementById('last-updated');

const elSignalsBody       = document.getElementById('signals-body');
const elSignalsEmpty      = document.getElementById('signals-empty');
const elSignalsPagination = document.getElementById('signals-pagination');
const elSignalsPrev       = document.getElementById('signals-prev');
const elSignalsNext       = document.getElementById('signals-next');
const elSignalsPageInfo   = document.getElementById('signals-page-info');

const elEventsList        = document.getElementById('events-list');
const elEventsEmpty       = document.getElementById('events-empty');
const elEventsPagination  = document.getElementById('events-pagination');
const elEventsPrev        = document.getElementById('events-prev');
const elEventsNext        = document.getElementById('events-next');
const elEventsPageInfo    = document.getElementById('events-page-info');

const PAGE_SIZE = 10;
let _signalRows = [], _signalPage = 0;
let _eventRows  = [], _eventPage  = 0;

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

function renderSignalPage() {
  elSignalsBody.textContent = '';
  const slice = _signalRows.slice(_signalPage * PAGE_SIZE, (_signalPage + 1) * PAGE_SIZE);
  slice.forEach(sig => {
    const score = sig.score != null ? parseFloat(sig.score).toFixed(3) : '—';
    const tr = document.createElement('tr');
    const tickerCell = document.createElement('td');
    tickerCell.className = 'ticker-cell';
    const link = document.createElement('a');
    link.href = `stock.html?ticker=${encodeURIComponent(sig.ticker)}`;
    link.className = 'ticker-link';
    link.textContent = sig.ticker;
    tickerCell.appendChild(link);
    tr.appendChild(tickerCell);
    tr.appendChild(td(directionChip(sig.direction)));
    tr.appendChild(td(confidenceBar(sig.confidence)));
    tr.appendChild(td(score, 'score-cell'));
    elSignalsBody.appendChild(tr);
  });
  const total = Math.ceil(_signalRows.length / PAGE_SIZE);
  if (elSignalsPageInfo) elSignalsPageInfo.textContent = `Page ${_signalPage + 1} of ${total}`;
  if (elSignalsPrev)     elSignalsPrev.disabled = _signalPage === 0;
  if (elSignalsNext)     elSignalsNext.disabled = _signalPage >= total - 1;
}

function renderSignals(signals) {
  if (!Array.isArray(signals) || signals.length === 0) {
    show(elSignalsEmpty);
    hide(elSignalsPagination);
    return;
  }
  hide(elSignalsEmpty);
  _signalRows = signals.slice().sort((a, b) => (parseFloat(b.score) || 0) - (parseFloat(a.score) || 0));
  _signalPage = 0;
  renderSignalPage();
  if (_signalRows.length > PAGE_SIZE) show(elSignalsPagination);
}

// ── Render: Events ────────────────────────────────────────────────────────────

function renderEventPage() {
  elEventsList.textContent = '';
  const slice = _eventRows.slice(_eventPage * PAGE_SIZE, (_eventPage + 1) * PAGE_SIZE);
  slice.forEach(ev => {
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
  const total = Math.ceil(_eventRows.length / PAGE_SIZE);
  if (elEventsPageInfo) elEventsPageInfo.textContent = `Page ${_eventPage + 1} of ${total}`;
  if (elEventsPrev)     elEventsPrev.disabled = _eventPage === 0;
  if (elEventsNext)     elEventsNext.disabled = _eventPage >= total - 1;
}

function renderEvents(events) {
  if (!Array.isArray(events) || events.length === 0) {
    show(elEventsEmpty);
    hide(elEventsPagination);
    return;
  }
  hide(elEventsEmpty);
  _eventRows = events;
  _eventPage = 0;
  renderEventPage();
  if (_eventRows.length > PAGE_SIZE) show(elEventsPagination);
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
  const res = await fetch('../latest.json');
  if (!res.ok) {
    throw new Error(`Could not load latest.json (${res.status}). Run the pipeline to generate data.`);
  }
  return res.json();
}

// ── Boot ──────────────────────────────────────────────────────────────────────

async function init() {
  hide(elLoading);
  hide(elError);
  show(elDashboard);

  try {
    const data = await fetchLatestOutput();
    renderDashboard(data);
  } catch (err) {
    // Only show error if dashboard has no content yet
    if (elSignalsBody && elSignalsBody.children.length === 0) {
      showError(err.message);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (elSignalsPrev) elSignalsPrev.addEventListener('click', () => { if (_signalPage > 0) { _signalPage--; renderSignalPage(); } });
  if (elSignalsNext) elSignalsNext.addEventListener('click', () => { if (_signalPage < Math.ceil(_signalRows.length / PAGE_SIZE) - 1) { _signalPage++; renderSignalPage(); } });
  if (elEventsPrev)  elEventsPrev.addEventListener('click',  () => { if (_eventPage > 0)  { _eventPage--;  renderEventPage();  } });
  if (elEventsNext)  elEventsNext.addEventListener('click',  () => { if (_eventPage < Math.ceil(_eventRows.length / PAGE_SIZE) - 1)  { _eventPage++;  renderEventPage();  } });
  init();
});
