# P7: Dashboard (GitHub Pages) + GitHub Actions Workflow

> **For agentic workers:** Use subagent-driven-development to implement task-by-task.

**Goal:** Static GitHub Pages dashboard showing latest pipeline output with date picker + GHA workflow running pipeline on weekdays 9am ET.

**Architecture:** `dashboard/index.html` + `dashboard/app.js` reads `outputs/YYYY-MM-DD.json` via GitHub Contents API. GHA workflow runs `main.py` and commits output JSON.

**Tech Stack:** Vanilla HTML/JS, GitHub Actions, GitHub Contents API

---

### Task 1: dashboard/index.html + app.js

**Files:**
- Create: `dashboard/index.html`
- Create: `dashboard/app.js`

- [ ] **Step 1: Create dashboard/index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Financial Sentiment Dashboard</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
    h1 { font-size: 1.5rem; }
    #stale-banner { background: #fff3cd; border: 1px solid #ffc107; padding: 0.75rem 1rem; border-radius: 4px; margin-bottom: 1rem; display: none; }
    table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
    th, td { text-align: left; padding: 0.5rem; border-bottom: 1px solid #ddd; }
    th { background: #f5f5f5; }
    .bullish { color: #2d8a2d; font-weight: bold; }
    .bearish { color: #c0392b; font-weight: bold; }
    .neutral { color: #888; }
    footer { margin-top: 2rem; font-size: 0.8rem; color: #888; border-top: 1px solid #eee; padding-top: 1rem; }
    select { padding: 0.4rem; font-size: 1rem; }
  </style>
</head>
<body>
  <h1>Financial News Sentiment Dashboard</h1>
  <div id="stale-banner">⚠️ Data may be stale — last updated <span id="last-updated"></span></div>
  <label for="date-picker">Select run date: </label>
  <select id="date-picker"></select>
  <div id="content"></div>
  <footer>Educational use only. Not investment advice.</footer>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create dashboard/app.js**

```javascript
const REPO = 'YOUR_GITHUB_USERNAME/stockSentimentAnalysis';
const API_BASE = `https://api.github.com/repos/${REPO}/contents/outputs`;

async function fetchJson(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

async function listOutputDates() {
  const files = await fetchJson(API_BASE);
  return files
    .filter(f => f.name.match(/^\d{4}-\d{2}-\d{2}\.json$/))
    .map(f => f.name.replace('.json', ''))
    .sort()
    .reverse();
}

async function loadOutput(date) {
  const meta = await fetchJson(`${API_BASE}/${date}.json`);
  const content = JSON.parse(atob(meta.content));
  return content;
}

function checkStale(runDate) {
  const last = new Date(runDate);
  const now = new Date();
  const hours = (now - last) / 3600000;
  if (hours > 24) {
    document.getElementById('stale-banner').style.display = 'block';
    document.getElementById('last-updated').textContent = runDate;
  }
}

function renderSignals(signals) {
  if (!signals || signals.length === 0) return '<p>No signals generated.</p>';
  const rows = [...signals]
    .sort((a, b) => b.confidence - a.confidence)
    .map(s => `<tr>
      <td>${s.ticker}</td>
      <td class="${s.direction}">${s.direction}</td>
      <td>${(s.confidence * 100).toFixed(1)}%</td>
      <td>${s.score.toFixed(3)}</td>
    </tr>`).join('');
  return `<h2>Signals</h2>
    <table><thead><tr><th>Ticker</th><th>Direction</th><th>Confidence</th><th>Score</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function renderPlan(plan) {
  if (!plan || !plan.allocations || plan.allocations.length === 0) return '';
  const rows = plan.allocations.map(a => `<tr>
    <td>${a.ticker}</td>
    <td>$${a.amount.toFixed(2)}</td>
    <td>${a.percentage.toFixed(1)}%</td>
    <td>${a.rationale}</td>
  </tr>`).join('');
  return `<h2>Investment Plan</h2>
    <p>${plan.risk_summary}</p>
    <table><thead><tr><th>Ticker</th><th>Amount</th><th>%</th><th>Rationale</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

async function init() {
  const picker = document.getElementById('date-picker');
  const content = document.getElementById('content');
  try {
    const dates = await listOutputDates();
    if (dates.length === 0) {
      content.innerHTML = '<p>No pipeline outputs found yet.</p>';
      return;
    }
    dates.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d; opt.textContent = d;
      picker.appendChild(opt);
    });
    async function loadDate(date) {
      content.innerHTML = '<p>Loading...</p>';
      try {
        const data = await loadOutput(date);
        checkStale(data.run_date);
        content.innerHTML = renderSignals(data.signals) + renderPlan(data.investment_plan);
      } catch (e) {
        content.innerHTML = `<p>Error loading data: ${e.message}</p>`;
      }
    }
    picker.addEventListener('change', e => loadDate(e.target.value));
    await loadDate(dates[0]);
  } catch (e) {
    content.innerHTML = `<p>Error: ${e.message}</p>`;
  }
}

init();
```

- [ ] **Step 3: Update REPO constant in app.js**

Replace `YOUR_GITHUB_USERNAME/stockSentimentAnalysis` with the actual repo path.

- [ ] **Step 4: Commit**

```bash
git add dashboard/
git commit -m "feat: GitHub Pages dashboard with date picker and stale data banner"
```

---

### Task 2: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/pipeline.yml`

- [ ] **Step 1: Create .github/workflows/pipeline.yml**

```yaml
name: Financial News Pipeline

on:
  schedule:
    - cron: '0 14 * * 1-5'  # 9am ET (UTC-5) weekdays
  workflow_dispatch:
    inputs:
      risk:
        description: 'Risk appetite'
        required: false
        default: 'moderate'
        type: choice
        options: [conservative, moderate, aggressive]
      amount:
        description: 'Investment amount (USD)'
        required: false
        default: '10000'

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    steps:
      - name: Validate secrets
        run: |
          if [ -z "${{ secrets.HF_TOKEN }}" ]; then echo "HF_TOKEN missing"; exit 1; fi
          if [ -z "${{ secrets.SUPABASE_URL }}" ]; then echo "SUPABASE_URL missing"; exit 1; fi
          if [ -z "${{ secrets.SUPABASE_KEY }}" ]; then echo "SUPABASE_KEY missing"; exit 1; fi

      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -e .

      - name: Run pipeline
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          EDGAR_USER_AGENT: "stockSentimentAnalysis/1.0 ${{ secrets.CONTACT_EMAIL }}"
        run: |
          python main.py \
            --risk ${{ inputs.risk || 'moderate' }} \
            --amount ${{ inputs.amount || '10000' }}

      - name: Commit output
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add outputs/
          git diff --cached --quiet || git commit -m "chore: pipeline output $(date -u +%Y-%m-%d)"
          git push
```

- [ ] **Step 2: Commit**

```bash
mkdir -p .github/workflows
git add .github/workflows/pipeline.yml
git commit -m "feat: GitHub Actions pipeline workflow (weekdays 9am ET + workflow_dispatch)"
```

---

## P7 Done

Verify by:
1. Push to `main` and enable GitHub Pages in repo Settings → Pages → Source: `dashboard/` folder
2. Manually trigger `workflow_dispatch` from the Actions tab
3. Check `outputs/` for a committed JSON file
4. Open GitHub Pages URL — dashboard should load the latest run
