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
