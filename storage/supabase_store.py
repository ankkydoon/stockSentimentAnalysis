import uuid
from supabase import create_client, Client
from models.article import Article
from models.signal import InvestmentSignal


class SupabaseStore:
    def __init__(self, url: str, key: str):
        url = (url or "").strip().rstrip("/")
        if "/rest/" in url:
            url = url.split("/rest/")[0]
        self._enabled = False
        self.client: Client | None = None
        if url and key:
            try:
                self.client = create_client(url, key)
                self._enabled = True
                print(f"[store] Supabase connected: {url[:40]}...")
            except Exception as e:
                print(f"[store] ERROR connecting to Supabase: {e}")
        else:
            print("[store] WARNING: SUPABASE_URL or SUPABASE_KEY not set — running in no-op mode")

    def upsert_article(self, article: Article) -> None:
        if not self._enabled:
            return
        self.client.table("articles").upsert({
            "id": article.id,
            "url": article.url,
            "title": article.title,
            "source": article.source,
            "published_at": article.published_at.isoformat(),
            "is_duplicate": article.is_duplicate,
        }).execute()

    def article_exists(self, article_id: str) -> bool:
        if not self._enabled:
            return False
        result = self.client.table("articles").select("id").eq("id", article_id).execute()
        return len(result.data) > 0

    def upsert_signal(self, signal: InvestmentSignal) -> None:
        if not self._enabled:
            print(f"[store] WARNING: Supabase not enabled, skipping upsert_signal for {signal.ticker}")
            return
        try:
            self.client.table("signals").upsert({
                "id": signal.id,
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
            print(f"[store] upserted signal {signal.ticker} to Supabase")
        except Exception as e:
            print(f"[store] ERROR upserting signal {signal.ticker}: {e}")

    def upsert_sentiment_ts(self, ticker: str, date: str, ewma_score: float, n_articles: int) -> None:
        if not self._enabled:
            return
        self.client.table("entity_sentiment_ts").upsert({
            "ticker": ticker,
            "date": date,
            "ewma_score": ewma_score,
            "n_articles": n_articles,
        }).execute()

    def get_sentiment_ewma(self, ticker: str) -> float:
        if not self._enabled:
            return 0.0
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
        if not self._enabled:
            return
        self.client.table("sp500_embeddings").upsert({
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "summary": summary,
            "embedding": embedding,
        }).execute()

    def search_sp500(self, embedding: list[float], threshold: float = 0.72, limit: int = 1) -> list[dict]:
        if not self._enabled:
            return []
        result = self.client.rpc("match_sp500", {
            "query_embedding": embedding,
            "match_threshold": threshold,
            "match_count": limit,
        }).execute()
        return result.data or []

    _DEFAULT_WEIGHTS = {"w_sentiment": 0.50, "w_event": 0.35, "w_price": 0.15}

    def get_weights(self) -> dict:
        if not self._enabled:
            return dict(self._DEFAULT_WEIGHTS)
        result = (
            self.client.table("signal_weights")
            .select("w_sentiment, w_event, w_price")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return dict(self._DEFAULT_WEIGHTS)

    def save_weights(self, w_sentiment: float, w_event: float, w_price: float,
                     signals_evaluated: int, directional_accuracy: float, notes: str = "") -> None:
        if not self._enabled:
            return
        self.client.table("signal_weights").insert({
            "w_sentiment": round(w_sentiment, 4),
            "w_event": round(w_event, 4),
            "w_price": round(w_price, 4),
            "signals_evaluated": signals_evaluated,
            "directional_accuracy": round(directional_accuracy, 4),
            "notes": notes,
        }).execute()
