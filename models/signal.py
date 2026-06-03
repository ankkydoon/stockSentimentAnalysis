import hashlib
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class InvestmentSignal(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = ""
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

    @model_validator(mode="after")
    def set_id(self) -> "InvestmentSignal":
        derived = hashlib.sha256(
            f"{self.ticker}:{self.generated_at.isoformat()}".encode()
        ).hexdigest()
        object.__setattr__(self, "id", derived)
        return self
