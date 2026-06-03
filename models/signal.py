from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class InvestmentSignal(BaseModel):
    ticker: str
    direction: Literal["bullish", "bearish", "neutral"]
    confidence: float
    score: float
    sentiment_component: float
    event_component: float
    price_component: float
    evidence_ids: list[str]
    generated_at: datetime
    horizon_days: int = 5
