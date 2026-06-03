from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class UserProfile(BaseModel):
    investment_amount: float = Field(gt=0)
    risk_appetite: Literal["conservative", "moderate", "aggressive"]
    time_horizon_months: int = Field(ge=1)
    preferred_sectors: list[str] = []
    exclude_tickers: list[str] = []

class Allocation(BaseModel):
    ticker: str
    amount: float = Field(ge=0)
    percentage: float = Field(ge=0.0, le=100.0)
    rationale: str

class InvestmentPlan(BaseModel):
    total_amount: float = Field(gt=0)
    allocations: list[Allocation]
    risk_summary: str
    expected_return_range: tuple[float, float]
    time_horizon_months: int = Field(ge=1)
    rebalance_trigger: Literal["monthly", "on_new_signal"]
    disclaimer: str = "Educational use only. Not investment advice."

    @model_validator(mode="after")
    def validate_allocations_sum(self) -> "InvestmentPlan":
        if self.allocations:
            total = sum(a.amount for a in self.allocations)
            if abs(total - self.total_amount) > 0.01:
                raise ValueError(
                    f"Allocation amounts sum to {total:.2f} but total_amount is {self.total_amount:.2f}"
                )
        return self
