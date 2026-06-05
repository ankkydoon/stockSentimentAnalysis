from datetime import datetime, timezone
from models.article import Article
from agents.news_ingestion import deduplicate


def make_article(url: str, body: str = "body") -> Article:
    return Article(url=url, title="title", body=body, source="test",
                   published_at=datetime(2026, 6, 2, tzinfo=timezone.utc))


def test_deduplicate_removes_same_url():
    a1 = make_article("https://ex.com/1")
    a2 = make_article("https://ex.com/1")  # same URL = same SHA256 id
    result = deduplicate([a1, a2], threshold=0.72)
    assert len(result) == 1


def test_deduplicate_keeps_different_articles():
    a1 = make_article("https://ex.com/1", body="Apple earnings beat estimates")
    a2 = make_article("https://ex.com/2", body="Microsoft acquires gaming company")
    result = deduplicate([a1, a2], threshold=0.72)
    assert len(result) == 2


def test_deduplicate_excludes_duplicate_from_result():
    a1 = make_article("https://ex.com/1")
    a2 = make_article("https://ex.com/1")
    result = deduplicate([a1, a2], threshold=0.72)
    # only the first article kept; second (same id) excluded
    assert len(result) == 1
    assert result[0].id == a1.id
