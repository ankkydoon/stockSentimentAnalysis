from langgraph.types import interrupt

from models.event import EventCategory


def route_after_ingestion(state: dict) -> str:
    articles = state.get("deduplicated_articles") or []
    if not articles:
        return "end"
    return "entity_recognition"


def route_after_ner(state: dict) -> str:
    article_entities: dict = state.get("article_entities") or {}
    if not article_entities:
        return "end"
    if all(len(v) == 0 for v in article_entities.values()):
        return "end"
    return "sentiment_analysis"


def route_after_event_detection(state: dict) -> str:
    events = state.get("events") or []
    has_earnings = any(
        e.category == EventCategory.EARNINGS_REPORT for e in events
    )
    if has_earnings:
        return "earnings_subagent"
    if state.get("requires_interrupt"):
        return "human_review"
    return "signal_generation"


def route_after_earnings(state: dict) -> str:
    if state.get("requires_interrupt"):
        return "human_review"
    return "signal_generation"


def human_review_node(state: dict) -> dict:
    decision = interrupt(
        {
            "message": "High-severity event detected. Approve signal generation? (y/n)",
            "events": [
                {"ticker": e.ticker, "category": e.category, "severity": e.severity}
                for e in (state.get("events") or [])
            ],
        }
    )
    return {"human_review_decision": decision, "requires_interrupt": False}
