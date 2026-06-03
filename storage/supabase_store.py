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
