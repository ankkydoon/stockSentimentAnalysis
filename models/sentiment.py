from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class SentimentScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    score: float
    label: Literal["positive", "negative", "neutral"]
    n_sentences: int = Field(ge=0)
    window_ewma: float

    @field_validator("score", "window_ewma")
    @classmethod
    def clamp(cls, v: float) -> float:
        return max(-1.0, min(1.0, v))
