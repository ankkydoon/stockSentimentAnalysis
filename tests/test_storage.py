import pytest
from unittest.mock import MagicMock, patch
from storage.supabase_store import SupabaseStore


def test_store_init_requires_url_and_key():
    with pytest.raises(ValueError):
        SupabaseStore(url="", key="")

def test_store_init_requires_url():
    with pytest.raises(ValueError):
        SupabaseStore(url="", key="somekey")

def test_store_init_requires_key():
    with pytest.raises(ValueError):
        SupabaseStore(url="https://x.supabase.co", key="")

def test_upsert_article_calls_supabase():
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    with patch("storage.supabase_store.create_client", return_value=mock_client):
        store = SupabaseStore(url="https://x.supabase.co", key="key")
        from datetime import datetime, timezone
        from models.article import Article
        a = Article(url="https://ex.com/1", title="T", body="B",
                    source="ex", published_at=datetime(2026, 6, 2, tzinfo=timezone.utc))
        store.upsert_article(a)
    mock_client.table.assert_called_with("articles")

def test_article_exists_true():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "abc"}])
    with patch("storage.supabase_store.create_client", return_value=mock_client):
        store = SupabaseStore(url="https://x.supabase.co", key="key")
        assert store.article_exists("abc") is True

def test_article_exists_false():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    with patch("storage.supabase_store.create_client", return_value=mock_client):
        store = SupabaseStore(url="https://x.supabase.co", key="key")
        assert store.article_exists("missing") is False

def test_upsert_signal_uses_deterministic_id():
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    with patch("storage.supabase_store.create_client", return_value=mock_client):
        store = SupabaseStore(url="https://x.supabase.co", key="key")
        from datetime import datetime, timezone
        from models.signal import InvestmentSignal
        sig = InvestmentSignal(
            ticker="AAPL", direction="bullish", confidence=0.8,
            score=0.4, sentiment_component=0.5, event_component=0.3,
            price_component=0.1, evidence_ids=("abc",),
            generated_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        )
        store.upsert_signal(sig)
        call_args = mock_client.table.return_value.upsert.call_args[0][0]
    mock_client.table.assert_called_with("signals")
    assert call_args["id"] == sig.id  # deterministic, not random

def test_get_sentiment_ewma_returns_zero_when_empty():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    with patch("storage.supabase_store.create_client", return_value=mock_client):
        store = SupabaseStore(url="https://x.supabase.co", key="key")
        result = store.get_sentiment_ewma("AAPL")
    assert result == 0.0

def test_search_sp500_returns_ticker():
    mock_client = MagicMock()
    mock_client.rpc.return_value.execute.return_value = MagicMock(
        data=[{"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "similarity": 0.95}]
    )
    with patch("storage.supabase_store.create_client", return_value=mock_client):
        store = SupabaseStore(url="https://x.supabase.co", key="key")
        results = store.search_sp500([0.1] * 384, threshold=0.72)
    assert results[0]["ticker"] == "AAPL"

def test_search_sp500_returns_empty_on_no_match():
    mock_client = MagicMock()
    mock_client.rpc.return_value.execute.return_value = MagicMock(data=[])
    with patch("storage.supabase_store.create_client", return_value=mock_client):
        store = SupabaseStore(url="https://x.supabase.co", key="key")
        results = store.search_sp500([0.1] * 384, threshold=0.72)
    assert results == []
