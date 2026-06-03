from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class InvestmentSignal(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    direction: Literal["bullish", "bearish", "neutral"]
    confidence: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=-1.0, le=1.0)
    sentiment_component: float = Field(ge=-1.0, le=1.0)
    event_component: float = Field(ge=-1.0, le=1.0)
    price_component: float = Field(ge=-1.0, le=1.0)
    evidence_ids: tuple[str, ...] = ()
    generated_at: datetime
    horizon_days: int = Field(default=5, ge=1)
