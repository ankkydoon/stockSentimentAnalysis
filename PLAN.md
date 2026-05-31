# Financial News Sentiment Analyzer — Full Project Plan

## Overview

A LangGraph multi-agent system that scans financial news in real-time, detects sentiment and key events, generates investment signals, recommends personalized investment plans, and validates performance against real stock data.

**Goal:** Give retail investors the same market intelligence as institutional investors — for free.

---

## System Architecture: 7 Agents + 2 Modules

```
News → [Agent 1: Ingestion] → [Agent 2: NER] → [Agent 3: Sentiment]
     → [Agent 4: Event Detection] → [Agent 5: Signal Generation]
     → [Agent 6: Investment Recommendation] → [Module: Backtesting]
     + [Module: FinBERT Fine-tuning Pipeline]
```

---

## Project Structure

```
stockSentimentAnalysis/
├── pyproject.toml
├── .env.example
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── feeds.py
├── models/
│   ├── __init__.py
│   ├── article.py
│   ├── entity.py
│   ├── sentiment.py
│   ├── event.py
│   ├── signal.py
│   └── recommendation.py        # NEW: InvestmentPlan, UserProfile
├── state/
│   ├── __init__.py
│   └── graph_state.py
├── agents/
│   ├── __init__.py
│   ├── news_ingestion.py
│   ├── entity_recognition.py
│   ├── sentiment_analysis.py
│   ├── event_detection.py
│   ├── signal_generation.py
│   └── recommendation.py        # NEW: Agent 6
├── graph/
│   ├── __init__.py
│   ├── builder.py
│   └── router.py
├── storage/
│   ├── __init__.py
│   ├── sqlite_store.py
│   └── chroma_store.py
├── backtesting/                  # NEW
│   ├── __init__.py
│   ├── engine.py
│   ├── metrics.py
│   └── report.py
├── training/                     # NEW: FinBERT fine-tuning
│   ├── __init__.py
│   ├── dataset.py
│   ├── trainer.py
│   └── evaluate.py
├── scripts/
│   ├── seed_sp500_profiles.py
│   └── collect_training_data.py  # NEW
└── main.py
```

---

## Part 1: Core Pipeline (Agents 1–5)

### Step 1: Project scaffolding
- `pyproject.toml` with all dependencies
- `.env.example` with all tunable env vars
- All `__init__.py` and `data/` placeholder

### Step 2: Config layer
- `config/settings.py` — pydantic-settings, all knobs (dedup threshold, trend days, severity threshold, model IDs, paths)
- `config/feeds.py` — Yahoo Finance, MarketWatch, SEC EDGAR 8-K + 10-Q RSS feeds

### Step 3: Pydantic data models
- `models/article.py` — `Article`: id (SHA-256 of URL), url, title, body, source, published_at, minhash_signature, is_duplicate
- `models/entity.py` — `Entity` + `EntityProfile` for ChromaDB
- `models/sentiment.py` — `SentimentScore` (per entity/article) + `TrendWindow` (7-day rolling per ticker)
- `models/event.py` — `EventCategory` enum + `Event` with severity [0,1]
- `models/signal.py` — `InvestmentSignal` with direction (bullish/bearish/neutral), confidence, contribution scores

### Step 4: LangGraph state schema
`state/graph_state.py` — `GraphState` TypedDict:
- `raw_articles`, `deduplicated_articles`
- `article_entities`, `unique_entities`
- `sentiment_scores`, `trend_windows`
- `events`, `signals`, `pending_human_review`
- `investment_plan` (NEW)
- `backtest_results` (NEW)
- `requires_interrupt`, `human_review_decision`
- `error_log: Annotated[list[str], operator.add]`

### Step 5: Storage layer
- `storage/sqlite_store.py` — articles + signals + recommendations tables
- `storage/chroma_store.py` — PersistentClient + all-MiniLM-L6-v2 for S&P 500 profiles

### Step 6: Agent 1 — News Ingestion
- feedparser → newspaper3k for full article body
- Dedup: SQLite SHA-256 (cross-run) + MinHashLSH 5-shingles threshold=0.85 (in-run)
- Cap: MAX_ARTICLES_PER_RUN=50

### Step 7: Agent 2 — Entity Recognition
- spaCy en_core_web_lg NER on title + body[:2000]
- ChromaDB semantic match, score ≥ 0.6 → resolved ticker/sector

