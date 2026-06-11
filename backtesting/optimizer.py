"""
Weight optimizer — derives signal component weights from backtest results.

Uses directional accuracy per component proxy to rebalance the three weights:
  w_sentiment, w_event, w_price

Falls back to defaults when fewer than MIN_SIGNALS signals are available.
"""
from __future__ import annotations

import logging

from storage.supabase_store import SupabaseStore
from backtesting.engine import BacktestEngine

logger = logging.getLogger(__name__)

MIN_SIGNALS = 20
DEFAULTS = {"w_sentiment": 0.50, "w_event": 0.35, "w_price": 0.15}


def _normalize(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total == 0:
        return dict(DEFAULTS)
    return {k: v / total for k, v in weights.items()}


def _derive_weights(results: list[dict]) -> dict[str, float]:
    """
    Estimate per-component contribution by correlating each component score
    with correctness, then normalise to sum to 1.

    Each signal row has components: {"sentiment": float, "event": float, "price": float}
    and correct: bool.
    """
    sums = {"w_sentiment": 0.0, "w_event": 0.0, "w_price": 0.0}
    counts = {"w_sentiment": 0, "w_event": 0, "w_price": 0}

    for r in results:
        components = r.get("components") or {}
        correct = r.get("correct", False)
        direction = r.get("direction", "neutral")
        if direction == "neutral":
            continue

        # For each component, check if its sign agreed with actual price move
        sign = 1 if direction == "bullish" else -1

        for key, comp_key in [("w_sentiment", "sentiment"), ("w_event", "event"), ("w_price", "price")]:
            val = components.get(comp_key)
            if val is None:
                continue
            agreed = (val * sign > 0)
            sums[key] += 1.0 if agreed else 0.0
            counts[key] += 1

    raw = {}
    for key in sums:
        if counts[key] > 0:
            raw[key] = sums[key] / counts[key]
        else:
            raw[key] = DEFAULTS[key]

    # If all components look equally useless, fall back to defaults
    if max(raw.values()) < 0.5:
        logger.warning("All component accuracies below 50%% — keeping defaults")
        return dict(DEFAULTS)

    return _normalize(raw)


def run_optimization(store: SupabaseStore, start_date: str, end_date: str) -> dict:
    """
    Run backtest over [start_date, end_date], derive new weights, save to DB.
    Returns the weights dict that was saved (or defaults if insufficient data).
    """
    engine = BacktestEngine(store=store, forward_days=14)
    backtest = engine.run(start_date=start_date, end_date=end_date)

    evaluated = backtest.get("signals_evaluated", 0)
    accuracy = backtest.get("directional_accuracy", 0.0)

    logger.info("Backtest: %d signals evaluated, accuracy=%.3f", evaluated, accuracy)

    if evaluated < MIN_SIGNALS:
        logger.warning(
            "Only %d signals evaluated (minimum %d) — keeping default weights",
            evaluated, MIN_SIGNALS,
        )
        store.save_weights(
            w_sentiment=DEFAULTS["w_sentiment"],
            w_event=DEFAULTS["w_event"],
            w_price=DEFAULTS["w_price"],
            signals_evaluated=evaluated,
            directional_accuracy=accuracy,
            notes=f"sparse data ({evaluated} signals) — defaults retained",
        )
        return dict(DEFAULTS)

    # Re-fetch raw results for component-level analysis
    raw_signals = engine._fetch_signals_for_optimization(start_date, end_date)
    weights = _derive_weights(raw_signals)

    store.save_weights(
        w_sentiment=weights["w_sentiment"],
        w_event=weights["w_event"],
        w_price=weights["w_price"],
        signals_evaluated=evaluated,
        directional_accuracy=accuracy,
        notes=f"optimized from {evaluated} signals",
    )

    logger.info("Saved new weights: %s", weights)
    return weights
