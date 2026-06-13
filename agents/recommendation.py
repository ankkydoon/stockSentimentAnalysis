from __future__ import annotations

import uuid
from typing import Literal

import yfinance as yf

from config.settings import get_settings
from models.recommendation import Allocation, InvestmentPlan, UserProfile
from models.signal import InvestmentSignal
from storage.supabase_store import SupabaseStore

def _load_sp500_universe(store: SupabaseStore) -> dict[str, str]:
    """Return {ticker: sector} for all rows in sp500_embeddings. Falls back to empty dict."""
    if not store._enabled:
        return {}
    try:
        result = store.client.table("sp500_embeddings").select("ticker, sector").execute()
        return {row["ticker"]: row["sector"] for row in (result.data or [])}
    except Exception:
        return {}

_FALLBACK_RETURN = 0.07  # 7% annual fallback


def _get_annual_return(ticker: str) -> float:
    try:
        hist = yf.Ticker(ticker).history(period="1y")["Close"]
        if len(hist) < 2:
            return _FALLBACK_RETURN
        return float((hist.iloc[-1] - hist.iloc[0]) / hist.iloc[0])
    except Exception:
        return _FALLBACK_RETURN


def _filter_signals(
    signals: list[InvestmentSignal],
    profile: UserProfile,
    ticker_sector: dict[str, str],
) -> list[InvestmentSignal]:
    # Filter to S&P 500 only, exclude user-excluded tickers, prefer non-neutral
    candidates = [
        s for s in signals
        if s.ticker not in profile.exclude_tickers
        and (not ticker_sector or s.ticker in ticker_sector)
    ]

    # Prefer bullish, fall back to any non-neutral, fall back to all
    bullish = [s for s in candidates if s.direction == "bullish"]
    non_neutral = [s for s in candidates if s.direction != "neutral"]
    candidates = bullish or non_neutral or candidates

    if profile.preferred_sectors:
        preferred_upper = {sec.lower() for sec in profile.preferred_sectors}
        sector_filtered = [
            s for s in candidates
            if ticker_sector.get(s.ticker, "").lower() in preferred_upper
        ]
        candidates = sector_filtered if sector_filtered else candidates

    # Always return top 3 by confidence
    return sorted(candidates, key=lambda s: s.confidence, reverse=True)[:3]



def _weighted_stock_allocations(
    signals: list[InvestmentSignal],
    total_stock_amount: float,
) -> list[Allocation]:
    if not signals:
        return []
    total_confidence = sum(s.confidence for s in signals)
    allocations: list[Allocation] = []
    for sig in signals:
        weight = sig.confidence / total_confidence if total_confidence > 0 else 1.0 / len(signals)
        amount = round(total_stock_amount * weight, 2)
        percentage = round(weight * 100, 4)
        rationale = (
            f"{sig.ticker}: {sig.direction} signal, confidence {sig.confidence:.0%}, "
            f"{sig.horizon_days}-day horizon"
        )
        allocations.append(
            Allocation(ticker=sig.ticker, amount=amount, percentage=percentage, rationale=rationale)
        )
    return allocations



def _build_allocations(
    risk_appetite: Literal["conservative", "moderate", "aggressive"],
    signals: list[InvestmentSignal],
    total_amount: float,
) -> list[Allocation]:
    # signals is already top-3 sorted by confidence — allocate 100% across them
    all_allocations = _weighted_stock_allocations(signals, total_amount)

    # Fix floating-point rounding: adjust last allocation so amounts sum exactly
    if all_allocations:
        current_sum = sum(a.amount for a in all_allocations)
        diff = round(total_amount - current_sum, 2)
        if diff != 0.0:
            last = all_allocations[-1]
            adjusted_amount = round(last.amount + diff, 2)
            adjusted_pct = round(adjusted_amount / total_amount * 100, 4)
            all_allocations[-1] = Allocation(
                ticker=last.ticker,
                amount=adjusted_amount,
                percentage=adjusted_pct,
                rationale=last.rationale,
            )

    return all_allocations


def _risk_summary(
    risk_appetite: Literal["conservative", "moderate", "aggressive"],
    n_stocks: int,
    has_etfs: bool,
) -> str:
    if risk_appetite == "conservative":
        return (
            f"Conservative allocation: 60% in broad-market ETFs (SPY, BND) to limit downside, "
            f"40% across {n_stocks} high-confidence bullish equities."
        )
    if risk_appetite == "moderate":
        return (
            f"Moderate allocation: 40% in SPY for diversified exposure, "
            f"60% across {n_stocks} high-confidence bullish equities."
        )
    return (
        f"Aggressive allocation: 100% in {n_stocks} high-confidence bullish equities "
        f"with no ETF buffer. Higher reward potential with higher volatility risk."
    )


def recommendation_node(state: dict) -> dict:
    raw_profile = state.get("user_profile")

    # Use defaults when no user profile provided (e.g. scheduled pipeline runs)
    if raw_profile is None:
        profile = UserProfile(investment_amount=10000.0, risk_appetite="moderate", time_horizon_months=12)
    else:
        profile = raw_profile if isinstance(raw_profile, UserProfile) else UserProfile(**raw_profile)

    settings = get_settings()
    store = SupabaseStore(url=settings.supabase_url, key=settings.supabase_key.get_secret_value())
    ticker_sector = _load_sp500_universe(store)

    signals: list[InvestmentSignal] = state.get("signals", [])
    filtered = _filter_signals(signals, profile, ticker_sector)

    if not filtered:
        return {"investment_plan": None}

    allocations = _build_allocations(
        profile.risk_appetite, filtered, profile.investment_amount
    )

    all_tickers = [a.ticker for a in allocations] or ["SPY"]
    individual_tickers = all_tickers

    returns = [_get_annual_return(t) for t in all_tickers]
    min_r = min(returns)
    max_r = max(returns)
    expected_return_range = (round(min_r * 0.7, 4), round(max_r * 1.3, 4))

    n_stocks = len(individual_tickers)
    risk_summary = _risk_summary(profile.risk_appetite, n_stocks, False)

    rebalance_trigger: Literal["monthly", "on_new_signal"] = (
        "monthly" if profile.time_horizon_months >= 6 else "on_new_signal"
    )

    plan = InvestmentPlan(
        total_amount=profile.investment_amount,
        allocations=allocations,
        risk_summary=risk_summary,
        expected_return_range=expected_return_range,
        time_horizon_months=profile.time_horizon_months,
        rebalance_trigger=rebalance_trigger,
    )

    _try_persist(plan)
    return {"investment_plan": plan}


def _try_persist(plan: InvestmentPlan) -> None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key.get_secret_value():
        return
    try:
        store = SupabaseStore(
            url=settings.supabase_url,
            key=settings.supabase_key.get_secret_value(),
        )
        # SupabaseStore does not expose upsert_plan; skip persistence silently.
        if hasattr(store, "upsert_plan"):
            store.upsert_plan(plan)  # type: ignore[attr-defined]
    except Exception:
        pass
