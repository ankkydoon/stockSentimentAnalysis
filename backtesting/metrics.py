from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime


def directional_accuracy(results: list[dict]) -> float:
    """% of signals where direction matched actual price move (neutral excluded from denominator)."""
    actionable = [r for r in results if r["direction"] != "neutral"]
    if not actionable:
        return 0.0
    correct = sum(1 for r in actionable if r["correct"])
    return correct / len(actionable)


def precision_by_direction(results: list[dict]) -> dict[str, float]:
    """{'bullish': float, 'bearish': float} — true positives / total predicted for each direction."""
    counts: dict[str, dict[str, int]] = {
        "bullish": {"tp": 0, "total": 0},
        "bearish": {"tp": 0, "total": 0},
    }
    for r in results:
        direction = r["direction"]
        if direction not in counts:
            continue
        counts[direction]["total"] += 1
        if r["correct"]:
            counts[direction]["tp"] += 1

    return {
        direction: (
            counts[direction]["tp"] / counts[direction]["total"]
            if counts[direction]["total"] > 0
            else 0.0
        )
        for direction in ("bullish", "bearish")
    }


def mean_return(results: list[dict]) -> float:
    """Average actual return across all non-neutral signals."""
    actionable = [r["actual_return"] for r in results if r["direction"] != "neutral"]
    if not actionable:
        return 0.0
    return sum(actionable) / len(actionable)


def sharpe_ratio(results: list[dict]) -> float:
    """mean_return / std_return * sqrt(252); returns 0.0 if std is zero."""
    actionable = [r["actual_return"] for r in results if r["direction"] != "neutral"]
    if len(actionable) < 2:
        return 0.0
    n = len(actionable)
    mu = sum(actionable) / n
    variance = sum((x - mu) ** 2 for x in actionable) / (n - 1)
    std = math.sqrt(variance)
    if std == 0.0:
        return 0.0
    return (mu / std) * math.sqrt(252)


def max_drawdown(returns: list[float]) -> float:
    """Worst peak-to-trough drawdown over the cumulative return series."""
    if not returns:
        return 0.0
    peak = 0.0
    cumulative = 0.0
    worst = 0.0
    for r in returns:
        cumulative += r
        if cumulative > peak:
            peak = cumulative
        drawdown = peak - cumulative
        if drawdown > worst:
            worst = drawdown
    return -worst


def hit_rate_by_sector(results: list[dict], ticker_sector: dict[str, str]) -> dict[str, float]:
    """Directional accuracy broken down by sector (neutral signals excluded)."""
    sector_correct: dict[str, int] = defaultdict(int)
    sector_total: dict[str, int] = defaultdict(int)

    for r in results:
        if r["direction"] == "neutral":
            continue
        sector = ticker_sector.get(r["ticker"], "Unknown")
        sector_total[sector] += 1
        if r["correct"]:
            sector_correct[sector] += 1

    return {
        sector: sector_correct[sector] / total
        for sector, total in sector_total.items()
        if total > 0
    }


def hit_rate_by_event_type(results: list[dict]) -> dict[str, float]:
    """Directional accuracy broken down by event_category (neutral signals excluded)."""
    event_correct: dict[str, int] = defaultdict(int)
    event_total: dict[str, int] = defaultdict(int)

    for r in results:
        if r["direction"] == "neutral":
            continue
        category = r.get("event_category") or "unknown"
        event_total[category] += 1
        if r["correct"]:
            event_correct[category] += 1

    return {
        category: event_correct[category] / total
        for category, total in event_total.items()
        if total > 0
    }
