# Stock Sentiment Analyzer

A LangGraph multi-agent system that scans financial news in real-time, detects sentiment and key events, generates investment signals, and produces personalized investment plans — with a self-improving feedback loop that adjusts signal weights based on historical accuracy.

> **Educational use only. Not investment advice.**

---

## High-Level Architecture

```
RSS Feeds (CNBC, MarketWatch, SEC EDGAR 8-K)
        │
        ▼
┌─────────────────┐
│  Agent 1        │  News Ingestion
│  news_ingestion │  feedparser + newspaper4k, SHA-256 dedup, MinHash LSH
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agent 2        │  Entity Recognition
│  entity_recog.  │  spaCy NER + Supabase pgvector → S&P 500 ticker resolution
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agent 3        │  Sentiment Analysis
│  sentiment      │  ProsusAI/FinBERT via HF API, 7-day EWMA per ticker
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agent 4        │  Event Detection
│  event_detect.  │  Mistral-7B via HF API, few-shot JSON classification
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐  ┌──────────────────┐
│ Agent  │  │ Human-in-the-Loop│  high severity → interrupt for review
│  4b    │  │    interrupt()   │
│Earnings│  └────────┬─────────┘
│Sub-Agt │           │
└────┬───┘           │
     └──────┬────────┘
            │
            ▼
┌─────────────────┐
│  Agent 5        │  Signal Generation (deterministic, no LLM)
│  signal_gen.    │  score = w_s×sentiment + w_e×event + w_p×price
│                 │  ← weights read live from Supabase signal_weights table
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agent 6        │  Briefing Report
│  briefing_rpt.  │  Jinja2 Markdown → reports/YYYY-MM-DD_briefing.md
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Agent 7        │  Investment Recommendation
│  recommend.     │  Top 3 S&P 500 signals by confidence, weighted by conviction
└────────┬────────┘
         │
         ▼
    outputs/YYYY-MM-DD.json → docs/latest.json → Dashboard
         │
         ▼
┌─────────────────────────────────────────────────┐
│  Feedback Loop (weekly, every Monday 8am ET)    │
│                                                 │
│  backtesting/engine.py                          │
│    → fetch last 30 days of signals from DB      │
│    → compare against actual yfinance returns    │
│    → compute accuracy per component             │
│                                                 │
│  backtesting/optimizer.py                       │
│    → if ≥ 20 signals: derive new weights        │
│    → if < 20 signals: retain defaults           │
│    → save to signal_weights table in Supabase   │
│                                                 │
│  Next pipeline run picks up updated weights ←──┘
└─────────────────────────────────────────────────┘
```

---

## Agent Breakdown

| # | Agent | File | What it does |
|---|-------|------|-------------|
| 1 | News Ingestion | `agents/news_ingestion.py` | Scrapes 4 RSS feeds, deduplicates via SHA-256 + MinHash LSH, caps at `MAX_ARTICLES_PER_RUN` |
| 2 | Entity Recognition | `agents/entity_recognition.py` | spaCy NER extracts ORG entities, Supabase pgvector resolves them to S&P 500 tickers/sectors |
| 3 | Sentiment Analysis | `agents/sentiment_analysis.py` | FinBERT sentence-level scoring, attention-weighted aggregation, 7-day EWMA per ticker |
| 4 | Event Detection | `agents/event_detection.py` | Mistral-7B classifies events into 8 categories with severity score; triggers interrupt or earnings sub-agent |
| 4b | Earnings Sub-Agent | `agents/earnings_subagent.py` | Extracts EPS/revenue figures, computes beat/miss vs analyst consensus |
| 5 | Signal Generation | `agents/signal_generation.py` | Reads live weights from Supabase, computes composite score → bullish/bearish/neutral + confidence |
| 6 | Briefing Report | `agents/briefing_report.py` | Jinja2 daily Markdown briefing with signals, events, heatmap commentary |
| 7 | Investment Rec. | `agents/recommendation.py` | Top 3 S&P 500 stocks by confidence, allocated proportionally by conviction |

