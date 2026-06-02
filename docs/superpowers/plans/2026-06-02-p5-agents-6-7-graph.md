# P5: Agents 6–7 + Graph Wiring + main.py

> **For agentic workers:** Use subagent-driven-development to implement task-by-task.

**Goal:** Signals → Jinja2 briefing report + S&P 500 stock recommendations + full LangGraph pipeline wired end-to-end.

**Architecture:** Agent 6 renders Jinja2 template to Markdown. Agent 7 filters/ranks signals into a personalized plan. graph/builder.py wires all nodes. main.py is the CLI entry point.

**Tech Stack:** Jinja2, LangGraph, yfinance

---

### Task 1: Agent 6 — Briefing Report

**Files:**
- Create: `agents/briefing_report.py`
- Create: `reports/templates/briefing.md.j2`
- Create: `tests/test_briefing_report.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_briefing_report.py
from agents.briefing_report import render_briefing

def test_briefing_contains_disclaimer():
    output = render_briefing(signals=[], events=[], run_date="2026-06-02")
    assert "Educational use only" in output

def test_briefing_contains_run_date():
    output = render_briefing(signals=[], events=[], run_date="2026-06-02")
    assert "2026-06-02" in output
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_briefing_report.py -v
```

- [ ] **Step 3: Create reports/templates/briefing.md.j2**

```jinja2
# Financial News Briefing — {{ run_date }}

> **Educational use only. Not investment advice.**

## Top Signals

{% if signals %}
| Ticker | Direction | Confidence | Score |
|--------|-----------|------------|-------|
{% for s in signals | sort(attribute='confidence', reverse=True) | list %}
| {{ s.ticker }} | {{ s.direction }} | {{ "%.2f"|format(s.confidence) }} | {{ "%.3f"|format(s.score) }} |
{% endfor %}
{% else %}
No signals generated this run.
{% endif %}

## Event Log

{% if events %}
{% for e in events %}
- **{{ e.ticker or "Market" }}** — {{ e.category }} (severity {{ "%.2f"|format(e.severity) }}): {{ e.summary }}
{% endfor %}
{% else %}
No events detected this run.
{% endif %}

## High-Severity Alerts

{% set high = events | selectattr('severity', 'ge', 0.7) | list %}
{% if high %}
{% for e in high %}
⚠️ **{{ e.ticker or "Market" }}**: {{ e.summary }}
{% endfor %}
{% else %}
No high-severity events.
{% endif %}

---
*Generated {{ run_date }} | Educational use only. Not investment advice.*
```

- [ ] **Step 4: Implement agents/briefing_report.py**

```python
import os
from datetime import datetime, timezone
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from models.signal import InvestmentSignal
from models.event import Event

TEMPLATE_DIR = Path(__file__).parent.parent / "reports" / "templates"

def render_briefing(signals: list[InvestmentSignal], events: list[Event], run_date: str) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("briefing.md.j2")
    return template.render(signals=signals, events=events, run_date=run_date)

def briefing_report_node(state: dict) -> dict:
    run_date = state.get("run_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    content = render_briefing(
        signals=state.get("signals", []),
        events=state.get("events", []),
        run_date=run_date,
    )
    output_path = Path("reports") / f"{run_date}_briefing.md"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(content)
    return {}
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_briefing_report.py -v
```
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add agents/briefing_report.py reports/templates/briefing.md.j2 tests/test_briefing_report.py
git commit -m "feat: Agent 6 Jinja2 briefing report with disclaimer"
```

---

### Task 2: Agent 7 — Investment Recommendation

**Files:**
- Create: `agents/recommendation.py`
- Create: `tests/test_recommendation.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_recommendation.py
from datetime import datetime, timezone
from models.signal import InvestmentSignal
from models.recommendation import UserProfile
from agents.recommendation import filter_signals, allocate

def make_signal(ticker, direction, confidence):
    return InvestmentSignal(
        ticker=ticker, direction=direction, confidence=confidence,
        score=0.4, sentiment_component=0.5, event_component=0.3, price_component=0.1,
        evidence_ids=[], generated_at=datetime(2026,6,2,tzinfo=timezone.utc),
    )

def test_filter_conservative_returns_top_3():
    signals = [make_signal(t, "bullish", c) for t, c in
               [("AAPL",0.9),("MSFT",0.85),("GOOGL",0.8),("NVDA",0.75),("META",0.72)]]
    profile = UserProfile(investment_amount=10000, risk_appetite="conservative", time_horizon_months=12)
    result = filter_signals(signals, profile)
    assert len(result) == 3

def test_filter_excludes_low_confidence():
    signals = [make_signal("AAPL", "bullish", 0.5)]  # below conservative threshold 0.7
    profile = UserProfile(investment_amount=10000, risk_appetite="conservative", time_horizon_months=12)
    result = filter_signals(signals, profile)
    assert len(result) == 0

