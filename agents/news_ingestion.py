import feedparser
from datetime import datetime, timezone
from datasketch import MinHash, MinHashLSH
from models.article import Article
from config.feeds import RSS_FEEDS
from config.settings import get_settings


def _minhash(text: str, num_perm: int = 128) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for shingle in {text[i:i+5] for i in range(max(1, len(text) - 4))}:
        m.update(shingle.encode())
    return m


def deduplicate(articles: list[Article], threshold: float = 0.72) -> list[Article]:
    lsh = MinHashLSH(threshold=threshold, num_perm=128)
    seen_ids: set[str] = set()
    unique: list[Article] = []
    for article in articles:
        if article.id in seen_ids:
            continue
        m = _minhash(article.body or article.title)
        candidates = lsh.query(m)
        if not candidates:
            try:
                lsh.insert(article.id, m)
            except ValueError:
                pass  # duplicate key — already seen via different path
            seen_ids.add(article.id)
            unique.append(article)
    return unique


def _parse_date(entry) -> datetime:
    import email.utils
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                t = email.utils.parsedate_to_datetime(val)
                return t.astimezone(timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)


def _fetch_body(url: str) -> str:
    try:
        import newspaper
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        article = newspaper.Article(url, browser_user_agent=ua)
        article.download()
        article.parse()
        return article.text or ""
    except Exception:
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(url, timeout=15)
            return resp.text[:5000]
        except Exception:
            return ""


def fetch_articles(settings=None) -> list[Article]:
    if settings is None:
        settings = get_settings()
    articles: list[Article] = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                url = entry.get("link", "")
                if not url:
                    continue
                body = _fetch_body(url)
                articles.append(Article(
                    url=url,
                    title=entry.get("title", ""),
                    body=body,
                    source=feed_url,
                    published_at=_parse_date(entry),
                ))
                if len(articles) >= settings.max_articles_per_run:
                    return articles
        except Exception:
            continue
    return articles


def news_ingestion_node(state: dict) -> dict:
    settings = get_settings()
    articles = fetch_articles(settings)
    deduped = deduplicate(articles, threshold=settings.minhash_threshold)
    return {"raw_articles": articles, "deduplicated_articles": deduped}
