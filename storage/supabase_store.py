from supabase import create_client, Client
from models.article import Article
from models.signal import InvestmentSignal


class SupabaseStore:
    def __init__(self, url: str, key: str):
        if not url or not key:
            raise ValueError("Supabase URL and key are required")
        self.client: Client = create_client(url, key)

    def upsert_article(self, article: Article) -> None:
        self.client.table("articles").upsert({
            "id": article.id,
            "url": article.url,
            "title": article.title,
            "source": article.source,
            "published_at": article.published_at.isoformat(),
            "is_duplicate": article.is_duplicate,
        }).execute()

    def article_exists(self, article_id: str) -> bool:
        result = self.client.table("articles").select("id").eq("id", article_id).execute()
        return len(result.data) > 0

    def upsert_signal(self, signal: InvestmentSignal) -> None:
        import uuid
        self.client.table("signals").upsert({
            "id": str(uuid.uuid4()),
            "ticker": signal.ticker,
            "signal": signal.direction,
            "confidence": signal.confidence,
            "score": signal.score,
            "components": {
                "sentiment": signal.sentiment_component,
                "event": signal.event_component,
                "price": signal.price_component,
            },
            "evidence_ids": list(signal.evidence_ids),
            "generated_at": signal.generated_at.isoformat(),
            "horizon_days": signal.horizon_days,
        }).execute()

    def upsert_sentiment_ts(self, ticker: str, date: str, ewma_score: float, n_articles: int) -> None:
        self.client.table("entity_sentiment_ts").upsert({
            "ticker": ticker,
            "date": date,
            "ewma_score": ewma_score,
            "n_articles": n_articles,
        }).execute()

    def get_sentiment_ewma(self, ticker: str) -> float:
        result = (self.client.table("entity_sentiment_ts")
                  .select("ewma_score")
                  .eq("ticker", ticker)
                  .order("date", desc=True)
                  .limit(1)
                  .execute())
        if result.data:
            return result.data[0]["ewma_score"]
        return 0.0

    def upsert_sp500_embedding(self, ticker: str, name: str, sector: str, summary: str, embedding: list[float]) -> None:
        self.client.table("sp500_embeddings").upsert({
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "summary": summary,
            "embedding": embedding,
        }).execute()

    def search_sp500(self, embedding: list[float], threshold: float = 0.72, limit: int = 1) -> list[dict]:
        result = self.client.rpc("match_sp500", {
            "query_embedding": embedding,
            "match_threshold": threshold,
            "match_count": limit,
        }).execute()
        return result.data or []
