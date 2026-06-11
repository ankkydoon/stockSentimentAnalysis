import math
from datetime import datetime, timezone
import yfinance as yf
from config.settings import get_settings
from models.event import EventCategory
from models.signal import InvestmentSignal
from storage.supabase_store import SupabaseStore

NEGATIVE_EVENTS = {EventCategory.LITIGATION, EventCategory.REGULATORY_ACTION}
POSITIVE_EVENTS = {EventCategory.EARNINGS_REPORT, EventCategory.MERGERS_ACQUISITIONS,
                   EventCategory.PRODUCT_LAUNCH, EventCategory.GUIDANCE_UPDATE}
SEVERITY_WEIGHTS = {"low": 0.2, "medium": 0.5, "high": 1.0}


def _severity_label(severity: float) -> str:
    if severity >= 0.7:
        return "high"
    if severity >= 0.3:
        return "medium"
    return "low"


def _get_price_zscore(ticker: str) -> float:
    try:
        hist = yf.Ticker(ticker).history(period="35d")["Close"]
        if len(hist) < 6:
            return 0.0
        returns = hist.pct_change().dropna()
        recent = returns.iloc[-5:].mean()
        sigma = returns.iloc[:-5].std()
        if sigma == 0:
            return 0.0
        return float(recent / sigma)
    except Exception:
        return 0.0


def compute_signal_score(sentiment_ewma: float, event_severity_weight: float, price_zscore: float,
                         w_sentiment: float = 0.50, w_event: float = 0.35, w_price: float = 0.15) -> float:
    return w_sentiment * sentiment_ewma + w_event * event_severity_weight + w_price * price_zscore


def score_to_direction(score: float) -> str:
    if score > 0.25:
        return "bullish"
    if score < -0.25:
        return "bearish"
    return "neutral"


def compute_confidence(score: float, components: list[float]) -> float:
    if not components:
        return 0.0
    mean = sum(components) / len(components)
    variance = sum((c - mean) ** 2 for c in components) / len(components)
    std = math.sqrt(variance)
    agreement = max(0.0, 1.0 - std)
    return min(1.0, abs(score) * agreement)


def signal_generation_node(state: dict) -> dict:
    settings = get_settings()
    store = SupabaseStore(url=settings.supabase_url,
                          key=settings.supabase_key.get_secret_value())
    run_date = state.get("run_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    weights = store.get_weights()
    w_sentiment = weights.get("w_sentiment", 0.50)
    w_event = weights.get("w_event", 0.35)
    w_price = weights.get("w_price", 0.15)
    print(f"[signals] using weights sentiment={w_sentiment} event={w_event} price={w_price}")

    ticker_sentiment = {s.ticker: s for s in state["sentiment_scores"]}
    ticker_events: dict[str, list] = {}
    for event in state["events"]:
        if event.ticker:
            ticker_events.setdefault(event.ticker, []).append(event)

    signals: list[InvestmentSignal] = []
    for ticker, sentiment in ticker_sentiment.items():
        events = ticker_events.get(ticker, [])
        event_weight = 0.0
        for ev in events:
            polarity = -1.0 if ev.category in NEGATIVE_EVENTS else 1.0
            weight = SEVERITY_WEIGHTS[_severity_label(ev.severity)]
            event_weight += polarity * weight
        if events:
            event_weight /= len(events)

        price_zscore = _get_price_zscore(ticker)
        score = compute_signal_score(sentiment.window_ewma, event_weight, price_zscore,
                                     w_sentiment=w_sentiment, w_event=w_event, w_price=w_price)
        # clamp score to model bounds [-1, 1]
        score = max(-1.0, min(1.0, score))
        direction = score_to_direction(score)
        confidence = compute_confidence(score, [sentiment.window_ewma, event_weight, price_zscore])
        evidence_ids = tuple(
            a.id for a in state["deduplicated_articles"]
            if any(e.ticker == ticker for e in state["article_entities"].get(a.id, []))
        )

        sig = InvestmentSignal(
            ticker=ticker, direction=direction,
            confidence=round(confidence, 3),
            score=round(score, 3),
            sentiment_component=round(sentiment.window_ewma, 3),
            event_component=round(event_weight, 3),
            price_component=round(max(-1.0, min(1.0, price_zscore)), 3),
            evidence_ids=evidence_ids,
            generated_at=datetime.now(timezone.utc),
        )
        store.upsert_signal(sig)
        signals.append(sig)
        print(f"[signals] {ticker}: direction={direction} score={score:.3f} confidence={round(confidence, 3):.3f}")

    print(f"[signals] generated {len(signals)} signals from {len(ticker_sentiment)} tickers")
    return {"signals": signals}
