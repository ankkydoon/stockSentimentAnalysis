"""Run once to seed sp500_embeddings in Supabase. Re-run manually when S&P 500 constituents change."""
import time
import pandas as pd
import yfinance as yf
from sentence_transformers import SentenceTransformer
from config.settings import get_settings
from storage.supabase_store import SupabaseStore

SP500_WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

def get_sp500_tickers() -> list[dict]:
    tables = pd.read_html(SP500_WIKI)
    df = tables[0]
    return df[["Symbol", "Security", "GICS Sector"]].rename(
        columns={"Symbol": "ticker", "Security": "name", "GICS Sector": "sector"}
    ).to_dict("records")

def get_summary(ticker: str) -> str:
    try:
        info = yf.Ticker(ticker).info
        return info.get("longBusinessSummary", "")[:500]
    except Exception:
        return ""

def main() -> None:
    settings = get_settings()
    store = SupabaseStore(url=settings.supabase_url, key=settings.supabase_key.get_secret_value())
    model = SentenceTransformer(settings.embedding_model_id)
    companies = get_sp500_tickers()
    for i, co in enumerate(companies):
        summary = get_summary(co["ticker"])
        text = f"{co['name']} ({co['ticker']}) — {co['sector']}. {summary}"
        embedding = model.encode(text).tolist()
        store.upsert_sp500_embedding(
            ticker=co["ticker"], name=co["name"],
            sector=co["sector"], summary=summary, embedding=embedding,
        )
        print(f"[{i+1}/{len(companies)}] Seeded {co['ticker']}")
        if (i + 1) % 10 == 0:
            time.sleep(1)
    print("Done. sp500_embeddings seeded.")

if __name__ == "__main__":
    main()
