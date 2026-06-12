const SUPABASE_URL = 'https://hxluvrvfuxlfjfhombim.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh4bHV2cnZmdXhsZmpmaG9tYmltIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA5MDA5OTYsImV4cCI6MjA5NjQ3Njk5Nn0.OEA8d8u5azHlXkltVsF-DeMYufuJ9iF4QupsRejjIVM';

const db = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const DIRECTION_CLASSES = new Set(['bullish', 'bearish', 'neutral']);

// ── DOM refs ──────────────────────────────────────────────────────────────────
const elLoading       = document.getElementById('loading');
const elError         = document.getElementById('error');
const elErrorMsg      = document.getElementById('error-message');
const elDetail        = document.getElementById('stock-detail');
const elPageTitle     = document.getElementById('page-title');
const elLastUpdated   = document.getElementById('last-updated');
const elHeroTicker    = document.getElementById('hero-ticker');
const elHeroName      = document.getElementById('hero-name');
const elHeroSector    = document.getElementById('hero-sector');
const elHeroSignal    = document.getElementById('hero-signal-wrap');
const elSignalDetail  = document.getElementById('signal-detail');
const elSentChart     = document.getElementById('sentiment-chart');
const elSentEmpty     = document.getElementById('sentiment-empty');
const elSigBody       = document.getElementById('signal-history-body');
const elSigEmpty      = document.getElementById('signal-history-empty');
const elWeightsBars   = document.getElementById('weights-bars');

// ── Helpers ───────────────────────────────────────────────────────────────────
function show(el) { el.hidden = false; }
function hide(el) { el.hidden = true; }

function directionChip(direction) {
  const d = DIRECTION_CLASSES.has((direction || '').toLowerCase()) ? direction.toLowerCase() : 'neutral';
  const span = document.createElement('span');
  span.className = `chip chip-${d}`;
  span.textContent = d.charAt(0).toUpperCase() + d.slice(1);
  return span;
}

function scoreBar(value, min, max, colorClass) {
  const pct = Math.round(((value - min) / (max - min)) * 100);
  const wrap = document.createElement('div');
  wrap.className = 'conf-bar-wrap';
  const bar = document.createElement('div');
  bar.className = `conf-bar ${colorClass}`;
  bar.style.width = `${Math.max(0, Math.min(100, pct))}%`;
  const label = document.createElement('span');
  label.className = 'conf-label';
  label.textContent = value.toFixed(3);
  wrap.appendChild(bar);
  wrap.appendChild(label);
  return wrap;
}

