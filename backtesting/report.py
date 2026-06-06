from __future__ import annotations

import json
import os
from typing import Any


def print_backtest_report(metrics: dict[str, Any]) -> None:
    """Print a formatted backtest report to stdout."""
    start = metrics.get("start_date", "N/A")
    end = metrics.get("end_date", "N/A")
    total = metrics.get("total_signals", 0)
    evaluated = metrics.get("signals_evaluated", 0)

    dir_acc = metrics.get("directional_accuracy", 0.0) * 100
    prec_bull = metrics.get("precision_bullish", 0.0) * 100
    prec_bear = metrics.get("precision_bearish", 0.0) * 100
    mean_ret = metrics.get("mean_return", 0.0) * 100
    sharpe = metrics.get("sharpe_ratio", 0.0)
    drawdown = metrics.get("max_drawdown", 0.0) * 100

    hit_sector: dict[str, float] = metrics.get("hit_rate_by_sector", {})
    hit_event: dict[str, float] = metrics.get("hit_rate_by_event_type", {})

    lines: list[str] = [
        "=== Backtest Report ===",
        f"Period: {start} to {end}",
        f"Signals evaluated: {evaluated} / {total}",
        "",
        f"Directional Accuracy:  {dir_acc:>6.1f}%",
        f"Precision (Bullish):   {prec_bull:>6.1f}%",
        f"Precision (Bearish):   {prec_bear:>6.1f}%",
        f"Mean Return:           {mean_ret:>+7.2f}%",
        f"Sharpe Ratio:          {sharpe:>6.2f}",
        f"Max Drawdown:          {drawdown:>+7.1f}%",
    ]

    if hit_sector:
        lines.append("")
        lines.append("Hit Rate by Sector:")
        for sector, rate in sorted(hit_sector.items()):
            lines.append(f"  {sector:<20s}  {rate * 100:.1f}%")

    if hit_event:
        lines.append("")
        lines.append("Hit Rate by Event Type:")
        for event, rate in sorted(hit_event.items()):
            lines.append(f"  {event:<20s}  {rate * 100:.1f}%")

    lines.append("")
    lines.append("Disclaimer: Educational use only. Not investment advice.")

    print("\n".join(lines))


def save_backtest_report(metrics: dict[str, Any], output_path: str) -> None:
    """Save metrics dict as JSON to output_path, creating parent directories if needed."""
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2, default=str)
