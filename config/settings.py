from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hf_token: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    edgar_user_agent: str = "stockSentimentAnalysis/1.0 user@example.com"

    max_articles_per_run: int = 50
    minhash_threshold: float = 0.72
    high_severity_threshold: float = 0.7

    finbert_model_id: str = "ProsusAI/finbert"
    mistral_model_id: str = "mistralai/Mistral-7B-Instruct-v0.2"
    embedding_model_id: str = "sentence-transformers/all-MiniLM-L6-v2"

    hf_api_retries: int = 3
    hf_api_backoff_base: float = 2.0
