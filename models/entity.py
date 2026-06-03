from pydantic import BaseModel, ConfigDict, Field

class Entity(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_text: str
    ticker: str | None = None
    sector: str | None = None
    similarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    linked: bool = False
