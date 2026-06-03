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