### Step 8: Agent 3 — Sentiment Analysis
- ProsusAI/finbert with output_attentions=True
- Entity-focused attention weighting per article
- TrendWindow per ticker: avg pos/neg/neutral + trend_direction

### Step 9: Agent 4 — Event Detection
- Mistral-7B via Ollama, temperature=0.0
- Few-shot: earnings / M&A / litigation / macro examples
- severity ≥ 0.8 → requires_human_review

### Step 10: Agent 5 — Signal Generation
- Composite = 0.40×sentiment + 0.35×event + 0.25×price_momentum
- Direction: bullish >0.1, bearish <-0.1, else neutral
- LangGraph interrupt() for high-severity signals

---

## Part 2: Investment Recommendation Engine (Agent 6)

### What it does
Takes user inputs + signals → personalized investment plan with allocation, timeline, and risk analysis.

### User inputs
```python
class UserProfile(BaseModel):
    investment_amount: float        # e.g. 10000.0 (USD)
    risk_appetite: str              # "conservative" | "moderate" | "aggressive"
    time_horizon_months: int        # e.g. 6, 12, 24, 60
    preferred_sectors: list[str]    # e.g. ["tech", "healthcare"] or []
    exclude_tickers: list[str]      # e.g. ["TSLA"] or []
```

### Output
```python
class InvestmentPlan(BaseModel):
    total_amount: float
    allocations: list[Allocation]   # ticker, amount, %, rationale
    risk_summary: str
    expected_return_range: tuple[float, float]   # e.g. (5.0, 15.0) percent
    time_horizon_months: int
    rebalance_trigger: str          # "monthly" | "on new signal"
    disclaimer: str
```

### Logic (agents/recommendation.py)
1. Filter signals: bullish only, confidence ≥ 0.6, match preferred sectors, exclude tickers
2. Risk-tier bucketing:
   - Conservative: top 3 signals, 60% large-cap ETFs + 40% individual stocks
   - Moderate: top 5 signals, 40% ETFs + 60% individual stocks
   - Aggressive: top 7 signals, 100% individual stocks
3. Allocation weighting: proportional to signal confidence score
4. Expected return estimate: use 12-month yfinance historical average return for each ticker as baseline, scaled by signal direction
5. Persist plan to SQLite

### Step 11: models/recommendation.py
- `UserProfile`, `Allocation`, `InvestmentPlan` Pydantic models

### Step 12: agents/recommendation.py
- Receives signals + user_profile from GraphState
- Returns investment_plan

---

## Part 3: Performance Backtesting Module

### What it does
Compares our historical signals against actual stock price movements to measure system accuracy.

### How it works
- For each past signal stored in SQLite: fetch actual price at signal date and N days later via yfinance
- Calculate: was the signal correct? By how much?
- Aggregate metrics across all signals

### Metrics (backtesting/metrics.py)
```
Directional Accuracy     = % of signals where direction matched actual price move
Precision (Bullish)      = true bullish / total bullish signals
Precision (Bearish)      = true bearish / total bearish signals
Mean Return (followed)   = avg actual return if you followed all signals
Sharpe Ratio             = mean_return / std_return × sqrt(252)
Max Drawdown             = worst peak-to-trough over backtest period
Hit Rate by Sector       = accuracy broken down by sector
Hit Rate by Event Type   = accuracy broken down by event category
```

### Step 13: backtesting/engine.py
- `BacktestEngine.run(start_date, end_date, forward_days=14)`
- Loads signals from SQLite, fetches prices via yfinance batch download
- Computes all metrics

### Step 14: backtesting/report.py
- Outputs a text/JSON summary table
- Optional: matplotlib chart of cumulative returns vs S&P 500 benchmark

### Step 15: GraphState integration
- Add `--backtest` CLI flag to main.py
- If set, run BacktestEngine after pipeline and append results to output

---

## Part 4: FinBERT Fine-tuning (2019–2026)

### Why fine-tune?
ProsusAI/finbert was trained on pre-2019 data. It may underperform on:
- Post-COVID market language (meme stocks, crypto contagion, rate pivot)
- Modern analyst terminology
- Your specific RSS feed writing style

### Training data sources
1. **Financial PhraseBank** — ~5000 labeled sentences (positive/negative/neutral)
2. **FiQA sentiment dataset** — financial news + opinion sentiment
3. **SEntFiN** — financial news headlines with fine-grained labels
4. **Self-collected** — labeled from our own RSS pipeline (human review decisions become training labels over time)

