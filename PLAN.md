# Financial News Sentiment Analyzer — Full Project Plan

## Overview

A LangGraph multi-agent system that scans financial news in real-time, detects sentiment and key events, generates investment signals, recommends personalized investment plans, and validates performance against real stock data.

**Goal:** Give retail investors the same market intelligence as institutional investors — for free.

---

## System Architecture: 8 Agents + 2 Modules

```
News → [Agent 1: Ingestion] → [Agent 2: NER] → [Agent 3: Sentiment]
     → [Agent 4: Event Detection] → [Agent 4b: Earnings Sub-Agent]
     → [Agent 5: Signal Generation] → [Agent 6: Briefing Report]
     → [Agent 7: Investment Recommendation] → [Module: Backtesting]
     + [Module: FinBERT Fine-tuning Pipeline]
```

**LangGraph routing:**
- `severity == high` → Human-in-the-Loop interrupt → Signal Generation
- `category == earnings_report` → Earnings Sub-Agent → Signal Generation
- all others → Signal Generation directly

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
│   ├── earnings_subagent.py         # NEW: dedicated earnings handler
│   ├── signal_generation.py
│   ├── briefing_report.py           # NEW: Agent 6 Jinja2 briefing
│   └── recommendation.py            # Agent 7
├── reports/
│   ├── __init__.py
│   └── sample_briefing.md           # NEW: sample output
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
- `storage/chroma_store.py` — PersistentClient + all-MiniLM-L6-v2. Three collections:
  - `sp500_companies` — name, ticker, sector, 200-word business summary
  - `sectors` — GICS sector definitions and event sensitivities
  - `fin_glossary` — ~400 financial terms (EPS, EBITDA, guidance, etc.)

### Step 6: Agent 1 — News Ingestion
- feedparser → newspaper3k for full article body
- Dedup: SQLite SHA-256 (cross-run) + MinHashLSH 5-shingles threshold=0.85 (in-run)
- Cap: MAX_ARTICLES_PER_RUN=50

### Step 7: Agent 2 — Entity Recognition
- spaCy `dslim/bert-base-NER` for PER/ORG + custom regex+gazetteer for ticker patterns (`$AAPL`, `(NASDAQ: AAPL)`)
- ChromaDB semantic match against `sp500_companies`, score ≥ 0.72 → resolved ticker/sector
- Corroboration rule: require at least one financial cue (ticker symbol, `$`, "shares", "Inc.") before linking common-word tickers (e.g. "Target", "Ford")
- Unlinked entities kept for observability but excluded from signals

### Step 8: Agent 3 — Sentiment Analysis
- ProsusAI/finbert, sentence-level via spaCy sentencizer
- Aggregation: attention weight = entity mention count × FinBERT softmax confidence (proxy weighting — not raw transformer attention, which is unreliable for interpretability)
- 7-day EWMA per ticker stored in SQLite `entity_sentiment_ts` table
- Output: `EntitySentiment{ticker, score ∈ [-1,1], label, n_sentences, window_ewma}`

### Step 9: Agent 4 — Event Detection
- Mistral-7B-Instruct-v0.2 via Ollama, NF4 4-bit quantized, temperature=0.0
- 8 few-shot exemplars per category; strict JSON output with PydanticOutputParser + 1 retry on malformed JSON
- Event taxonomy (closed set): `earnings_report`, `mergers_acquisitions`, `regulatory_action`, `management_change`, `product_launch`, `litigation`, `guidance_update`, `macro_other`
- Severity: `low / medium / high` — rubric in system prompt
- Pre-filter: only run Mistral if keyword match OR sentiment ≠ neutral (cuts ~70% of LLM calls)
- Top-3 ChromaDB context from `sectors` + `fin_glossary` injected into prompt
- `severity == high` → LangGraph interrupt for human review
- `category == earnings_report` → route to Earnings Sub-Agent

### Step 9b: Agent 4b — Earnings Sub-Agent (`agents/earnings_subagent.py`)
- Triggered only for `earnings_report` events
- Extracts EPS, revenue, guidance figures from article text via regex + Mistral
- Computes beat/miss vs analyst consensus (fetched from yfinance `earnings` table)
- Enriches the Event object before passing to Signal Generation

