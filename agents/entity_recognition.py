import re
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from models.entity import Entity
from config.settings import get_settings
from storage.supabase_store import SupabaseStore

FINANCIAL_CUES = ["$", "shares", "inc.", "corp.", "ltd.", "nasdaq", "nyse", "amex",
                  "ticker", "stock", "equity", "earnings", "dividend", "ipo", "etf"]

TICKER_PATTERN = re.compile(r'\$([A-Z]{1,5})\b|\((?:NASDAQ|NYSE|AMEX):\s*([A-Z]{1,5})\)')

# Fallback name→ticker map for well-known companies (used when Supabase is not seeded)
NAME_TO_TICKER: dict[str, tuple[str, str]] = {
    "apple": ("AAPL", "Technology"), "microsoft": ("MSFT", "Technology"),
    "nvidia": ("NVDA", "Technology"), "google": ("GOOGL", "Technology"),
    "alphabet": ("GOOGL", "Technology"), "amazon": ("AMZN", "Consumer Discretionary"),
    "meta": ("META", "Technology"), "tesla": ("TSLA", "Consumer Discretionary"),
    "berkshire": ("BRK-B", "Financials"), "eli lilly": ("LLY", "Healthcare"),
    "jpmorgan": ("JPM", "Financials"), "jp morgan": ("JPM", "Financials"),
    "johnson & johnson": ("JNJ", "Healthcare"), "johnson and johnson": ("JNJ", "Healthcare"),
    "unitedhealth": ("UNH", "Healthcare"), "exxon": ("XOM", "Energy"),
    "visa": ("V", "Financials"), "mastercard": ("MA", "Financials"),
    "procter & gamble": ("PG", "Consumer Staples"), "home depot": ("HD", "Consumer Discretionary"),
    "chevron": ("CVX", "Energy"), "abbvie": ("ABBV", "Healthcare"),
    "broadcom": ("AVGO", "Technology"), "costco": ("COST", "Consumer Staples"),
    "walmart": ("WMT", "Consumer Staples"), "netflix": ("NFLX", "Communication Services"),
    "adobe": ("ADBE", "Technology"), "salesforce": ("CRM", "Technology"),
    "amd": ("AMD", "Technology"), "advanced micro devices": ("AMD", "Technology"),
    "intel": ("INTC", "Technology"), "qualcomm": ("QCOM", "Technology"),
    "micron": ("MU", "Technology"), "super micro": ("SMCI", "Technology"),
    "spacex": ("SPCE", "Industrials"), "palantir": ("PLTR", "Technology"),
    "coinbase": ("COIN", "Financials"), "paypal": ("PYPL", "Financials"),
    "uber": ("UBER", "Consumer Discretionary"), "lyft": ("LYFT", "Consumer Discretionary"),
    "ford": ("F", "Consumer Discretionary"), "gm": ("GM", "Consumer Discretionary"),
    "general motors": ("GM", "Consumer Discretionary"), "boeing": ("BA", "Industrials"),
    "at&t": ("T", "Communication Services"), "verizon": ("VZ", "Communication Services"),
    "disney": ("DIS", "Communication Services"), "comcast": ("CMCSA", "Communication Services"),
    "pfizer": ("PFE", "Healthcare"), "moderna": ("MRNA", "Healthcare"),
    "goldman sachs": ("GS", "Financials"), "morgan stanley": ("MS", "Financials"),
    "bank of america": ("BAC", "Financials"), "citigroup": ("C", "Financials"),
    "wells fargo": ("WFC", "Financials"), "blackrock": ("BLK", "Financials"),
}


def _name_to_ticker_lookup(name: str) -> tuple[str, str] | None:
    lower = name.lower().strip()
    # Exact match only — no partial matching to avoid false positives
    return NAME_TO_TICKER.get(lower)


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
    # Exact match in hardcoded map (high confidence, no ambiguity)
    match = _name_to_ticker_lookup(raw_text)
    if match:
        ticker, sector = match
        return Entity(raw_text=raw_text, ticker=ticker, sector=sector,
                      similarity_score=0.95, linked=True)
    # Two-stage semantic search:
    # Stage 1: entity name alone must be a close match (catches "Apple" → AAPL)
    # Stage 2: entity name + context used for scoring (improves ranking)
    if store._enabled:
        model = _get_embedding_model()
        settings = get_settings()

        # Stage 1: name-only match — must pass a high threshold
        name_embedding = model.encode(raw_text, normalize_embeddings=True).tolist()
        name_results = store.search_sp500(name_embedding, threshold=0.75)
        if not name_results:
            # Entity name not close to any S&P 500 company — skip
            return Entity(raw_text=raw_text, linked=False)

        # Stage 2: re-rank using name + article context
        context = f"{raw_text}. {article_text[:300]}"
        ctx_embedding = model.encode(context, normalize_embeddings=True).tolist()
        ctx_results = store.search_sp500(ctx_embedding, threshold=settings.entity_similarity_threshold)

        # Use context result if it agrees with name result (same ticker)
        best = ctx_results[0] if ctx_results else name_results[0]
        print(f"[entity] '{raw_text}' → {best['ticker']} (similarity={best.get('similarity', 0):.3f})")
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
