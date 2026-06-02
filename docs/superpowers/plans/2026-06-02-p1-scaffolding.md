# P1: Scaffolding + Config + Models + State

> **For agentic workers:** Use subagent-driven-development to implement task-by-task.

**Goal:** Installable Python package with all Pydantic models, config, and LangGraph state schema.

**Architecture:** Pure data layer — no agents, no API calls. Everything downstream depends on these types.

**Tech Stack:** Python 3.11, pydantic v2, pydantic-settings, langgraph

---

### Task 1: pyproject.toml + package scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `config/__init__.py`
- Create: `models/__init__.py`
- Create: `state/__init__.py`
- Create: `agents/__init__.py`
- Create: `graph/__init__.py`
- Create: `storage/__init__.py`
- Create: `backtesting/__init__.py`
- Create: `training/__init__.py`
- Create: `scripts/__init__.py`
- Create: `.env.example`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "stock-sentiment"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.2.0",
    "langchain-core>=0.3.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.2.0",
    "transformers>=4.40.0",
    "torch>=2.2.0",
    "spacy>=3.7.0",
    "sentence-transformers>=3.0.0",
    "supabase>=2.4.0",
    "feedparser>=6.0.0",
    "newspaper3k>=0.2.8",
    "lxml[html_clean]>=5.0.0",
    "datasketch>=1.6.0",
    "yfinance>=0.2.40",
    "pandas>=2.1.0",
    "huggingface-hub>=0.22.0",
    "jinja2>=3.1.0",
    "datasets>=2.19.0",
    "scikit-learn>=1.4.0",
    "matplotlib>=3.8.0",
    "requests>=2.31.0",
    "cloudscraper>=1.2.71",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "pytest-cov>=5.0.0"]
```

- [ ] **Step 2: Create all __init__.py files**

```bash
touch config/__init__.py models/__init__.py state/__init__.py
touch agents/__init__.py graph/__init__.py storage/__init__.py
touch backtesting/__init__.py training/__init__.py scripts/__init__.py
touch reports/__init__.py
```

- [ ] **Step 3: Create .env.example**

```bash
# HuggingFace
HF_TOKEN=hf_your_token_here

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key

# SEC EDGAR
EDGAR_USER_AGENT="stockSentimentAnalysis/1.0 your@email.com"

# Pipeline tuning
MAX_ARTICLES_PER_RUN=50
MINHASH_THRESHOLD=0.72
HIGH_SEVERITY_THRESHOLD=0.7
FINBERT_MODEL_ID=ProsusAI/finbert
MISTRAL_MODEL_ID=mistralai/Mistral-7B-Instruct-v0.2
```

- [ ] **Step 4: Install package**

```bash
pip install -e ".[dev]"
```

Expected: no errors, `import stock_sentiment` works (will fail until src layout added — that's fine for now).

- [ ] **Step 5: Commit**

```bash
git checkout -b feature/p1-scaffolding
git add pyproject.toml .env.example config/ models/ state/ agents/ graph/ storage/ backtesting/ training/ scripts/ reports/
git commit -m "feat: project scaffold, pyproject.toml, package structure"
```

---

### Task 2: Config layer

**Files:**
- Create: `config/settings.py`
- Create: `config/feeds.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_config.py
from config.settings import Settings

def test_settings_defaults():
    s = Settings()
    assert s.max_articles_per_run == 50
    assert s.minhash_threshold == 0.72
    assert s.high_severity_threshold == 0.7

def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("MAX_ARTICLES_PER_RUN", "10")
    s = Settings()
    assert s.max_articles_per_run == 10
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_config.py -v
```
Expected: `ModuleNotFoundError: No module named 'config.settings'`

- [ ] **Step 3: Implement config/settings.py**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hf_token: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    edgar_user_agent: str = "stockSentimentAnalysis/1.0 user@example.com"

    max_articles_per_run: int = 50
    minhash_threshold: float = 0.72
    high_severity_threshold: float = 0.7

    finbert_model_id: str = "ProsusAI/finbert"
    mistral_model_id: str = "mistralai/Mistral-7B-Instruct-v0.2"
    embedding_model_id: str = "sentence-transformers/all-MiniLM-L6-v2"

    hf_api_retries: int = 3
    hf_api_backoff_base: float = 2.0
```

