import re
from models.event import Event, EventCategory

EPS_PATTERN = re.compile(r'EPS\s+of\s+\$?([\d.]+)', re.IGNORECASE)
EPS_EST_PATTERN = re.compile(r'estimate[sd]?\s+of\s+\$?([\d.]+)', re.IGNORECASE)
REVENUE_PATTERN = re.compile(r'[Rr]evenue.*?\$?([\d.]+)\s*(billion|million|B|M)\b', re.IGNORECASE)


def extract_earnings_figures(text: str) -> dict:
    result: dict = {"reported_eps": None, "estimated_eps": None,
                    "reported_revenue": None, "beat_miss": None}
    eps_match = EPS_PATTERN.search(text)
    if eps_match:
        result["reported_eps"] = float(eps_match.group(1))
    est_match = EPS_EST_PATTERN.search(text)
    if est_match:
        result["estimated_eps"] = float(est_match.group(1))
    rev_match = REVENUE_PATTERN.search(text)
    if rev_match:
        multiplier = 1e9 if rev_match.group(2).lower() in ("billion", "b") else 1e6
        result["reported_revenue"] = float(rev_match.group(1)) * multiplier
    if result["reported_eps"] and result["estimated_eps"]:
        result["beat_miss"] = "beat" if result["reported_eps"] > result["estimated_eps"] else "miss"
    return result


def earnings_subagent_node(state: dict) -> dict:
    events = state.get("events", [])
    enriched = []
    for event in events:
        if event.category != EventCategory.EARNINGS_REPORT:
            enriched.append(event)
            continue
        article = next((a for a in state["deduplicated_articles"] if a.id == event.article_id), None)
        if article:
            figures = extract_earnings_figures(article.body)
            beat_miss = figures.get("beat_miss", "")
            suffix = f" ({beat_miss})" if beat_miss else ""
            event = event.model_copy(update={"summary": event.summary + suffix})
        enriched.append(event)
    return {"events": enriched}