### Label format
3-class: `positive`, `negative`, `neutral` — consistent with base FinBERT output

### Step 16: scripts/collect_training_data.py
- Downloads Financial PhraseBank + FiQA + SEntFiN from HuggingFace datasets
- Merges into unified JSONL format: `{"text": "...", "label": "positive"}`
- Splits: 80% train, 10% val, 10% test

### Step 17: training/dataset.py
- `FinBERTDataset(Dataset)` — loads JSONL, tokenizes with `AutoTokenizer`
- Handles class imbalance with weighted sampler

### Step 18: training/trainer.py
- `FineTuner` class using HuggingFace `Trainer` API
- Base model: `ProsusAI/finbert`
- Training config: lr=2e-5, batch=16, epochs=3, warmup_steps=100
- Saves best checkpoint to `models/finbert-finetuned/`

### Step 19: training/evaluate.py
- Runs inference on test split
- Reports: accuracy, F1 per class, confusion matrix
- Compares fine-tuned vs base FinBERT on same test set

### Integration
- After fine-tuning, update `settings.py`: `FINBERT_MODEL_ID = "models/finbert-finetuned"`
- Agent 3 loads from this path automatically

---

## Part 5: Graph Wiring + Entry Point

### Step 20: Graph (graph/)
- `router.py` — skip to END if no articles after ingestion; skip to END if no entities after NER
- `builder.py` — node sequence:
  ```
  news_ingestion → entity_recognition → sentiment_analysis 
  → event_detection → signal_generation → recommendation → END
  ```
- Compile with `MemorySaver` checkpointer

### Step 21: ChromaDB seed (scripts/seed_sp500_profiles.py)
- Wikipedia S&P 500 list → yfinance enrichment → ChromaDB upsert
- Rate-limit: 1s sleep every 10 tickers

### Step 22: Entry point (main.py)
CLI args: `--interactive`, `--thread-id`, `--backtest`, `--amount`, `--risk`, `--horizon`

```
python main.py --interactive --amount 10000 --risk moderate --horizon 12
python main.py --backtest --start 2024-01-01 --end 2025-01-01
```

Flow:
1. Parse args → build UserProfile
2. Initialize GraphState, run graph.invoke()
3. Handle interrupt for human review
4. Print signal summary table
5. Print investment plan allocation table
6. If --backtest: print accuracy metrics vs S&P 500

---

## Verification Steps

1. `pip install -e .` — clean install
2. `python -m spacy download en_core_web_lg`
3. `ollama pull mistral` + verify with `ollama list`
4. `python -m scripts.seed_sp500_profiles` — logs ~500 companies indexed
5. `python main.py` — articles → entities → sentiment → events → signals
6. `python main.py --interactive --amount 10000 --risk moderate --horizon 12` — shows investment plan
7. `python main.py --backtest` — shows directional accuracy vs benchmark
8. Human interrupt test: set `HIGH_IMPACT_SEVERITY_THRESHOLD=0.1` → pauses for review
9. Dedup test: run twice → second run logs 0 new articles
10. Fine-tune: `python -m training.trainer` → compare base vs fine-tuned F1

---

## Full Dependency List

```toml
[dependencies]
langgraph>=0.2.0
langchain-core>=0.3.0
transformers>=4.40.0
torch>=2.2.0
spacy>=3.7.0
sentence-transformers>=3.0.0
chromadb>=0.5.0
feedparser>=6.0.0
newspaper3k>=0.2.8
lxml[html_clean]>=5.0.0
datasketch>=1.6.0
yfinance>=0.2.40
pandas>=2.1.0
ollama>=0.2.0
pydantic>=2.7.0
pydantic-settings>=2.2.0
datasets>=2.19.0          # for fine-tuning data
scikit-learn>=1.4.0       # for metrics
matplotlib>=3.8.0         # for backtest charts
```

---

## Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| LLM backend | Ollama (local) | No API cost, privacy, offline capable |
| Sentiment model | FinBERT + fine-tune | Domain-specific, attention weighting possible |
| Vector DB | ChromaDB | Persistent, no external service needed |
| Orchestration | LangGraph | Native interrupt/resume, state management |
| Storage | SQLite | Lightweight, no infra, signals become backtest data |
| Backtesting | yfinance | Free, reliable historical OHLCV |

---

*Built for retail investors. No financial advice — always do your own research.*
