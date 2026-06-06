from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import yfinance as yf

from storage.supabase_store import SupabaseStore
from backtesting import metrics as bm

logger = logging.getLogger(__name__)


def _next_trading_day(dt: datetime) -> str:
    """Return the date string for the next calendar day (yfinance start is inclusive)."""
    next_day = dt.date() + timedelta(days=1)
    return next_day.isoformat()


def _date_str(dt: datetime, offset_days: int = 0) -> str:
    """Return ISO date string with an optional day offset."""
    return (dt.date() + timedelta(days=offset_days)).isoformat()


def _fetch_signals_by_date_range(
    store: SupabaseStore, start_date: str, end_date: str
) -> list[dict]:
    """Query the signals table for rows within [start_date, end_date]."""
    response = (
        store.client.table("signals")
        .select("*")
        .gte("generated_at", start_date)
        .lte("generated_at", end_date)
        .execute()
    )
    return response.data or []


def _batch_close_prices(
    tickers: list[str], start: str, end: str
) -> pd.DataFrame:
    """Download adjusted close prices for a list of tickers.

    Returns a DataFrame with dates as index and tickers as columns.
    Adds one extra calendar day to `end` so yfinance includes the end date.
    """
    end_inclusive = (
        datetime.fromisoformat(end).date() + timedelta(days=1)
    ).isoformat()
    try:
        data = yf.download(
            tickers,
            start=start,
            end=end_inclusive,
            auto_adjust=True,
            progress=False,
            threads=True,
        )["Close"]
    except Exception as exc:
        logger.warning("yfinance batch download failed: %s", exc)
        return pd.DataFrame()

    # yfinance returns a Series when there is only one ticker; normalise to DataFrame.
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])

    return data


def _get_price_on_or_after(prices: pd.Series, target_date: str) -> float | None:
    """Return the close price on target_date or the next available trading day."""
    target = pd.Timestamp(target_date)
    future = prices[prices.index >= target]
    if future.empty:
        return None
    value = future.iloc[0]
    if pd.isna(value):
        return None
    return float(value)


class BacktestEngine:
    def __init__(self, store: SupabaseStore, forward_days: int = 14) -> None:
        self.store = store
        self.forward_days = forward_days

    def run(self, start_date: str, end_date: str) -> dict[str, Any]:
        """Run a backtest over signals generated between start_date and end_date.

        Steps:
          1. Fetch signals from the store.
          2. For each non-neutral signal fetch actual prices via yfinance.
          3. Compute actual_return and correctness.
          4. Compute all metrics.
          5. Return a metrics dict.
        """
        raw_signals = _fetch_signals_by_date_range(self.store, start_date, end_date)
        total_signals = len(raw_signals)
        logger.info("Fetched %d signals between %s and %s", total_signals, start_date, end_date)

        # Filter out neutral signals — they are excluded from return/accuracy metrics.
        actionable = [s for s in raw_signals if s.get("signal", "neutral") != "neutral"]

        if not actionable:
            logger.warning("No actionable (non-neutral) signals found in date range.")
            return _empty_metrics(start_date, end_date, total_signals)

        # --- Determine the full date window needed for price download ---
        all_tickers = list({s["ticker"] for s in actionable})

        parsed_dates = [
            datetime.fromisoformat(s["generated_at"].replace("Z", "+00:00"))
            for s in actionable
        ]
        earliest_signal = min(parsed_dates)
        latest_signal = max(parsed_dates)

        price_start = _next_trading_day(earliest_signal)
        price_end = _date_str(latest_signal, offset_days=self.forward_days + 5)

        logger.info(
            "Downloading prices for %d tickers from %s to %s",
            len(all_tickers),
            price_start,
            price_end,
        )
        price_data = _batch_close_prices(all_tickers, price_start, price_end)

        # --- Build result rows ---
        results: list[dict] = []
        skipped = 0

        for sig in actionable:
            ticker = sig["ticker"]
            direction = sig["signal"]  # column name in Supabase is "signal"
            confidence = sig.get("confidence", 0.0)
            generated_at = datetime.fromisoformat(
                sig["generated_at"].replace("Z", "+00:00")
            )

            # Price series for this ticker
            if price_data.empty or ticker not in price_data.columns:
                logger.warning("No price data for ticker %s — skipping signal.", ticker)
                skipped += 1
                continue

            ticker_prices: pd.Series = price_data[ticker].dropna()

            entry_date = _next_trading_day(generated_at)
            exit_date = _date_str(generated_at, offset_days=self.forward_days)

            price_start_val = _get_price_on_or_after(ticker_prices, entry_date)
            price_end_val = _get_price_on_or_after(ticker_prices, exit_date)

            if price_start_val is None or price_end_val is None:
                logger.warning(
                    "Missing start or end price for %s around %s — skipping.",
                    ticker,
                    entry_date,
                )
                skipped += 1
                continue

            if price_start_val == 0.0:
                logger.warning("Zero start price for %s — skipping.", ticker)
                skipped += 1
                continue

            actual_return = (price_end_val - price_start_val) / price_start_val

            correct = (
                (direction == "bullish" and actual_return > 0)
                or (direction == "bearish" and actual_return < 0)
            )

            # Pull event_category out of components if present
            components = sig.get("components") or {}
            event_category = components.get("event_category") or sig.get("event_category")

            results.append(
                {
                    "ticker": ticker,
                    "direction": direction,
                    "confidence": confidence,
                    "signal_date": generated_at,
                    "forward_days": self.forward_days,
                    "actual_return": actual_return,
                    "correct": correct,
                    "event_category": event_category,
                }
            )

        logger.info(
            "Evaluated %d signals (%d skipped due to missing price data).",
            len(results),
            skipped,
        )

        if not results:
            return _empty_metrics(start_date, end_date, total_signals)

        # --- Compute metrics ---
        prec = bm.precision_by_direction(results)
        returns_list = [r["actual_return"] for r in results if r["direction"] != "neutral"]

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_signals": total_signals,
            "signals_evaluated": len(results),
            "directional_accuracy": bm.directional_accuracy(results),
            "precision_bullish": prec["bullish"],
            "precision_bearish": prec["bearish"],
            "mean_return": bm.mean_return(results),
            "sharpe_ratio": bm.sharpe_ratio(results),
            "max_drawdown": bm.max_drawdown(returns_list),
            "hit_rate_by_sector": bm.hit_rate_by_sector(results, {}),
            "hit_rate_by_event_type": bm.hit_rate_by_event_type(results),
        }


def _empty_metrics(start_date: str, end_date: str, total_signals: int) -> dict[str, Any]:
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_signals": total_signals,
        "signals_evaluated": 0,
        "directional_accuracy": 0.0,
        "precision_bullish": 0.0,
        "precision_bearish": 0.0,
        "mean_return": 0.0,
        "sharpe_ratio": 0.0,
        "max_drawdown": 0.0,
        "hit_rate_by_sector": {},
        "hit_rate_by_event_type": {},
    }
