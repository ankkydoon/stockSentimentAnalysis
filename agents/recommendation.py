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

_ETF_SPY = "SPY"
_ETF_BND = "BND"
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
    candidates = [
        s for s in signals
        if s.direction == "bullish"
        and s.confidence >= 0.6
        and s.ticker not in profile.exclude_tickers
        and (not ticker_sector or s.ticker in ticker_sector)  # must be in S&P 500
    ]

    if profile.preferred_sectors:
        preferred_upper = {sec.lower() for sec in profile.preferred_sectors}
        sector_filtered = [
            s for s in candidates
            if ticker_sector.get(s.ticker, "").lower() in preferred_upper
        ]
        candidates = sector_filtered if sector_filtered else candidates

    return candidates


def _top_n_by_confidence(signals: list[InvestmentSignal], n: int) -> list[InvestmentSignal]:
    return sorted(signals, key=lambda s: s.confidence, reverse=True)[:n]


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


def _etf_rationale(ticker: str) -> str:
    if ticker == _ETF_SPY:
        return f"{ticker}: broad market ETF (S&P 500) for diversified exposure"
    if ticker == _ETF_BND:
        return f"{ticker}: bond ETF for capital preservation and income"
    return f"{ticker}: ETF allocation"


def _build_allocations(
    risk_appetite: Literal["conservative", "moderate", "aggressive"],
    signals: list[InvestmentSignal],
    total_amount: float,
) -> list[Allocation]:
    if risk_appetite == "conservative":
        top = _top_n_by_confidence(signals, 3)
        etf_amount = round(total_amount * 0.60, 2)
        stock_amount = total_amount - etf_amount

        spy_amount = round(etf_amount * 0.50, 2)
        bnd_amount = round(etf_amount - spy_amount, 2)

        etf_allocations = [
            Allocation(
                ticker=_ETF_SPY,
                amount=spy_amount,
                percentage=round(spy_amount / total_amount * 100, 4),
                rationale=_etf_rationale(_ETF_SPY),
            ),
            Allocation(
                ticker=_ETF_BND,
                amount=bnd_amount,
                percentage=round(bnd_amount / total_amount * 100, 4),
                rationale=_etf_rationale(_ETF_BND),
            ),
        ]
        stock_allocations = _weighted_stock_allocations(top, stock_amount)

    elif risk_appetite == "moderate":
        top = _top_n_by_confidence(signals, 5)
        etf_amount = round(total_amount * 0.40, 2)
        stock_amount = total_amount - etf_amount

        etf_allocations = [
            Allocation(
                ticker=_ETF_SPY,
                amount=etf_amount,
                percentage=round(etf_amount / total_amount * 100, 4),
                rationale=_etf_rationale(_ETF_SPY),
            )
        ]
        stock_allocations = _weighted_stock_allocations(top, stock_amount)

    else:  # aggressive
        top = _top_n_by_confidence(signals, 7)
        etf_allocations = []
        stock_allocations = _weighted_stock_allocations(top, total_amount)

    all_allocations = etf_allocations + stock_allocations

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
    if raw_profile is None:
        return {"investment_plan": None}

    profile: UserProfile = (
        raw_profile if isinstance(raw_profile, UserProfile) else UserProfile(**raw_profile)
    )

    settings = get_settings()
    store = SupabaseStore(url=settings.supabase_url, key=settings.supabase_key.get_secret_value())
    ticker_sector = _load_sp500_universe(store)

    signals: list[InvestmentSignal] = state.get("signals", [])
    filtered = _filter_signals(signals, profile, ticker_sector)

    if not filtered:
        # No qualifying signals — build a safe all-ETF fallback for conservative/moderate,
        # or return None for aggressive (no eligible trades).
        if profile.risk_appetite == "aggressive":
            return {"investment_plan": None}
        spy_amount = round(profile.investment_amount * 0.70, 2)
        bnd_amount = round(profile.investment_amount - spy_amount, 2)
        allocations = [
            Allocation(
                ticker=_ETF_SPY,
                amount=spy_amount,
                percentage=round(spy_amount / profile.investment_amount * 100, 4),
                rationale=_etf_rationale(_ETF_SPY),
            ),
            Allocation(
                ticker=_ETF_BND,
                amount=bnd_amount,
                percentage=round(bnd_amount / profile.investment_amount * 100, 4),
                rationale=_etf_rationale(_ETF_BND),
            ),
        ]
        plan = InvestmentPlan(
            total_amount=profile.investment_amount,
            allocations=allocations,
            risk_summary="No qualifying signals found; defaulting to diversified ETF allocation.",
            expected_return_range=(
                round(_FALLBACK_RETURN * 0.7, 4),
                round(_FALLBACK_RETURN * 1.3, 4),
            ),
            time_horizon_months=profile.time_horizon_months,
            rebalance_trigger="on_new_signal",
        )
        _try_persist(plan)
        return {"investment_plan": plan}

    allocations = _build_allocations(
        profile.risk_appetite, filtered, profile.investment_amount
    )

    # Determine which tickers are in the plan (excluding ETFs for return calc)
    individual_tickers = [
        a.ticker for a in allocations
        if a.ticker not in (_ETF_SPY, _ETF_BND)
    ]
    etf_tickers = [a.ticker for a in allocations if a.ticker in (_ETF_SPY, _ETF_BND)]
    all_tickers = individual_tickers + etf_tickers
    if not all_tickers:
        all_tickers = [_ETF_SPY]

    returns = [_get_annual_return(t) for t in all_tickers]
    min_r = min(returns)
    max_r = max(returns)
    expected_return_range = (round(min_r * 0.7, 4), round(max_r * 1.3, 4))

    n_stocks = len(individual_tickers)
    has_etfs = len(etf_tickers) > 0
    risk_summary = _risk_summary(profile.risk_appetite, n_stocks, has_etfs)

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