### Step 10: Agent 5 — Signal Generation
- Deterministic scoring (no LLM call — fully auditable):
  ```
  score = 0.50 × sentiment_ewma
        + 0.35 × event_severity_weight   (low=0.2, med=0.5, high=1.0; signed by event polarity)
        + 0.15 × price_zscore            (5-day return vs 30-day σ, contrarian-damped)

  bullish  if score >  0.25
  bearish  if score < -0.25
  neutral  otherwise

  agreement_factor = 1 - stdev(components) / max_stdev
  confidence = min(1.0, |score| × agreement_factor)
  ```
- Event polarity: negative for `litigation`/`regulatory_action`; positive for `earnings_report`/`mergers_acquisitions`/`product_launch`
- Persist all signals to SQLite with full component breakdown
- LangGraph interrupt() for high-severity pending review

---

## Part 1b: Briefing Report Agent (Agent 6)

### What it does
Generates a structured daily Markdown briefing from signals + events. Saved to `reports/` and served via the GitHub Pages dashboard.

### Sections
1. Top movers (biggest sentiment shifts)
2. Sector heatmap commentary
3. Event log with severity
4. High-severity callouts
5. Signal table with confidence bars
6. Methodology footer + disclaimer

### Implementation (`agents/briefing_report.py`)
- Jinja2 template rendering → `reports/YYYY-MM-DD_briefing.md`
- Optional: matplotlib sector heatmap saved as PNG alongside
- Disclaimer on every output: *"Educational use only. Not investment advice."*

---

## Part 2: Investment Recommendation Engine (Agent 7)

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
  → event_detection → [earnings_subagent if earnings] 
  → [human_review if high severity] 
  → signal_generation → briefing_report → recommendation → END
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

---

## Part 6: Evaluation Targets

| Metric | Dataset | Target |
|---|---|---|
| Sentiment macro-F1 | Financial PhraseBank (75% agree split) | ≥ 0.85 |
| Sentiment macro-F1 | FiQA (3-class via ±0.1 thresholds) | ≥ 0.65 |
| Entity linking precision@1 | 200 hand-labelled headlines | ≥ 0.90 |
| Event classification accuracy | 300 synthetic + 100 real labelled | ≥ 0.75 macro |
| Signal–price IC (Spearman ρ) | yfinance 30-day, 5-day forward returns | report only, no target |

---

## Part 7: Implementation Gotchas (Must Read)

1. **Look-ahead bias** — align signals to `published_at`, not ingestion time; shift forward returns by ≥1 trading day
2. **FinBERT on headlines** — trained on analyst sentences; aggressive headlines often score neutral. Calibrate thresholds on a held-out sample of your actual feed
3. **Sentence boundaries** — newspaper3k extracts malformed sentences from bullets/tables. Fallback: split on `\n\n` then `. ` to avoid 200-token "sentences"
4. **newspaper3k brittleness** — many sites block default UA or require JS. Add rotating UA + cloudscraper fallback; degrade to RSS summary when full text fails
5. **MinHash threshold** — 0.85 misses wire-service rewrites (Reuters→Yahoo, ~0.6–0.75). Add secondary check: `source ≠ source AND title cosine > 0.9`
6. **Entity ambiguity** — "Target", "Ford", "Apple" as common words. Require corroborating financial cue before linking
7. **SEC EDGAR rate limit** — requires descriptive `User-Agent` with contact email; max 10 req/sec. Violation = IP ban
8. **NF4 JSON malformation** — Mistral occasionally emits broken JSON. Always wrap in retry-with-repair loop (1 reformatting retry max)
9. **Survivorship bias** — S&P 500 KB uses current constituents. Document this bias clearly if backtesting historically
10. **Timezones** — yfinance = America/New_York; RSS may be UTC or local or missing. Normalise everything to UTC at ingestion; reject articles with no parseable timestamp
11. **Mistral licence** — Mistral-7B-Instruct-v0.2 = Apache-2.0 ✅. Verify ProsusAI/finbert licence for any commercial use
12. **Disclaimer required everywhere** — every signal, briefing, and dashboard tab must carry: *"Educational use only. Not investment advice."*

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
bitsandbytes>=0.43.0       # NF4 4-bit quantization for Mistral
jinja2>=3.1.0             # briefing report templates
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
| LLM quantization | NF4 4-bit (bitsandbytes) | Fits Mistral-7B in 16GB VRAM (~4.5GB) |
| Dashboard | GitHub Pages (HTML/JS) | No server, free hosting, shareable URL |

---

*Built for retail investors. No financial advice — always do your own research.*
