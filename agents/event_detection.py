import json
import re
from models.event import Event, EventCategory
from agents.hf_client import hf_post
from config.settings import get_settings

KEYWORDS = ["merger", "acquisition", "earnings", "eps", "revenue", "guidance", "lawsuit",
            "recall", "fda", "sec", "ceo", "layoff", "bankruptcy", "dividend", "buyback",
            "regulation", "investigation", "settlement", "product launch", "partnership"]

FEW_SHOT = """Classify the financial event in this article excerpt.
Return JSON only: {"category": "<category>", "severity": <0.0-1.0>, "summary": "<one sentence>"}

Categories: earnings_report, mergers_acquisitions, regulatory_action, management_change,
product_launch, litigation, guidance_update, macro_other

Severity rubric: low=0.0-0.3 (routine), medium=0.3-0.7 (notable), high=0.7-1.0 (market-moving)

Examples:
Text: "Apple beat Q3 EPS estimates by $0.12, revenue up 8% YoY"
JSON: {"category": "earnings_report", "severity": 0.6, "summary": "Apple beat Q3 earnings estimates"}

Text: "Microsoft to acquire Activision for $68.7 billion"
JSON: {"category": "mergers_acquisitions", "severity": 0.9, "summary": "Microsoft acquiring Activision Blizzard"}

Text: "FDA approves new diabetes drug from Eli Lilly"
JSON: {"category": "regulatory_action", "severity": 0.7, "summary": "FDA approves Eli Lilly diabetes drug"}

Text:
"""


def should_run_llm(sentiment_score: float, article_text: str) -> bool:
    text_lower = article_text.lower()
    has_keyword = any(kw in text_lower for kw in KEYWORDS)
    is_non_neutral = abs(sentiment_score) > 0.1
    return has_keyword or is_non_neutral


def parse_event_json(raw: str) -> dict | None:
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _call_mistral(article_text: str) -> dict | None:
    settings = get_settings()
    url = f"https://api-inference.huggingface.co/models/{settings.mistral_model_id}"
    prompt = FEW_SHOT + article_text[:1000] + '\nJSON:'
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 150, "temperature": 0.0}}
    try:
        raw = hf_post(url, payload, token=settings.hf_token.get_secret_value(),
                      retries=settings.hf_api_retries, backoff_base=settings.hf_api_backoff_base)
    except Exception:
        return None
    generated = raw[0].get("generated_text", "") if isinstance(raw, list) else ""
    result = parse_event_json(generated)
    if result is None:
        try:
            repair_payload = {"inputs": prompt + "\nReturn valid JSON only:",
                              "parameters": {"max_new_tokens": 150, "temperature": 0.0}}
            raw2 = hf_post(url, repair_payload, token=settings.hf_token.get_secret_value(),
                           retries=1, backoff_base=0.0)
            generated2 = raw2[0].get("generated_text", "") if isinstance(raw2, list) else ""
        except Exception:
            return None
        result = parse_event_json(generated2)
    return result


def event_detection_node(state: dict) -> dict:
    settings = get_settings()
    events: list[Event] = []
    ticker_sentiment = {s.ticker: s.score for s in state["sentiment_scores"]}

    for article in state["deduplicated_articles"]:
        entities = state["article_entities"].get(article.id, [])
        ticker = next((e.ticker for e in entities if e.linked and e.ticker), None)
        sentiment_score = ticker_sentiment.get(ticker, 0.0) if ticker else 0.0

        if not should_run_llm(sentiment_score, article.body):
            continue

        parsed = _call_mistral(article.body)
        if not parsed:
            continue

        try:
            category = EventCategory(parsed["category"])
        except ValueError:
            category = EventCategory.MACRO_OTHER

        # clamp severity to [0, 1] before passing to Event model
        severity = min(1.0, max(0.0, float(parsed.get("severity", 0.5))))
        events.append(Event(
            article_id=article.id,
            ticker=ticker,
            category=category,
            severity=severity,
            summary=parsed.get("summary", ""),
            raw_llm_output=str(parsed),
        ))

    requires_interrupt = any(e.severity >= settings.high_severity_threshold for e in events)
    return {"events": events, "requires_interrupt": requires_interrupt}
