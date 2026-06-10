from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hf_token: SecretStr = SecretStr("")
    supabase_url: str = ""
    supabase_key: SecretStr = SecretStr("")
    edgar_user_agent: str = "stockSentimentAnalysis/1.0 user@example.com"

    max_articles_per_run: int = 50
    minhash_threshold: float = 0.72
    high_severity_threshold: float = 0.7

    finbert_model_id: str = "ProsusAI/finbert"
    mistral_model_id: str = "mistralai/Mistral-7B-Instruct-v0.3"
    mistral_provider: str = "novita"
    embedding_model_id: str = "sentence-transformers/all-MiniLM-L6-v2"

    hf_api_retries: int = 3
    hf_api_backoff_base: float = 2.0
    entity_similarity_threshold: float = 0.72


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