- [ ] **Step 4: Implement config/feeds.py**

```python
RSS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline",
    "https://www.marketwatch.com/rss/topstories",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    # SEC EDGAR 8-K filings
    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&dateb=&owner=include&count=40&output=atom",
]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add config/settings.py config/feeds.py tests/test_config.py
git commit -m "feat: config layer with pydantic-settings and RSS feeds"
```

---

### Task 3: Pydantic models

**Files:**
- Create: `models/article.py`
- Create: `models/entity.py`
- Create: `models/sentiment.py`
- Create: `models/event.py`
- Create: `models/signal.py`
- Create: `models/recommendation.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_models.py
from datetime import datetime, timezone
from models.article import Article
from models.entity import Entity
from models.sentiment import SentimentScore
from models.event import Event, EventCategory
from models.signal import InvestmentSignal
from models.recommendation import UserProfile, InvestmentPlan, Allocation

def test_article_id_is_sha256_of_url():
    a = Article(
        url="https://example.com/news/1",
        title="Test",
        body="body",
        source="example",
        published_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
    )
    import hashlib
    expected = hashlib.sha256(b"https://example.com/news/1").hexdigest()
    assert a.id == expected

def test_sentiment_score_bounds():
    s = SentimentScore(ticker="AAPL", score=0.8, label="positive", n_sentences=3, window_ewma=0.75)
    assert -1.0 <= s.score <= 1.0

def test_signal_direction():
    sig = InvestmentSignal(
        ticker="AAPL", direction="bullish", confidence=0.8,
        score=0.4, sentiment_component=0.5,
        event_component=0.3, price_component=0.1,
        evidence_ids=[], generated_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
    )
    assert sig.direction in ("bullish", "bearish", "neutral")

def test_user_profile_risk_validation():
    from pydantic import ValidationError
    import pytest
    with pytest.raises(ValidationError):
        UserProfile(investment_amount=1000, risk_appetite="unknown", time_horizon_months=12)
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_models.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement models/article.py**

```python
import hashlib
from datetime import datetime
from pydantic import BaseModel, model_validator

class Article(BaseModel):
    id: str = ""
    url: str
    title: str
    body: str
    source: str
    published_at: datetime
    minhash_signature: list[int] = []
    is_duplicate: bool = False

    @model_validator(mode="after")
    def set_id(self) -> "Article":
        if not self.id:
            self.id = hashlib.sha256(self.url.encode()).hexdigest()
        return self
```

- [ ] **Step 4: Implement models/entity.py**

```python
from pydantic import BaseModel

class Entity(BaseModel):
    raw_text: str
    ticker: str | None = None
    sector: str | None = None
    similarity_score: float = 0.0
    linked: bool = False
```

- [ ] **Step 5: Implement models/sentiment.py**

```python
from pydantic import BaseModel, field_validator

class SentimentScore(BaseModel):
    ticker: str
    score: float
    label: str
    n_sentences: int
    window_ewma: float

    @field_validator("score", "window_ewma")
    @classmethod
    def clamp(cls, v: float) -> float:
        return max(-1.0, min(1.0, v))
```

- [ ] **Step 6: Implement models/event.py**

```python
from enum import Enum
from pydantic import BaseModel

class EventCategory(str, Enum):
    EARNINGS_REPORT = "earnings_report"
    MERGERS_ACQUISITIONS = "mergers_acquisitions"
    REGULATORY_ACTION = "regulatory_action"
    MANAGEMENT_CHANGE = "management_change"
    PRODUCT_LAUNCH = "product_launch"
    LITIGATION = "litigation"
    GUIDANCE_UPDATE = "guidance_update"
    MACRO_OTHER = "macro_other"

class Event(BaseModel):
    article_id: str
    ticker: str | None = None
    category: EventCategory
    severity: float  # 0.0 to 1.0
    summary: str = ""
    raw_llm_output: str = ""