---

## Signal Scoring Formula

Weights are dynamic — read from Supabase `signal_weights` table on every run and updated weekly by the optimizer.

```
score = w_sentiment × sentiment_ewma        (default: 0.50)
      + w_event     × event_severity_weight  (default: 0.35, signed by event polarity)
      + w_price     × price_zscore           (default: 0.15, 5-day return vs 30-day σ)

bullish  if score >  0.25
bearish  if score < -0.25
neutral  otherwise

confidence = min(1.0, |score| × agreement_factor)
```

---

## Feedback Loop

The optimizer runs every **Monday 8am ET** via GitHub Actions:

1. Fetches all signals generated in the last 30 days from Supabase
2. Downloads actual forward prices from Yahoo Finance (14-day horizon)
3. Checks whether each component (sentiment/event/price) agreed with the actual price move
4. Derives new component weights proportional to their individual accuracy
5. Saves updated weights to `signal_weights` table — pipeline picks them up on next run

**Minimum data requirement:** 20 signals needed before weights are adjusted. Below that threshold, defaults (0.50/0.35/0.15) are retained and logged as "sparse data".

---

## LangGraph Routing

```
news_ingestion
    │ no articles → END
    ▼
entity_recognition
    │ no entities → END
    ▼
sentiment_analysis → event_detection
                          │ earnings_report → earnings_subagent ─┐
                          │ high severity   → human_review ──────┤
                          │ otherwise ────────────────────────────┤
                                                                   ▼
                                                          signal_generation
                                                          (reads weights from DB)
                                                                   │
                                                          briefing_report
                                                                   │
                                                          recommendation → END
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Orchestration | LangGraph `StateGraph` + `MemorySaver` |
| Sentiment LLM | ProsusAI/FinBERT via HuggingFace Inference API |
| Event LLM | Mistral-7B-Instruct-v0.2 via HuggingFace Inference API |
| NER | spaCy `en_core_web_sm` |
| Vector DB | Supabase pgvector (503 S&P 500 company embeddings) |
| Relational DB | Supabase Postgres (`signals`, `articles`, `entity_sentiment_ts`, `signal_weights`) |
| News sources | CNBC, MarketWatch, SEC EDGAR 8-K (feedparser + newspaper4k) |
| Price data | yfinance |
| Backtesting | Custom engine — directional accuracy, Sharpe ratio, max drawdown |
| Weight optimizer | `backtesting/optimizer.py` — weekly adaptive reweighting |
| Dashboard | GitHub Pages (vanilla HTML/JS), reads `docs/latest.json` |
| CI/CD | GitHub Actions — every 3 hours market hours (9am/12pm/3pm ET weekdays) |

---

## Project Structure

```
stockSentimentAnalysis/
├── agents/                  # All 8 agent node functions
│   ├── news_ingestion.py
│   ├── entity_recognition.py
│   ├── sentiment_analysis.py
│   ├── event_detection.py
│   ├── earnings_subagent.py
│   ├── signal_generation.py
│   ├── briefing_report.py
│   └── recommendation.py
├── graph/
│   ├── builder.py           # LangGraph StateGraph wiring
│   └── router.py            # Conditional edge routing functions
├── models/                  # Pydantic data models
├── storage/
│   └── supabase_store.py    # Supabase client — signals, weights, embeddings
├── backtesting/
│   ├── engine.py            # Backtest signals vs yfinance forward returns
│   ├── metrics.py           # Directional accuracy, Sharpe, drawdown
│   ├── optimizer.py         # Weekly weight optimizer (feedback loop)
│   └── report.py
├── scripts/
│   └── run_optimizer.py     # Entrypoint for GHA weight optimization job
├── config/
│   ├── settings.py          # pydantic-settings, all env vars
│   └── feeds.py             # RSS feed URLs
├── docs/                    # GitHub Pages dashboard
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   ├── latest.json          # Written by pipeline after every run
│   └── dashboard/           # Alternate dashboard view
├── outputs/                 # Full pipeline output JSON (committed by GHA)
├── .github/workflows/
│   └── pipeline.yml         # Scheduled (3h market hours) + manual + weekly optimizer
└── main.py                  # CLI entry point
```

---

## Guardrails & Evals

No separate eval framework — guardrails are built directly into the pipeline:

| Layer | What | Where |
|---|---|---|
| **Pydantic bounds** | All signal fields validated at model creation — score `[-1,1]`, confidence `[0,1]`, severity `[0,1]`, allocation `[0,100]` | `models/signal.py`, `models/event.py`, `models/recommendation.py` |
| **Score clamping** | Signal score and price z-score hard-clamped to `[-1, 1]` before storage | `agents/signal_generation.py` |
| **Sentiment clamping** | EWMA sentiment score forced to `[-1, 1]` | `models/sentiment.py` |
| **LLM output repair** | Mistral bad JSON triggers a second repair attempt before the event is dropped | `agents/event_detection.py` |
| **CAPTCHA / JS-wall detection** | Blocked article pages detected by keyword scan and skipped — falls back to RSS summary | `agents/news_ingestion.py` |
| **Human-in-the-loop** | Events with severity ≥ `high_severity_threshold` pause the pipeline and require manual approval before signal generation | `graph/router.py`, `agents/event_detection.py` |
| **Sparse data guard** | Optimizer skips weight update and retains defaults when fewer than 20 signals available in the backtest window | `backtesting/optimizer.py` |
| **Secret validation** | CI fails immediately if `HF_TOKEN`, `SUPABASE_URL`, or `SUPABASE_KEY` are missing | `.github/workflows/pipeline.yml` |
| **S&P 500 universe filter** | Investment plan only suggests tickers present in `sp500_embeddings` — non-index stocks are excluded | `agents/recommendation.py` |

---

## Supabase Schema

| Table | Purpose |
|---|---|
| `articles` | Deduplicated news articles across runs |
| `signals` | Generated investment signals with components |
| `entity_sentiment_ts` | Per-ticker EWMA sentiment history |
| `sp500_embeddings` | 503 S&P 500 companies (ticker, name, sector, embedding) |
| `signal_weights` | Historical weight snapshots — pipeline always reads latest row |

---

## Setup

### 1. Install dependencies

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m spacy download en_core_web_sm
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in: HF_TOKEN, SUPABASE_URL, SUPABASE_KEY, EDGAR_USER_AGENT
```

### 3. Supabase is pre-configured

All tables and the full S&P 500 universe (503 companies) are already seeded. No manual SQL setup required.

---

## Usage

```bash
# Basic run
python main.py

# Interactive mode with investment plan
python main.py --interactive --amount 10000 --risk moderate --horizon 12

# Backtest signals against actual price movements
python main.py --backtest --start 2024-01-01 --end 2025-01-01

# Resume from checkpoint
python main.py --thread-id my-session
```

---

## GitHub Actions Pipeline

| Job | Schedule | What it does |
|---|---|---|
| `run-pipeline` | Weekdays 9am, 12pm, 3pm ET | Full news → signals → plan → commits `latest.json` |
| `optimize-weights` | Every Monday 8am ET | Backtests last 30 days, updates signal weights in Supabase |

Trigger manually: **Actions → Financial News Sentiment Pipeline → Run workflow**

Required secrets: `HF_TOKEN`, `SUPABASE_URL`, `SUPABASE_KEY`

---

## Dashboard

Live at GitHub Pages. Reads `docs/latest.json` — updated automatically after every pipeline run.

Shows: investment signals, detected events, and top 3 S&P 500 investment recommendations.

---

*Educational use only. Not investment advice. Always do your own research.*
