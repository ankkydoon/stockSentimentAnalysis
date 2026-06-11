import logging
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO)

from config.settings import get_settings
from storage.supabase_store import SupabaseStore
from backtesting.optimizer import run_optimization

today = datetime.now(timezone.utc)
start = (today - timedelta(days=30)).strftime("%Y-%m-%d")
end = today.strftime("%Y-%m-%d")

settings = get_settings()
store = SupabaseStore(url=settings.supabase_url, key=settings.supabase_key.get_secret_value())
weights = run_optimization(store, start, end)
print("New weights:", weights)