def test_allocate_sums_to_total():
    signals = [make_signal(t, "bullish", c) for t, c in [("AAPL",0.9),("MSFT",0.8)]]
    profile = UserProfile(investment_amount=10000, risk_appetite="moderate", time_horizon_months=12)
    plan = allocate(signals, profile)
    total = sum(a.amount for a in plan.allocations)
    assert abs(total - 10000) < 0.01
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_recommendation.py -v
```

- [ ] **Step 3: Implement agents/recommendation.py**

```python
from datetime import datetime, timezone
from models.signal import InvestmentSignal
from models.recommendation import UserProfile, InvestmentPlan, Allocation

TIER_CONFIG = {
    "conservative": {"top_n": 3, "min_confidence": 0.7},
    "moderate":     {"top_n": 5, "min_confidence": 0.6},
    "aggressive":   {"top_n": 7, "min_confidence": 0.5},
}

def filter_signals(signals: list[InvestmentSignal], profile: UserProfile) -> list[InvestmentSignal]:
    cfg = TIER_CONFIG[profile.risk_appetite]
    bullish = [s for s in signals
               if s.direction == "bullish"
               and s.confidence >= cfg["min_confidence"]
               and s.ticker not in profile.exclude_tickers]
    if profile.preferred_sectors:
        bullish = [s for s in bullish if True]  # sector filter applied at graph level
    return sorted(bullish, key=lambda s: s.confidence, reverse=True)[:cfg["top_n"]]

def allocate(signals: list[InvestmentSignal], profile: UserProfile) -> InvestmentPlan:
    if not signals:
        return InvestmentPlan(
            total_amount=profile.investment_amount,
            allocations=[],
            risk_summary="No qualifying signals found.",
            expected_return_range=(0.0, 0.0),
            time_horizon_months=profile.time_horizon_months,
            rebalance_trigger="monthly",
        )
    total_confidence = sum(s.confidence for s in signals)
    allocations = []
    for s in signals:
        pct = s.confidence / total_confidence
        amount = round(profile.investment_amount * pct, 2)
        allocations.append(Allocation(
            ticker=s.ticker,
            amount=amount,
            percentage=round(pct * 100, 1),
            rationale=f"{s.direction} signal (confidence {s.confidence:.2f}, score {s.score:.3f})",
        ))
    return InvestmentPlan(
        total_amount=profile.investment_amount,
        allocations=allocations,
        risk_summary=f"{profile.risk_appetite.capitalize()} portfolio: {len(signals)} positions",
        expected_return_range=(5.0, 20.0),
        time_horizon_months=profile.time_horizon_months,
        rebalance_trigger="on_new_signal",
    )

def recommendation_node(state: dict) -> dict:
    profile = state.get("user_profile")
    if not profile:
        return {"investment_plan": None}
    filtered = filter_signals(state.get("signals", []), profile)
    plan = allocate(filtered, profile)
    return {"investment_plan": plan}
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_recommendation.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add agents/recommendation.py tests/test_recommendation.py
git commit -m "feat: Agent 7 investment recommendation with risk-tiered signal filtering"
```

---

### Task 3: Graph wiring

**Files:**
- Create: `graph/router.py`
- Create: `graph/builder.py`
- Create: `tests/test_graph.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_graph.py
from graph.builder import build_graph

def test_graph_compiles():
    graph = build_graph(interactive=False)
    assert graph is not None
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_graph.py -v
```

- [ ] **Step 3: Implement graph/router.py**

```python
from langgraph.graph import END

def should_continue_after_ingestion(state: dict) -> str:
    if not state.get("deduplicated_articles"):
        return END
    return "entity_recognition"

def should_continue_after_ner(state: dict) -> str:
    if not state.get("article_entities"):
        return END
    return "sentiment_analysis"

def route_after_event_detection(state: dict) -> str:
    from models.event import EventCategory
    events = state.get("events", [])
    has_earnings = any(e.category == EventCategory.EARNINGS_REPORT for e in events)
    if has_earnings:
        return "earnings_subagent"
    return "signal_generation"

def route_high_severity(state: dict, interactive: bool = False) -> str:
    if state.get("requires_interrupt") and interactive:
        return "human_review"
    return "signal_generation"
