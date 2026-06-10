# Stock Sentiment Analyzer

A LangGraph multi-agent system that scans financial news in real-time, detects sentiment and key events, generates investment signals, and produces personalized investment plans — giving retail investors institutional-grade market intelligence for free.

> **Educational use only. Not investment advice.**

---

## High-Level Architecture

```
RSS Feeds (Yahoo Finance, MarketWatch, SEC EDGAR)
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
│  entity_recog.  │  spaCy NER + ChromaDB/Supabase pgvector → S&P 500 ticker resolution
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
│  signal_gen.    │  score = 0.50×sentiment + 0.35×event + 0.15×price momentum
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
│  recommend.     │  Risk-tiered allocation plan from signals + user profile
└────────┬────────┘
         │
         ▼
    outputs/YYYY-MM-DD.json
```

---

## Agent Breakdown

| # | Agent | File | What it does |
|---|-------|------|-------------|
| 1 | News Ingestion | `agents/news_ingestion.py` | Scrapes RSS feeds, deduplicates via SHA-256 + MinHash LSH, caps at `MAX_ARTICLES_PER_RUN` |
| 2 | Entity Recognition | `agents/entity_recognition.py` | spaCy NER extracts ORG entities, Supabase pgvector resolves them to S&P 500 tickers/sectors |
| 3 | Sentiment Analysis | `agents/sentiment_analysis.py` | FinBERT sentence-level scoring, attention-weighted aggregation, 7-day EWMA per ticker |
| 4 | Event Detection | `agents/event_detection.py` | Mistral-7B classifies events into 8 categories with severity score; triggers interrupt or earnings sub-agent |
| 4b | Earnings Sub-Agent | `agents/earnings_subagent.py` | Extracts EPS/revenue figures, computes beat/miss vs analyst consensus |
| 5 | Signal Generation | `agents/signal_generation.py` | Deterministic composite score → bullish/bearish/neutral + confidence |
| 6 | Briefing Report | `agents/briefing_report.py` | Jinja2 daily Markdown briefing with signals, events, heatmap commentary |
| 7 | Investment Rec. | `agents/recommendation.py` | Risk-tiered portfolio allocation (conservative/moderate/aggressive) from signals |

---

## Signal Scoring Formula

```
score = 0.50 × sentiment_ewma
      + 0.35 × event_severity_weight   (signed by event polarity)
      + 0.15 × price_zscore            (5-day return vs 30-day σ)

bullish  if score >  0.25
bearish  if score < -0.25
neutral  otherwise

confidence = min(1.0, |score| × agreement_factor)
```

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
| Embeddings | `all-MiniLM-L6-v2` via HuggingFace |
| NER | spaCy |
| Vector DB | Supabase pgvector |
| Relational DB | Supabase (Postgres) |
| News scraping | feedparser + newspaper4k |
| Price data | yfinance |
| Dashboard | GitHub Pages (vanilla HTML/JS) |
| CI/CD | GitHub Actions |

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
├── state/
│   └── graph_state.py       # GraphState TypedDict
├── storage/
│   └── supabase_store.py    # Supabase client (graceful no-op if unconfigured)
├── backtesting/             # Signal accuracy vs yfinance forward returns
│   ├── engine.py
│   ├── metrics.py
│   └── report.py
├── training/                # FinBERT fine-tuning pipeline
├── config/
│   ├── settings.py          # pydantic-settings, all env vars
│   └── feeds.py             # RSS feed URLs
├── dashboard/               # GitHub Pages frontend
│   ├── index.html
│   ├── app.js
│   └── style.css
├── reports/                 # Generated briefing Markdown files
├── outputs/                 # Pipeline output JSON (committed by GHA)
├── scripts/
│   └── seed_sp500_profiles.py
├── .github/workflows/
│   └── pipeline.yml         # Scheduled + manual GHA pipeline
└── main.py                  # CLI entry point
```

---

## Setup

### 1. Install dependencies

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in: HF_TOKEN, SUPABASE_URL, SUPABASE_KEY, EDGAR_USER_AGENT
```

### 3. Initialize Supabase (run once)

In Supabase SQL Editor:
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE articles (id TEXT PRIMARY KEY, url TEXT, title TEXT, source TEXT, published_at TIMESTAMPTZ, is_duplicate BOOL);
CREATE TABLE signals (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), ticker TEXT, signal TEXT, confidence FLOAT, score FLOAT, components JSONB, evidence_ids TEXT[], generated_at TIMESTAMPTZ, horizon_days INT DEFAULT 5);
CREATE TABLE sp500_embeddings (ticker TEXT PRIMARY KEY, name TEXT, sector TEXT, summary TEXT, embedding vector(384));

CREATE INDEX ON sp500_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON signals (ticker, generated_at DESC);
```

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

Runs automatically on weekdays at 9am ET. Trigger manually via:

**Actions tab → Financial News Sentiment Pipeline → Run workflow**

Required secrets: `HF_TOKEN`, `SUPABASE_URL`, `SUPABASE_KEY`

---

## Dashboard

Enable GitHub Pages: **Settings → Pages → Source: main branch, `/dashboard` folder**

The dashboard reads the latest `outputs/` JSON via GitHub Contents API and renders signals, events, and investment plan in real-time.

---

## Backtesting

```bash
python main.py --backtest --start 2024-01-01 --end 2025-01-01
```

Metrics reported: directional accuracy, precision (bullish/bearish), mean return, Sharpe ratio, max drawdown, hit rate by sector and event type.

---

*Educational use only. Not investment advice. Always do your own research.*
