import os
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, BaseLoader

from models.event import Event, EventCategory
from models.signal import InvestmentSignal
from models.sentiment import SentimentScore
from config.settings import get_settings

# ---------------------------------------------------------------------------
# Ticker → sector lookup (best-effort; unknown tickers fall through to "Other")
# ---------------------------------------------------------------------------
TICKER_SECTOR: dict[str, str] = {
    # Technology
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
    "GOOG": "Technology", "META": "Technology", "NVDA": "Technology",
    "AMD": "Technology", "INTC": "Technology", "TSLA": "Technology",
    "CRM": "Technology", "ORCL": "Technology", "ADBE": "Technology",
    "QCOM": "Technology", "TXN": "Technology", "AVGO": "Technology",
    # Financials
    "JPM": "Financials", "BAC": "Financials", "WFC": "Financials",
    "GS": "Financials", "MS": "Financials", "C": "Financials",
    "AXP": "Financials", "BRK.B": "Financials", "V": "Financials",
    "MA": "Financials", "PYPL": "Financials",
    # Healthcare
    "JNJ": "Healthcare", "UNH": "Healthcare", "PFE": "Healthcare",
    "MRK": "Healthcare", "ABBV": "Healthcare", "LLY": "Healthcare",
    "BMY": "Healthcare", "AMGN": "Healthcare", "GILD": "Healthcare",
    # Consumer
    "AMZN": "Consumer Discretionary", "HD": "Consumer Discretionary",
    "MCD": "Consumer Staples", "KO": "Consumer Staples", "PEP": "Consumer Staples",
    "WMT": "Consumer Staples", "COST": "Consumer Staples", "PG": "Consumer Staples",
    # Energy
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy", "SLB": "Energy",
    # Industrials
    "BA": "Industrials", "CAT": "Industrials", "GE": "Industrials",
    "HON": "Industrials", "UPS": "Industrials", "RTX": "Industrials",
    # Communication
    "NFLX": "Communication Services", "DIS": "Communication Services",
    "T": "Communication Services", "VZ": "Communication Services",
    "CMCSA": "Communication Services",
}


# ---------------------------------------------------------------------------
# Jinja2 template
# ---------------------------------------------------------------------------
_TEMPLATE_SRC = """\
# Daily Investment Briefing — {{ run_date }}

> Generated at {{ generated_at }}

---

## Overview

| Metric | Value |
|--------|-------|
| Total articles processed | {{ total_articles }} |
| Total signals generated | {{ signals | length }} |
| High-severity events | {{ high_severity_events | length }} |

---

## Top Movers

{% if top_movers %}
| Rank | Ticker | Direction | Confidence | Score |
|------|--------|-----------|-----------|-------|
{% for s in top_movers %}| {{ loop.index }} | **{{ s.ticker }}** | {{ s.direction | upper }} | {{ "%.2f" | format(s.confidence) }} | {{ "%+.3f" | format(s.score) }} |
{% endfor %}
{% else %}
_No signals available._
{% endif %}

---

## Sector Commentary

{% if sector_groups %}
{% for sector, sigs in sector_groups.items() %}
### {{ sector }}

{% for s in sigs %}
- **{{ s.ticker }}** — {{ s.direction | upper }}, score {{ "%+.3f" | format(s.score) }}, confidence {{ "%.2f" | format(s.confidence) }}
{% endfor %}

{% endfor %}
{% else %}
_No sector data available._
{% endif %}

---

## Event Log

{% if events %}
| Ticker | Category | Severity | Summary |
|--------|----------|---------|---------|
{% for ev in events %}| {{ ev.ticker or "—" }} | {{ ev.category.value }} | {{ "%.2f" | format(ev.severity) }} | {{ ev.summary | truncate(80, True) }} |
{% endfor %}
{% else %}
_No events recorded._
{% endif %}

---

## High-Severity Callouts

{% if high_severity_events %}
{% for ev in high_severity_events %}
> **⚠ {{ ev.ticker or "MARKET" }} — {{ ev.category.value | upper }}** (severity {{ "%.2f" | format(ev.severity) }})
>
> {{ ev.summary }}

{% endfor %}
{% else %}
_No high-severity events._
{% endif %}

---

## Full Signal Table

{% if signals %}
| Ticker | Direction | Confidence | Score | Sentiment | Event | Price |
|--------|-----------|-----------|-------|-----------|-------|-------|
{% for s in signals %}| {{ s.ticker }} | {{ s.direction }} | {{ "%.3f" | format(s.confidence) }} | {{ "%+.3f" | format(s.score) }} | {{ "%+.3f" | format(s.sentiment_component) }} | {{ "%+.3f" | format(s.event_component) }} | {{ "%+.3f" | format(s.price_component) }} |
{% endfor %}
{% else %}
_No signals available._
{% endif %}

---

## Methodology

Signals are generated using a weighted composite score:

```
score = 0.50 × sentiment_ewma + 0.35 × event_severity_weight + 0.15 × price_z_score
```

- **sentiment_ewma**: exponentially weighted moving average of FinBERT sentence scores
  for articles mentioning the ticker over the current window.
- **event_severity_weight**: polarity-adjusted average severity of detected events
  (negative for litigation/regulatory, positive for earnings/M&A/launches/guidance).
- **price_z_score**: recent 5-day return normalised by the trailing standard deviation.

Score thresholds: `> 0.25` → **bullish**, `< -0.25` → **bearish**, otherwise **neutral**.
Confidence reflects agreement across components (lower variance = higher confidence).

---

## Disclaimer

*This report is generated automatically for **educational purposes only**. It does not
constitute investment advice. Past signals are not indicative of future returns. Always
conduct independent research and consult a qualified financial advisor before making any
investment decision.*
"""


def _build_sector_groups(signals: list[InvestmentSignal]) -> dict[str, list[InvestmentSignal]]:
    groups: dict[str, list[InvestmentSignal]] = {}
    for sig in signals:
        sector = TICKER_SECTOR.get(sig.ticker, "Other")
        groups.setdefault(sector, []).append(sig)
    # Sort each sector's signals by abs(score) descending
    for sector in groups:
        groups[sector].sort(key=lambda s: abs(s.score), reverse=True)
    # Return sectors sorted alphabetically (Other at end)
    return dict(
        sorted(groups.items(), key=lambda kv: (kv[0] == "Other", kv[0]))
    )


def briefing_report_node(state: dict) -> dict:
    settings = get_settings()
    run_date: str = state.get("run_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    signals: list[InvestmentSignal] = state.get("signals", [])
    events: list[Event] = state.get("events", [])
    raw_articles = state.get("raw_articles", [])

    # Top 5 movers by absolute score
    top_movers = sorted(signals, key=lambda s: abs(s.score), reverse=True)[:5]

    # Sector groupings
    sector_groups = _build_sector_groups(signals)

    # High-severity events
    high_severity_threshold = getattr(settings, "high_severity_threshold", 0.7)
    high_severity_events = [ev for ev in events if ev.severity >= high_severity_threshold]

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    env = Environment(loader=BaseLoader(), autoescape=False)
    template = env.from_string(_TEMPLATE_SRC)

    rendered = template.render(
        run_date=run_date,
        generated_at=generated_at,
        total_articles=len(raw_articles),
        signals=sorted(signals, key=lambda s: abs(s.score), reverse=True),
        events=events,
        top_movers=top_movers,
        sector_groups=sector_groups,
        high_severity_events=high_severity_events,
    )

    reports_dir = Path(__file__).resolve().parent.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    output_path = reports_dir / f"{run_date}_briefing.md"
    output_path.write_text(rendered, encoding="utf-8")

    return {}
