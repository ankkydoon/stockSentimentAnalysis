from pydantic import BaseModel, field_validator


class SentimentScore(BaseModel):
    ticker: str
    score: float
    label: str
    n_sentences: int
    window_ewma: float

    @field_validator("score", "window_ewma")
    @classmethod
    def clamp(cls, v: float) -> float:
        return max(-1.0, min(1.0, v))
