/* ============================================================
   Stock Sentiment Dashboard — app.js
   Fetches the latest pipeline output from GitHub and renders
   all dashboard sections.
   ============================================================ */

// Compact dashboard data written by the pipeline after each run
const LATEST_DATA_URL =
  'https://raw.githubusercontent.com/ankkydoon/stockSentimentAnalysis/main/docs/latest.json';

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
  const res = await fetch(LATEST_DATA_URL);
  if (!res.ok) throw new Error(`Failed to load dashboard data (HTTP ${res.status})`);
  return res.json();
}

/* ── Embedded fallback data (last known pipeline run) ────────────────────── */
const EMBEDDED_DATA = {"run_date": "2026-06-10", "signals": [{"ticker": "COIN", "direction": "bearish", "confidence": 0.22, "score": -0.399, "sentiment_component": -0.099, "event_component": -1.0, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "GM", "direction": "bullish", "confidence": 0.23, "score": 0.29, "sentiment_component": 0.229, "event_component": 0.5, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "UBER", "direction": "neutral", "confidence": 0.176, "score": 0.224, "sentiment_component": 0.098, "event_component": 0.5, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "BAC", "direction": "neutral", "confidence": 0.174, "score": 0.222, "sentiment_component": 0.095, "event_component": 0.5, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "MS", "direction": "neutral", "confidence": 0.133, "score": 0.174, "sentiment_component": -0.001, "event_component": 0.5, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "TSLA", "direction": "neutral", "confidence": 0.133, "score": 0.174, "sentiment_component": -0.001, "event_component": 0.5, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "SMCI", "direction": "neutral", "confidence": 0.114, "score": -0.151, "sentiment_component": 0.048, "event_component": -0.5, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "GS", "direction": "neutral", "confidence": 0.101, "score": 0.136, "sentiment_component": -0.078, "event_component": 0.5, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "PLTR", "direction": "neutral", "confidence": 0.095, "score": 0.128, "sentiment_component": -0.094, "event_component": 0.5, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "INTC", "direction": "neutral", "confidence": 0.08, "score": 0.11, "sentiment_component": -0.13, "event_component": 0.5, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "META", "direction": "neutral", "confidence": 0.091, "score": -0.101, "sentiment_component": -0.201, "event_component": 0.0, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "JPM", "direction": "neutral", "confidence": 0.066, "score": 0.092, "sentiment_component": -0.165, "event_component": 0.5, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "CRM", "direction": "neutral", "confidence": 0.052, "score": 0.074, "sentiment_component": -0.201, "event_component": 0.5, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "NVDA", "direction": "neutral", "confidence": 0.023, "score": 0.024, "sentiment_component": 0.048, "event_component": 0.0, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "MU", "direction": "neutral", "confidence": 0.001, "score": -0.001, "sentiment_component": -0.001, "event_component": 0.0, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "AMZN", "direction": "neutral", "confidence": 0.0, "score": 0.0, "sentiment_component": 0.0, "event_component": 0.0, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "GOOGL", "direction": "neutral", "confidence": 0.0, "score": 0.0, "sentiment_component": 0.0, "event_component": 0.0, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}, {"ticker": "MSFT", "direction": "neutral", "confidence": 0.0, "score": 0.0, "sentiment_component": 0.0, "event_component": 0.0, "price_component": 0.0, "generated_at": "2026-06-10T17:24:00+00:00"}], "events": [{"ticker": null, "category": "macro_other", "severity": 0.5, "summary": "US President Trump escalates threats against Iran, leading to market reactions."}, {"ticker": null, "category": "macro_other", "severity": 0.4, "summary": "President Trump comments on inflation and hints at military actions affecting oil markets"}, {"ticker": "AMZN", "category": "regulatory_action", "severity": 0.5, "summary": "OpenAI and Anthropic confidentially file IPO prospectuses, introducing new terminology like 'tokens' in AI sector"}, {"ticker": null, "category": "regulatory_action", "severity": 0.8, "summary": "Sen. Elizabeth Warren calls for the SEC to delay SpaceX's IPO due to concerns about valuation and corporate governance."}, {"ticker": null, "category": "macro_other", "severity": 0.5, "summary": "President Trump signs $70 billion bill to fund immigration enforcement agencies"}, {"ticker": null, "category": "macro_other", "severity": 0.5, "summary": "Consumer prices in May rose to their fastest pace in over three years, increasing the inflation rate to 4.2% year-over-year."}, {"ticker": null, "category": "macro_other", "severity": 0.5, "summary": "College costs exceed $100,000 at multiple prestigious institutions, signaling a significant financial trend in higher education."}, {"ticker": "COIN", "category": "regulatory_action", "severity": 0.7, "summary": "AI Financial Corp. discloses improved outlook and faces potential delisting risk due to stock price issues"}, {"ticker": null, "category": "regulatory_action", "severity": 0.5, "summary": "Bill Gates discusses his association with Jeffrey Epstein and its impact on the Gates Foundation"}, {"ticker": null, "category": "regulatory_action", "severity": 0.8, "summary": "Presidential pick for acting director of national intelligence faces bipartisan pushback, risking lapse of surveillance program"}, {"ticker": null, "category": "macro_other", "severity": 0.4, "summary": "Crypto traders expect strong demand for SpaceX's upcoming IPO based on perpetual futures trading."}, {"ticker": "AMZN", "category": "macro_other", "severity": 0.4, "summary": "U.S. tech giants back German robotics company in a $1.4 billion fundraising round"}, {"ticker": "PLTR", "category": "management_change", "severity": 0.5, "summary": "Palantir CEO Alex Karp expresses concerns about the company's AI labs and customer satisfaction."}, {"ticker": "JPM", "category": "macro_other", "severity": 0.5, "summary": "U.S. President Trump's comments on Iran lead to fluctuations in oil prices and stock market reactions."}, {"ticker": null, "category": "macro_other", "severity": 0.5, "summary": "Market pressure due to geopolitical tensions and inflation concerns"}, {"ticker": null, "category": "macro_other", "severity": 0.5, "summary": "AI's impact on private credit and software companies is causing market shifts and investor differentiation."}, {"ticker": "UBER", "category": "product_launch", "severity": 0.5, "summary": "Einride, an autonomous EV freight trucking company, went public on the Nasdaq, seeing a significant rise in its stock price on its first day of trading."}, {"ticker": null, "category": "macro_other", "severity": 0.5, "summary": "The 2026 FIFA World Cup is expected to drive significant betting activity and impact the sports-wagering market."}, {"ticker": null, "category": "macro_other", "severity": 0.5, "summary": "Market facing significant tests with inflation data and Oracle's earnings report"}, {"ticker": null, "category": "macro_other", "severity": 0.5, "summary": "Precious metals and stocks decline amid inflation concerns and Fed rate path uncertainty"}, {"ticker": "TSLA", "category": "macro_other", "severity": 0.5, "summary": "SpaceX is set to conduct a high-profile initial public offering with a record-raising sum and a unique pricing mechanism."}, {"ticker": "INTC", "category": "macro_other", "severity": 0.5, "summary": "U.S. House approves $70 billion funding package for immigration enforcement, facing opposition from Democrats"}, {"ticker": "GM", "category": "macro_other", "severity": 0.4, "summary": "General Motors expands efforts in energy storage and EV support to address rising energy costs and AI infrastructure demands"}, {"ticker": "SMCI", "category": "regulatory_action", "severity": 0.5, "summary": "Super Micro announces $7 billion in equity-related financing deals, causing a 13% drop in share price"}, {"ticker": "CRM", "category": "management_change", "severity": 0.4, "summary": "Thoma Bravo's founder discusses how AI is transforming the roles of junior workers within the company."}, {"ticker": null, "category": "macro_other", "severity": 0.5, "summary": "CrowdStrike warns of increasing cyberattacks from China-based entities targeting AI assets of tech companies"}, {"ticker": "BAC", "category": "product_launch", "severity": 0.5, "summary": "Kalshi launches trading on crypto perpetual futures with significant initial trading volume"}, {"ticker": "JPM", "category": "product_launch", "severity": 0.5, "summary": "JPMorgan Chase plans to deploy long-running autonomous AI agents this year."}, {"ticker": null, "category": "macro_other", "severity": 0.4, "summary": "BYD expects China's EV market penetration to reach 80%, contrasting with Nio's view on the industry's future."}, {"ticker": null, "category": "macro_other", "severity": 0.4, "summary": "Startup EDGE Markets raises $29.2 million and launches products for prediction markets and gambling"}, {"ticker": "GS", "category": "macro_other", "severity": 0.4, "summary": "Hong Kong IPOs underperforming despite strong fundraising and listing activity"}, {"ticker": null, "category": "macro_other", "severity": 0.4, "summary": "Investors are rushing into HYPE exchange-traded funds despite the broader crypto market downturn"}, {"ticker": null, "category": "macro_other", "severity": 0.5, "summary": "Strong May jobs report reinforces no interest rate cuts, despite inflation concerns"}, {"ticker": "GS", "category": "macro_other", "severity": 0.4, "summary": "Investor advised to look at emerging markets, particularly Taiwan and South Korea, for AI investment opportunities"}, {"ticker": null, "category": "management_change", "severity": 0.4, "summary": "Tencent hires a former OpenAI researcher as chief AI scientist to focus on AGI development"}, {"ticker": null, "category": "product_launch", "severity": 0.4, "summary": "Kalshi is developing a new interface for its prediction markets platform, likened to the Bloomberg Terminal."}, {"ticker": null, "category": "macro_other", "severity": 0.5, "summary": "Bitcoin prices fall to multi-month lows, traders expect further declines"}, {"ticker": "MS", "category": "macro_other", "severity": 0.4, "summary": "Morgan Stanley plans to integrate AI tools for corporate clients' wealth management, potentially changing user interaction with financial platforms."}, {"ticker": null, "category": "management_change", "severity": 0.4, "summary": "Federal Reserve Chair Kevin Warsh hires two conservative economic policy researchers as temporary contractors"}, {"ticker": null, "category": "macro_other", "severity": 0.3, "summary": "Los Angeles mayoral election with potential impact on local market sentiment"}, {"ticker": "GS", "category": "macro_other", "severity": 0.4, "summary": "Goldman Sachs CEO discusses market optimism and potential for large AI firm IPOs"}, {"ticker": null, "category": "macro_other", "severity": 0.4, "summary": "Polymarket completes first block trade on AI compute infrastructure contract"}, {"ticker": null, "category": "mergers_acquisitions", "severity": 0.8, "summary": "Berkshire Hathaway acquires Taylor Morrison Home for $6.8 billion, expanding its housing business"}], "investment_plan": {"total_amount": 10000.0, "allocations": [{"ticker": "SPY", "amount": 7000.0, "percentage": 70.0, "rationale": "SPY: broad market ETF (S&P 500) for diversified exposure"}, {"ticker": "BND", "amount": 3000.0, "percentage": 30.0, "rationale": "BND: bond ETF for capital preservation and income"}], "risk_summary": "No qualifying bullish signals found; defaulting to diversified ETF allocation.", "expected_return_range": [0.049, 0.091], "time_horizon_months": 12, "rebalance_trigger": "on_new_signal", "disclaimer": "Educational use only. Not investment advice."}};

// ── Boot ──────────────────────────────────────────────────────────────────────

async function init() {
  // Render embedded data instantly — no spinner wait
  hide(elLoading);
  hide(elError);
  renderDashboard(EMBEDDED_DATA);

  // Fetch latest pipeline output and re-render if available
  try {
    const fresh = await fetchLatestOutput();
    if (fresh) renderDashboard(fresh);
  } catch (_) {
    // Silently ignore — embedded data is already shown
  }
}

document.addEventListener('DOMContentLoaded', init);