function td(content, className) {
  const cell = document.createElement('td');
  if (className) cell.className = className;
  if (content instanceof Node) cell.appendChild(content);
  else cell.textContent = content != null ? String(content) : '—';
  return cell;
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ── Sparkline chart ───────────────────────────────────────────────────────────
function renderSparkline(container, rows) {
  if (!rows || rows.length === 0) { show(elSentEmpty); return; }
  hide(elSentEmpty);

  const W = container.clientWidth || 600;
  const H = 120;
  const PAD = { top: 16, right: 16, bottom: 32, left: 48 };
  const cW = W - PAD.left - PAD.right;
  const cH = H - PAD.top - PAD.bottom;

  const values = rows.map(r => r.ewma_score);
  const dates  = rows.map(r => r.date);
  const minV = Math.min(...values, -0.1);
  const maxV = Math.max(...values, 0.1);

  const xScale = i => PAD.left + (i / (rows.length - 1 || 1)) * cW;
  const yScale = v => PAD.top + (1 - (v - minV) / (maxV - minV)) * cH;

  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('width', '100%');
  svg.setAttribute('height', H);
  svg.style.overflow = 'visible';

  // Zero line
  if (minV < 0 && maxV > 0) {
    const zeroY = yScale(0);
    const zeroLine = document.createElementNS(ns, 'line');
    zeroLine.setAttribute('x1', PAD.left); zeroLine.setAttribute('x2', PAD.left + cW);
    zeroLine.setAttribute('y1', zeroY);    zeroLine.setAttribute('y2', zeroY);
    zeroLine.setAttribute('stroke', '#30363d'); zeroLine.setAttribute('stroke-dasharray', '4,4');
    svg.appendChild(zeroLine);
  }

  // Area fill
  const areaPoints = values.map((v, i) => `${xScale(i)},${yScale(v)}`).join(' ');
  const areaPath = `M ${PAD.left},${PAD.top + cH} L ${areaPoints.split(' ').join(' L ')} L ${PAD.left + cW},${PAD.top + cH} Z`;
  const area = document.createElementNS(ns, 'path');
  area.setAttribute('d', areaPath);
  area.setAttribute('fill', 'rgba(88,166,255,0.08)');
  svg.appendChild(area);

  // Line
  const linePath = values.map((v, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)},${yScale(v)}`).join(' ');
  const line = document.createElementNS(ns, 'path');
  line.setAttribute('d', linePath);
  line.setAttribute('fill', 'none');
  line.setAttribute('stroke', '#58a6ff');
  line.setAttribute('stroke-width', '2');
  line.setAttribute('stroke-linejoin', 'round');
  svg.appendChild(line);

  // Dots + tooltips
  values.forEach((v, i) => {
    const circle = document.createElementNS(ns, 'circle');
    circle.setAttribute('cx', xScale(i)); circle.setAttribute('cy', yScale(v));
    circle.setAttribute('r', 4);
    circle.setAttribute('fill', v >= 0 ? '#3fb950' : '#f85149');
    circle.setAttribute('stroke', '#161b22'); circle.setAttribute('stroke-width', '2');
    const title = document.createElementNS(ns, 'title');
    title.textContent = `${dates[i]}: ${v.toFixed(3)}`;
    circle.appendChild(title);
    svg.appendChild(circle);
  });

  // X-axis labels (first, mid, last)
  [[0, dates[0]], [Math.floor(rows.length / 2), dates[Math.floor(rows.length / 2)]], [rows.length - 1, dates[rows.length - 1]]]
    .filter(([i]) => dates[i])
    .forEach(([i, d]) => {
      const text = document.createElementNS(ns, 'text');
      text.setAttribute('x', xScale(i)); text.setAttribute('y', H - 4);
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('fill', '#8b949e'); text.setAttribute('font-size', '11');
      text.textContent = d;
      svg.appendChild(text);
    });

  // Y-axis labels
  [minV, 0, maxV].forEach(v => {
    const text = document.createElementNS(ns, 'text');
    text.setAttribute('x', PAD.left - 6); text.setAttribute('y', yScale(v) + 4);
    text.setAttribute('text-anchor', 'end');
    text.setAttribute('fill', '#8b949e'); text.setAttribute('font-size', '11');
    text.textContent = v.toFixed(2);
    svg.appendChild(text);
  });

  container.appendChild(svg);
}

// ── Render weights bars ───────────────────────────────────────────────────────
function renderWeights(weights) {
  elWeightsBars.textContent = '';
  const items = [
    { label: 'Sentiment', key: 'w_sentiment', color: 'bar-high' },
    { label: 'Event',     key: 'w_event',     color: 'bar-mid' },
    { label: 'Price',     key: 'w_price',      color: 'bar-low' },
  ];
  items.forEach(({ label, key, color }) => {
    const val = weights[key] ?? 0;
    const pct = Math.round(val * 100);
    const row = document.createElement('div');
    row.className = 'weight-row';
    const lbl = document.createElement('span');
    lbl.className = 'weight-label';
    lbl.textContent = label;
    const wrap = document.createElement('div');
    wrap.className = 'conf-bar-wrap weight-bar-wrap';
    const bar = document.createElement('div');
    bar.className = `conf-bar ${color}`;
    bar.style.width = `${pct}%`;
    const pctLabel = document.createElement('span');
    pctLabel.className = 'conf-label';
    pctLabel.textContent = `${pct}%`;
    wrap.appendChild(bar);
    wrap.appendChild(pctLabel);
    row.appendChild(lbl);
    row.appendChild(wrap);
    elWeightsBars.appendChild(row);
  });
}

// ── Render signal history table ───────────────────────────────────────────────
function renderSignalHistory(signals) {
  elSigBody.textContent = '';
  if (!signals || signals.length === 0) { show(elSigEmpty); return; }
  hide(elSigEmpty);
  signals.forEach(sig => {
    const tr = document.createElement('tr');
    tr.appendChild(td(formatDate(sig.generated_at)));
    tr.appendChild(td(directionChip(sig.signal)));
    tr.appendChild(td(scoreBar(sig.score ?? 0, -1, 1, sig.score >= 0 ? 'bar-high' : 'bar-low')));
    tr.appendChild(td(scoreBar(sig.confidence ?? 0, 0, 1, 'bar-mid')));
    tr.appendChild(td((sig.components?.sentiment ?? '—').toString(), 'score-cell'));
    tr.appendChild(td((sig.components?.event     ?? '—').toString(), 'score-cell'));
    tr.appendChild(td((sig.components?.price     ?? '—').toString(), 'score-cell'));
    elSigBody.appendChild(tr);
  });
}

// ── Render latest signal detail ───────────────────────────────────────────────
function renderSignalDetail(sig) {
  elSignalDetail.textContent = '';
  if (!sig) {
    elSignalDetail.textContent = 'No signal data available.';
    return;
  }
  const grid = document.createElement('div');
  grid.className = 'signal-detail-grid';

  const items = [
    { label: 'Direction',  value: directionChip(sig.signal) },
    { label: 'Score',      value: `${(sig.score ?? 0).toFixed(3)}` },
    { label: 'Confidence', value: `${Math.round((sig.confidence ?? 0) * 100)}%` },
    { label: 'Horizon',    value: `${sig.horizon_days ?? 5} days` },
    { label: 'Generated',  value: formatDate(sig.generated_at) },
  ];
  items.forEach(({ label, value }) => {
    const cell = document.createElement('div');
    cell.className = 'detail-cell';
    const l = document.createElement('span');
    l.className = 'detail-label';
    l.textContent = label;
    const v = document.createElement('span');
    v.className = 'detail-value';
    if (value instanceof Node) v.appendChild(value);
    else v.textContent = value;
    cell.appendChild(l);
    cell.appendChild(v);
    grid.appendChild(cell);
  });

  // Component breakdown
  if (sig.components) {
    const section = document.createElement('div');
    section.className = 'component-section';
    const heading = document.createElement('p');
    heading.className = 'component-heading';
    heading.textContent = 'Component Breakdown';
    section.appendChild(heading);
    [['Sentiment', sig.components.sentiment], ['Event', sig.components.event], ['Price', sig.components.price]]
      .forEach(([label, val]) => {
        if (val == null) return;
        const row = document.createElement('div');
        row.className = 'weight-row';
        const l = document.createElement('span');
        l.className = 'weight-label';
        l.textContent = label;
        const colorClass = val >= 0.3 ? 'bar-high' : val >= 0 ? 'bar-mid' : 'bar-low';
        row.appendChild(l);
        row.appendChild(scoreBar(Math.abs(val), 0, 1, colorClass));
        section.appendChild(row);
      });
    elSignalDetail.appendChild(grid);
    elSignalDetail.appendChild(section);
  } else {
    elSignalDetail.appendChild(grid);
  }
}

// ── Main fetch + render ───────────────────────────────────────────────────────
async function init() {
  const params = new URLSearchParams(window.location.search);
  const ticker = (params.get('ticker') || '').toUpperCase().trim();

  if (!ticker) {
    elErrorMsg.textContent = 'No ticker specified. Add ?ticker=AAPL to the URL.';
    hide(elLoading); show(elError); return;
  }

  elPageTitle.textContent = ticker;
  document.title = `${ticker} — Sentiment Dashboard`;

  try {
    // Fetch all data in parallel
    const [profileRes, signalsRes, sentimentRes, weightsRes] = await Promise.all([
      db.from('sp500_embeddings').select('ticker, name, sector').eq('ticker', ticker).single(),
      db.from('signals').select('*').eq('ticker', ticker).order('generated_at', { ascending: false }).limit(30),
      db.from('entity_sentiment_ts').select('date, ewma_score, n_articles').eq('ticker', ticker).order('date', { ascending: true }),
      db.from('signal_weights').select('w_sentiment, w_event, w_price, updated_at, signals_evaluated, notes').order('updated_at', { ascending: false }).limit(1),
    ]);

    hide(elLoading);

    // Profile (name + sector) — ok if not found
    const profile = profileRes.data;
    elHeroTicker.textContent = ticker;
    elHeroName.textContent   = profile?.name   || ticker;
    elHeroSector.textContent = profile?.sector || '';

    // Latest signal hero chip
    const signals = signalsRes.data || [];
    if (signals.length > 0) {
      elHeroSignal.appendChild(directionChip(signals[0].signal));
    }

    // Sections
    renderSignalDetail(signals[0] || null);
    renderSignalHistory(signals);
    renderSparkline(elSentChart, sentimentRes.data || []);

    // Weights
    const weights = weightsRes.data?.[0] || { w_sentiment: 0.50, w_event: 0.35, w_price: 0.15 };
    renderWeights(weights);
    const updatedAt = weights.updated_at ? `Weights last updated: ${formatDate(weights.updated_at)}` : '';
    elLastUpdated.textContent = updatedAt;

    show(elDetail);
  } catch (err) {
    hide(elLoading);
    elErrorMsg.textContent = err.message || 'Failed to load stock data.';
    show(elError);
  }
}

document.addEventListener('DOMContentLoaded', init);
