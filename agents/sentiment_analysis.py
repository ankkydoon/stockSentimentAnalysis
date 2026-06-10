from datetime import datetime, timezone
from models.sentiment import SentimentScore
from agents.hf_client import hf_post
from config.settings import get_settings
from storage.supabase_store import SupabaseStore

LABEL_TO_SCORE = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}


def compute_ewma(previous: float, new_value: float, alpha: float = 0.3) -> float:
    return alpha * new_value + (1 - alpha) * previous


def aggregate_sentiment(hf_outputs: list[dict]) -> float:
    if not hf_outputs:
        return 0.0
    total_weight = sum(o["score"] for o in hf_outputs)
    if total_weight == 0:
        return 0.0
    return sum(LABEL_TO_SCORE.get(o["label"], 0.0) * o["score"] for o in hf_outputs) / total_weight


def sentiment_analysis_node(state: dict) -> dict:
    settings = get_settings()
    store = SupabaseStore(url=settings.supabase_url,
                          key=settings.supabase_key.get_secret_value())
    api_url = f"https://api-inference.huggingface.co/models/{settings.finbert_model_id}"
    run_date = state.get("run_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    ticker_sentences: dict[str, list[str]] = {}
    for article in state["deduplicated_articles"]:
        entities = state["article_entities"].get(article.id, [])
        linked_tickers = {e.ticker for e in entities if e.linked and e.ticker}
        sentences = [s.strip() for s in article.body.split(". ") if len(s.strip()) > 20][:20]
        for ticker in linked_tickers:
            ticker_sentences.setdefault(ticker, []).extend(sentences)

    sentiment_scores: list[SentimentScore] = []
    errors: list[str] = []
    for ticker, sentences in ticker_sentences.items():
        if not sentences:
            continue
        try:
            outputs = hf_post(api_url, {"inputs": sentences[:10]},
                              token=settings.hf_token.get_secret_value(),
                              retries=settings.hf_api_retries,
                              backoff_base=settings.hf_api_backoff_base)
        except Exception as exc:
            errors.append(f"FinBERT API error for {ticker}: {type(exc).__name__}: {str(exc)[:100]}")
            continue
        if isinstance(outputs, list) and outputs:
            flat = outputs if isinstance(outputs[0], dict) else [i for sub in outputs for i in sub]
            score = aggregate_sentiment(flat)
        else:
            score = 0.0
        previous_ewma = store.get_sentiment_ewma(ticker)
        ewma = compute_ewma(previous_ewma, score)
        store.upsert_sentiment_ts(ticker=ticker, date=run_date, ewma_score=ewma,
                                  n_articles=len(sentences))
        label: str
        if score > 0.1:
            label = "positive"
        elif score < -0.1:
            label = "negative"
        else:
            label = "neutral"
        sentiment_scores.append(SentimentScore(
            ticker=ticker, score=score, label=label,
            n_sentences=len(sentences), window_ewma=ewma,
        ))
    return {"sentiment_scores": sentiment_scores, "error_log": errors}
