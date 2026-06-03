"""Seed 50 synthetic historical signals for backtest validation on day 1."""
import random
from datetime import datetime, timedelta, timezone
from config.settings import get_settings
from storage.supabase_store import SupabaseStore
from models.signal import InvestmentSignal

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "JNJ", "V"]
DIRECTIONS = ["bullish", "bearish", "neutral"]

def main() -> None:
    random.seed(42)
    settings = get_settings()
    store = SupabaseStore(url=settings.supabase_url, key=settings.supabase_key.get_secret_value())
    base_date = datetime.now(timezone.utc) - timedelta(days=60)
    for i in range(50):
        direction = random.choice(DIRECTIONS)
        score = round(random.uniform(-0.8, 0.8), 3)
        sig = InvestmentSignal(
            ticker=random.choice(TICKERS),
            direction=direction,
            confidence=round(random.uniform(0.5, 0.95), 2),
            score=score,
            sentiment_component=round(random.uniform(-1, 1), 3),
            event_component=round(random.uniform(-1, 1), 3),
            price_component=round(random.uniform(-1, 1), 3),
            evidence_ids=(f"synthetic_{i}",),
            generated_at=base_date + timedelta(days=i),
        )
        store.upsert_signal(sig)
        print(f"Seeded signal {i+1}/50: {sig.ticker} {sig.direction}")
    print("Done. Synthetic backtest signals seeded.")

if __name__ == "__main__":
    main()
