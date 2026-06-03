from pydantic import BaseModel


class Entity(BaseModel):
    raw_text: str
    ticker: str | None = None
    sector: str | None = None
    similarity_score: float = 0.0
    linked: bool = False
