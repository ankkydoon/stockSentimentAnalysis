from typing import Literal
from pydantic import BaseModel


class UserProfile(BaseModel):
    investment_amount: float
    risk_appetite: Literal["conservative", "moderate", "aggressive"]
    time_horizon_months: int
    preferred_sectors: list[str] = []
    exclude_tickers: list[str] = []


class Allocation(BaseModel):
    ticker: str
    amount: float
    percentage: float
    rationale: str


class InvestmentPlan(BaseModel):
    total_amount: float
    allocations: list[Allocation]
    risk_summary: str
    expected_return_range: tuple[float, float]
    time_horizon_months: int
    rebalance_trigger: Literal["monthly", "on_new_signal"]
    disclaimer: str = "Educational use only. Not investment advice."
