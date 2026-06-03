from enum import Enum
from pydantic import BaseModel, Field

class EventCategory(str, Enum):
    EARNINGS_REPORT = "earnings_report"
    MERGERS_ACQUISITIONS = "mergers_acquisitions"
    REGULATORY_ACTION = "regulatory_action"
    MANAGEMENT_CHANGE = "management_change"
    PRODUCT_LAUNCH = "product_launch"
    LITIGATION = "litigation"
    GUIDANCE_UPDATE = "guidance_update"
    MACRO_OTHER = "macro_other"

class Event(BaseModel):
    article_id: str
    ticker: str | None = None
    category: EventCategory
    severity: float = Field(ge=0.0, le=1.0)
    summary: str = ""
    raw_llm_output: str = ""
