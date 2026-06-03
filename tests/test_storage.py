import pytest
from unittest.mock import MagicMock, patch
from storage.supabase_store import SupabaseStore

def test_store_init_requires_url_and_key():
    with pytest.raises(Exception):
        SupabaseStore(url="", key="")

def test_upsert_article_calls_supabase():
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    with patch("storage.supabase_store.create_client", return_value=mock_client):
        store = SupabaseStore(url="https://x.supabase.co", key="key")
        from datetime import datetime, timezone
        from models.article import Article
        a = Article(url="https://ex.com/1", title="T", body="B",
                    source="ex", published_at=datetime(2026,6,2,tzinfo=timezone.utc))
        store.upsert_article(a)
    mock_client.table.assert_called_with("articles")

def test_upsert_signal_calls_supabase():
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    with patch("storage.supabase_store.create_client", return_value=mock_client):
        store = SupabaseStore(url="https://x.supabase.co", key="key")
        from datetime import datetime, timezone
        from models.signal import InvestmentSignal
        sig = InvestmentSignal(
            ticker="AAPL", direction="bullish", confidence=0.8,
            score=0.4, sentiment_component=0.5, event_component=0.3,
            price_component=0.1, evidence_ids=["abc"],
            generated_at=datetime(2026,6,2,tzinfo=timezone.utc),
        )
        store.upsert_signal(sig)
    mock_client.table.assert_called_with("signals")

def test_get_sentiment_ewma_returns_zero_when_empty():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    with patch("storage.supabase_store.create_client", return_value=mock_client):
        store = SupabaseStore(url="https://x.supabase.co", key="key")
        result = store.get_sentiment_ewma("AAPL")
    assert result == 0.0
