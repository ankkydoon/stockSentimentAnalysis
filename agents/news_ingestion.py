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


def _is_blocked(text: str) -> bool:
    """Return True if the body looks like a CAPTCHA/JS-wall page rather than article text."""
    if not text or len(text) < 200:
        return True
    lowered = text[:500].lower()
    blocked_signals = ["enable js", "enable javascript", "captcha", "please enable", "disable any ad blocker", "geo.captcha-delivery"]
    return any(s in lowered for s in blocked_signals)


def _fetch_body(url: str, rss_summary: str = "") -> str:
    body = ""
    try:
        import newspaper
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        article = newspaper.Article(url, browser_user_agent=ua)
        article.download()
        article.parse()
        body = article.text or ""
    except Exception:
        pass

    if _is_blocked(body):
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(url, timeout=15)
            body = resp.text[:5000]
        except Exception:
            pass

    # Fall back to RSS summary if body is still blocked or empty
    if _is_blocked(body) and rss_summary:
        return rss_summary
    return body


def _parse_feed(feed_url: str, settings) -> list:
    if "sec.gov" in feed_url:
        return feedparser.parse(feed_url, request_headers={
            "User-Agent": settings.edgar_user_agent
        }).entries
    return feedparser.parse(feed_url).entries


def fetch_articles(settings=None) -> list[Article]:
    if settings is None:
        settings = get_settings()
    articles: list[Article] = []
    for feed_url in RSS_FEEDS:
        try:
            entries = _parse_feed(feed_url, settings)
            for entry in entries:
                url = entry.get("link", "")
                if not url:
                    continue
                rss_summary = entry.get("summary", "") or entry.get("description", "")
                body = _fetch_body(url, rss_summary=rss_summary)
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