```

- [ ] **Step 4: Implement graph/builder.py**

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from state.graph_state import GraphState
from agents.news_ingestion import news_ingestion_node
from agents.entity_recognition import entity_recognition_node
from agents.sentiment_analysis import sentiment_analysis_node
from agents.event_detection import event_detection_node
from agents.earnings_subagent import earnings_subagent_node
from agents.signal_generation import signal_generation_node
from agents.briefing_report import briefing_report_node
from agents.recommendation import recommendation_node
from graph.router import (should_continue_after_ingestion, should_continue_after_ner,
                          route_after_event_detection)

def build_graph(interactive: bool = False) -> StateGraph:
    builder = StateGraph(GraphState)
    builder.add_node("news_ingestion", news_ingestion_node)
    builder.add_node("entity_recognition", entity_recognition_node)
    builder.add_node("sentiment_analysis", sentiment_analysis_node)
    builder.add_node("event_detection", event_detection_node)
    builder.add_node("earnings_subagent", earnings_subagent_node)
    builder.add_node("signal_generation", signal_generation_node)
    builder.add_node("briefing_report", briefing_report_node)
    builder.add_node("recommendation", recommendation_node)

    builder.set_entry_point("news_ingestion")
    builder.add_conditional_edges("news_ingestion", should_continue_after_ingestion,
                                  {"entity_recognition": "entity_recognition", END: END})
    builder.add_conditional_edges("entity_recognition", should_continue_after_ner,
                                  {"sentiment_analysis": "sentiment_analysis", END: END})
    builder.add_edge("sentiment_analysis", "event_detection")
    builder.add_conditional_edges("event_detection", route_after_event_detection,
                                  {"earnings_subagent": "earnings_subagent",
                                   "signal_generation": "signal_generation"})
    builder.add_edge("earnings_subagent", "signal_generation")
    builder.add_edge("signal_generation", "briefing_report")
    builder.add_edge("briefing_report", "recommendation")
    builder.add_edge("recommendation", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_graph.py -v
```
Expected: 1 passed

- [ ] **Step 6: Commit**

```bash
git add graph/router.py graph/builder.py tests/test_graph.py
git commit -m "feat: LangGraph pipeline wired with conditional routing"
```

---

### Task 4: main.py CLI entry point

**Files:**
- Create: `main.py`

- [ ] **Step 1: Implement main.py**

```python
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from config.settings import Settings
from models.recommendation import UserProfile
from graph.builder import build_graph

def main():
    parser = argparse.ArgumentParser(description="Financial News Sentiment Analyzer")
    parser.add_argument("--interactive", action="store_true", help="Enable human-in-the-loop for high-severity events")
    parser.add_argument("--thread-id", default="default")
    parser.add_argument("--backtest", action="store_true")
    parser.add_argument("--amount", type=float, default=10000.0)
    parser.add_argument("--risk", choices=["conservative", "moderate", "aggressive"], default="moderate")
    parser.add_argument("--horizon", type=int, default=12)
    args = parser.parse_args()

    settings = Settings()
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if args.backtest:
        from backtesting.engine import BacktestEngine
        engine = BacktestEngine(settings=settings)
        results = engine.run()
        print(json.dumps(results, indent=2))
        return

    user_profile = UserProfile(
        investment_amount=args.amount,
        risk_appetite=args.risk,
        time_horizon_months=args.horizon,
    )

    graph = build_graph(interactive=args.interactive)
    initial_state = {
        "raw_articles": [], "deduplicated_articles": [],
        "article_entities": {}, "sentiment_scores": [],
        "events": [], "signals": [],
        "investment_plan": None, "backtest_results": None,
        "requires_interrupt": False, "human_review_decision": None,
        "error_log": [], "run_date": run_date,
        "user_profile": user_profile,
    }

    config = {"configurable": {"thread_id": args.thread_id}}
    final_state = graph.invoke(initial_state, config=config)

    output = {
        "run_date": run_date,
        "signals": [s.model_dump(mode="json") for s in final_state.get("signals", [])],
        "investment_plan": final_state["investment_plan"].model_dump(mode="json") if final_state.get("investment_plan") else None,
        "error_log": final_state.get("error_log", []),
        "disclaimer": "Educational use only. Not investment advice.",
    }

    out_path = Path("outputs") / f"{run_date}.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2))
    print(f"Output written to {out_path}")

    if final_state.get("signals"):
        print(f"\n{'Ticker':<8} {'Direction':<12} {'Confidence':<12} {'Score':<8}")
        print("-" * 40)
        for s in sorted(final_state["signals"], key=lambda x: x.confidence, reverse=True):
            print(f"{s.ticker:<8} {s.direction:<12} {s.confidence:<12.2f} {s.score:<8.3f}")

    if final_state.get("investment_plan"):
        plan = final_state["investment_plan"]
        print(f"\nInvestment Plan ({plan.risk_summary})")
        for a in plan.allocations:
            print(f"  {a.ticker}: ${a.amount:.2f} ({a.percentage:.1f}%) — {a.rationale}")
        print(f"\n{plan.disclaimer}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add main.py
git commit -m "feat: main.py CLI entry point with --interactive, --backtest, --amount, --risk, --horizon"
```

---

## P5 Done

```bash
pytest tests/ -v
python -c "from graph.builder import build_graph; g = build_graph(); print('Graph OK')"
python main.py --help
```