```

- [ ] **Step 7: Implement models/signal.py**

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel

class InvestmentSignal(BaseModel):
    ticker: str
    direction: Literal["bullish", "bearish", "neutral"]
    confidence: float
    score: float
    sentiment_component: float
    event_component: float
    price_component: float
    evidence_ids: list[str]
    generated_at: datetime
    horizon_days: int = 5
```

- [ ] **Step 8: Implement models/recommendation.py**

```python
from typing import Literal
from pydantic import BaseModel, field_validator

class UserProfile(BaseModel):
    investment_amount: float
    risk_appetite: Literal["conservative", "moderate", "aggressive"]
    time_horizon_months: int
    preferred_sectors: list[str] = []
    exclude_tickers: list[str] = []

class Allocation(BaseModel):
    ticker: str
    amount: float
    percentage: float
    rationale: str

class InvestmentPlan(BaseModel):
    total_amount: float
    allocations: list[Allocation]
    risk_summary: str
    expected_return_range: tuple[float, float]
    time_horizon_months: int
    rebalance_trigger: Literal["monthly", "on_new_signal"]
    disclaimer: str = "Educational use only. Not investment advice."
```

- [ ] **Step 9: Run tests**

```bash
pytest tests/test_models.py -v
```
Expected: 4 passed

- [ ] **Step 10: Commit**

```bash
git add models/ tests/test_models.py
git commit -m "feat: pydantic models for article, entity, sentiment, event, signal, recommendation"
```

---

### Task 4: LangGraph state schema

**Files:**
- Create: `state/graph_state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_state.py
from state.graph_state import GraphState

def test_graph_state_has_required_keys():
    state = GraphState(
        raw_articles=[],
        deduplicated_articles=[],
        article_entities={},
        sentiment_scores=[],
        events=[],
        signals=[],
        investment_plan=None,
        backtest_results=None,
        requires_interrupt=False,
        human_review_decision=None,
        error_log=[],
        run_date="2026-06-02",
    )
    assert state["signals"] == []
    assert state["error_log"] == []
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_state.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement state/graph_state.py**

```python
import operator
from typing import Annotated, Any
from typing_extensions import TypedDict
from models.article import Article
from models.entity import Entity
from models.sentiment import SentimentScore
from models.event import Event
from models.signal import InvestmentSignal
from models.recommendation import InvestmentPlan

class GraphState(TypedDict):
    raw_articles: list[Article]
    deduplicated_articles: list[Article]
    article_entities: dict[str, list[Entity]]   # article_id -> entities
    sentiment_scores: list[SentimentScore]
    events: list[Event]
    signals: list[InvestmentSignal]
    investment_plan: InvestmentPlan | None
    backtest_results: dict[str, Any] | None
    requires_interrupt: bool
    human_review_decision: str | None
    error_log: Annotated[list[str], operator.add]
    run_date: str   # YYYY-MM-DD UTC
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_state.py -v
```
Expected: 1 passed

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add state/graph_state.py tests/test_state.py
git commit -m "feat: LangGraph GraphState TypedDict with all pipeline fields"
```

---

### Task 5: training/ scaffold (v2 placeholder)

**Files:**
- Create: `training/dataset.py`
- Create: `training/trainer.py`
- Create: `training/evaluate.py`

- [ ] **Step 1: Create scaffold files**

```python
# training/dataset.py
# v2: FinBERT fine-tuning dataset loader
# Deferred — see PLAN.md Part 4
raise NotImplementedError("FinBERT fine-tuning is a v2 feature")
```

```python
# training/trainer.py
# v2: HuggingFace Trainer for FinBERT fine-tuning
raise NotImplementedError("FinBERT fine-tuning is a v2 feature")
```

```python
# training/evaluate.py
# v2: Evaluate fine-tuned vs base FinBERT
raise NotImplementedError("FinBERT fine-tuning is a v2 feature")
```

- [ ] **Step 2: Commit**

```bash
git add training/
git commit -m "feat: training/ scaffold placeholder for v2 FinBERT fine-tuning"
```

---

## P1 Done

All of these pass before moving to P2:
```bash
pytest tests/ -v          # all green
pip install -e ".[dev]"   # clean install
python -c "from state.graph_state import GraphState; print('OK')"
```
