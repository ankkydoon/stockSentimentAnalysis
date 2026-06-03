import hashlib
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
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
    expected = hashlib.sha256(b"https://example.com/news/1").hexdigest()
    assert a.id == expected

def test_article_id_cannot_be_overridden():
    a = Article(
        url="https://example.com/news/1",
        title="Test",
        body="body",
        source="example",
        published_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        id="injected",
    )
    expected = hashlib.sha256(b"https://example.com/news/1").hexdigest()
    assert a.id == expected  # validator always overwrites

def test_article_requires_aware_datetime():
    with pytest.raises(ValidationError):
        Article(
            url="https://example.com/news/1",
            title="Test",
            body="body",
            source="example",
            published_at=datetime(2026, 6, 2),  # naive — no timezone
        )

def test_sentiment_score_clamped():
    s = SentimentScore(ticker="AAPL", score=9.9, label="positive", n_sentences=3, window_ewma=0.75)
    assert s.score == 1.0

def test_sentiment_label_validated():
    with pytest.raises(ValidationError):
        SentimentScore(ticker="AAPL", score=0.8, label="unknown", n_sentences=3, window_ewma=0.75)

def test_event_severity_bounds():
    with pytest.raises(ValidationError):
        Event(article_id="abc", category=EventCategory.EARNINGS_REPORT, severity=1.5)

def test_signal_direction():
    sig = InvestmentSignal(
        ticker="AAPL", direction="bullish", confidence=0.8,
        score=0.4, sentiment_component=0.5,
        event_component=0.3, price_component=0.1,
        evidence_ids=[], generated_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
    )
    assert sig.direction in ("bullish", "bearish", "neutral")

def test_signal_invalid_direction():
    with pytest.raises(ValidationError):
        InvestmentSignal(
            ticker="AAPL", direction="sideways", confidence=0.8,
            score=0.4, sentiment_component=0.5,
            event_component=0.3, price_component=0.1,
            evidence_ids=[], generated_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        )

def test_user_profile_risk_validation():
    with pytest.raises(ValidationError):
        UserProfile(investment_amount=1000, risk_appetite="unknown", time_horizon_months=12)

def test_investment_plan_allocation_sum():
    allocs = [
        Allocation(ticker="AAPL", amount=600.0, percentage=60.0, rationale="test"),
        Allocation(ticker="MSFT", amount=400.0, percentage=40.0, rationale="test"),
    ]
    plan = InvestmentPlan(
        total_amount=1000.0, allocations=allocs, risk_summary="test",
        expected_return_range=(5.0, 15.0), time_horizon_months=12,
        rebalance_trigger="monthly",
    )
    assert abs(sum(a.amount for a in plan.allocations) - plan.total_amount) < 0.01

def test_investment_plan_allocation_sum_mismatch():
    allocs = [Allocation(ticker="AAPL", amount=200.0, percentage=20.0, rationale="test")]
    with pytest.raises(ValidationError):
        InvestmentPlan(
            total_amount=1000.0, allocations=allocs, risk_summary="test",
            expected_return_range=(5.0, 15.0), time_horizon_months=12,
            rebalance_trigger="monthly",
        )
