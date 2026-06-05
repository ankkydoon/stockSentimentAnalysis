import re
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from models.entity import Entity
from config.settings import get_settings
from storage.supabase_store import SupabaseStore

FINANCIAL_CUES = ["$", "shares", "inc.", "corp.", "ltd.", "nasdaq", "nyse", "amex",
                  "ticker", "stock", "equity", "earnings", "dividend", "ipo", "etf"]

TICKER_PATTERN = re.compile(r'\$([A-Z]{1,5})\b|\((?:NASDAQ|NYSE|AMEX):\s*([A-Z]{1,5})\)')


def extract_ticker_patterns(text: str) -> list[str]:
    matches = TICKER_PATTERN.findall(text)
    return list({t1 or t2 for t1, t2 in matches if t1 or t2})


def has_financial_cue(text: str) -> bool:
    lower = text.lower()
    return any(cue in lower for cue in FINANCIAL_CUES)


@lru_cache(maxsize=1)
def _get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(get_settings().embedding_model_id)


def resolve_entity(raw_text: str, article_text: str, store: SupabaseStore) -> Entity:
    if not has_financial_cue(article_text):
        return Entity(raw_text=raw_text, linked=False)
    model = _get_embedding_model()
    embedding = model.encode(raw_text).tolist()
    threshold = get_settings().entity_similarity_threshold
    results = store.search_sp500(embedding, threshold=threshold)
    if results:
        best = results[0]
        return Entity(raw_text=raw_text, ticker=best["ticker"],
                      sector=best.get("sector"), similarity_score=best.get("similarity", 0.0),
                      linked=True)
    return Entity(raw_text=raw_text, linked=False)


def entity_recognition_node(state: dict) -> dict:
    settings = get_settings()
    store = SupabaseStore(url=settings.supabase_url,
                          key=settings.supabase_key.get_secret_value())

    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        nlp = None

    article_entities: dict[str, list[Entity]] = {}
    for article in state["deduplicated_articles"]:
        entities: list[Entity] = []
        combined_text = article.body + " " + article.title
        for ticker in extract_ticker_patterns(combined_text):
            entities.append(Entity(raw_text=ticker, ticker=ticker, linked=True,
                                   similarity_score=1.0))
        if nlp:
            doc = nlp(article.body[:5000])
            for ent in doc.ents:
                if ent.label_ == "ORG":  # PER excluded — person names don't match sp500
                    resolved = resolve_entity(ent.text, article.body, store)
                    entities.append(resolved)
        article_entities[article.id] = entities
    return {"article_entities": article_entities}
