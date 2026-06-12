import argparse
import json
import os
import sys
from datetime import datetime, timezone

from graph.builder import build_graph
from models.recommendation import UserProfile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Financial News Sentiment Analyzer — LangGraph pipeline"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enable interactive investment plan mode (requires --amount, --risk, --horizon)",
    )
    parser.add_argument(
        "--amount",
        type=float,
        default=10000.0,
        metavar="AMOUNT",
        help="Investment amount in USD (default: 10000)",
    )
    parser.add_argument(
        "--risk",
        choices=["conservative", "moderate", "aggressive"],
        default="moderate",
        metavar="RISK",
        help="Risk appetite: conservative | moderate | aggressive (default: moderate)",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=12,
        metavar="MONTHS",
        help="Investment time horizon in months (default: 12)",
    )
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run backtesting engine after the main pipeline",
    )
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Backtest start date (required with --backtest)",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Backtest end date (required with --backtest)",
    )
    parser.add_argument(
        "--thread-id",
        type=str,
        default=None,
        metavar="THREAD_ID",
        help="Thread ID for resuming from a checkpoint",
    )
    return parser.parse_args()


def _build_initial_state(args: argparse.Namespace) -> dict:
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    state: dict = {
        "raw_articles": [],
        "deduplicated_articles": [],
        "article_entities": {},
        "sentiment_scores": [],
        "events": [],
        "signals": [],
        "investment_plan": None,
        "backtest_results": None,
        "requires_interrupt": False,
        "human_review_decision": None,
        "error_log": [],
        "run_date": run_date,
    }
    if args.interactive:
        state["user_profile"] = UserProfile(
            investment_amount=args.amount,
            risk_appetite=args.risk,
            time_horizon_months=args.horizon,
        )
    return state


def _print_signal_table(signals: list) -> None:
    if not signals:
        print("\nNo signals generated.")
        return
    header = f"{'Ticker':<10} {'Direction':<12} {'Confidence':>12} {'Score':>8}"
    separator = "-" * len(header)
    print(f"\n{separator}")
    print("  INVESTMENT SIGNALS")
    print(separator)
    print(header)
    print(separator)
    for sig in signals:
        print(
            f"{sig.ticker:<10} {sig.direction:<12} {sig.confidence:>12.3f} {sig.score:>8.3f}"
        )
    print(separator)


def _print_plan_table(plan) -> None:
    if plan is None:
        print("\nNo investment plan generated.")
        return
    header = f"{'Ticker':<10} {'Amount':>12} {'%':>8}  Rationale"
    separator = "-" * 70
    print(f"\n{separator}")
    print("  INVESTMENT PLAN")
    print(separator)
    print(f"Total: ${plan.total_amount:,.2f}  |  Horizon: {plan.time_horizon_months}mo  |  Rebalance: {plan.rebalance_trigger}")
    print(f"Risk summary: {plan.risk_summary}")
    print(separator)
    print(header)
    print(separator)
    for alloc in plan.allocations:
        print(
            f"{alloc.ticker:<10} {alloc.amount:>12,.2f} {alloc.percentage:>7.1f}%  {alloc.rationale}"
        )
    print(separator)
    print(f"Disclaimer: {plan.disclaimer}")


def _save_output(final_state: dict, run_date: str) -> str:
    outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    output_path = os.path.join(outputs_dir, f"{run_date}.json")

    # Keys that are large / not needed downstream (raw article bodies bloat the file)
    _SKIP_KEYS = {"raw_articles", "deduplicated_articles", "article_entities"}

    def _serialise(obj):
        if isinstance(obj, list):
            return [_serialise(i) for i in obj]
        if isinstance(obj, dict):
            return {k: _serialise(v) for k, v in obj.items()}
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        return str(obj)

    serialisable: dict = {
        k: _serialise(v) for k, v in final_state.items() if k not in _SKIP_KEYS
    }

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(serialisable, fh, indent=2, default=str)
    return output_path


def main() -> None:
    args = parse_args()

    thread_id = args.thread_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_config: dict = {"configurable": {"thread_id": thread_id}}

    initial_state = _build_initial_state(args)
    graph = build_graph()

    final_state: dict = {}

    final_state = graph.invoke(initial_state, config=run_config)

    signals = final_state.get("signals") or []
    _print_signal_table(signals)

    if args.interactive:
        investment_plan = final_state.get("investment_plan")
        _print_plan_table(investment_plan)

    if args.backtest:
        from backtesting.engine import BacktestEngine
        start_date = args.start or "2024-01-01"
        end_date = args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        print(f"\n[BACKTEST] Running from {start_date} to {end_date} ...")
        engine = BacktestEngine(start_date=start_date, end_date=end_date)
        backtest_results = engine.run(signals=signals)
        final_state["backtest_results"] = backtest_results
        print(f"[BACKTEST] Results: {backtest_results}")

    run_date = final_state.get("run_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_path = _save_output(final_state, run_date)
    print(f"\nOutput saved to: {output_path}")

    error_log = final_state.get("error_log") or []
    if error_log:
        print("\n[WARNINGS/ERRORS]")
        for entry in error_log:
            print(f"  - {entry}")

    sys.exit(0)


if __name__ == "__main__":
    main()
