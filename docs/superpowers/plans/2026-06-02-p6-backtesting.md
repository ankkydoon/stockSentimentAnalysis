# P6: Backtesting Module

> **For agentic workers:** Use subagent-driven-development to implement task-by-task.

**Goal:** Load historical signals from Supabase, fetch actual prices via yfinance, compute accuracy metrics.

**Architecture:** BacktestEngine loads signals, fetches prices in batch, delegates metric math to metrics.py. No LLM calls.

**Tech Stack:** yfinance, pandas, supabase-py

---

### Task 1: backtesting/metrics.py

**Files:**
- Create: `backtesting/metrics.py`
- Create: `tests/test_backtesting.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_backtesting.py
from backtesting.metrics import directional_accuracy, sharpe_ratio, max_drawdown

def test_directional_accuracy_perfect():
    signals = [("bullish", 0.05), ("bearish", -0.03), ("bullish", 0.02)]
    acc = directional_accuracy(signals)
    assert acc == 1.0

def test_directional_accuracy_half():
    signals = [("bullish", 0.05), ("bullish", -0.03)]
    acc = directional_accuracy(signals)
    assert acc == 0.5

def test_sharpe_positive_returns():
    returns = [0.02, 0.01, 0.03, 0.02, 0.015]
    s = sharpe_ratio(returns)
    assert s > 0

def test_max_drawdown_known_value():
    prices = [100, 110, 90, 95, 80]
    dd = max_drawdown(prices)
    assert abs(dd - (-0.2727)) < 0.01  # (80-110)/110
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_backtesting.py -v
```

- [ ] **Step 3: Implement backtesting/metrics.py**

```python
import math

def directional_accuracy(signal_returns: list[tuple[str, float]]) -> float:
    if not signal_returns:
        return 0.0
    correct = sum(
        1 for direction, ret in signal_returns
        if (direction == "bullish" and ret > 0) or (direction == "bearish" and ret < 0)
    )
    return correct / len(signal_returns)

def sharpe_ratio(returns: list[float], risk_free: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    n = len(returns)
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    std = math.sqrt(variance) if variance > 0 else 0.0
    if std == 0:
        return 0.0
    return (mean - risk_free) / std * math.sqrt(252)

def max_drawdown(prices: list[float]) -> float:
    if len(prices) < 2:
        return 0.0
    peak = prices[0]
    max_dd = 0.0
    for price in prices:
        if price > peak:
            peak = price
        dd = (price - peak) / peak
        if dd < max_dd:
            max_dd = dd
    return max_dd
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_backtesting.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backtesting/metrics.py tests/test_backtesting.py
git commit -m "feat: backtesting metrics (directional accuracy, Sharpe, max drawdown)"
```

---

### Task 2: backtesting/engine.py

**Files:**
- Create: `backtesting/engine.py`

- [ ] **Step 1: Implement backtesting/engine.py**

```python
from datetime import datetime, timezone, timedelta
import yfinance as yf
from config.settings import Settings
from storage.supabase_store import SupabaseStore
from backtesting.metrics import directional_accuracy, sharpe_ratio, max_drawdown

class BacktestEngine:
    def __init__(self, settings: Settings | None = None, forward_days: int = 14):
        self.settings = settings or Settings()
        self.forward_days = forward_days
        self.store = SupabaseStore(url=self.settings.supabase_url, key=self.settings.supabase_key)

    def _load_signals(self) -> list[dict]:
        result = self.store.client.table("signals").select("*").execute()
        return result.data or []

    def _fetch_return(self, ticker: str, signal_date: str) -> float | None:
        try:
            start = datetime.fromisoformat(signal_date).replace(tzinfo=timezone.utc)
            # shift forward 1 trading day to avoid look-ahead bias
            start += timedelta(days=1)
            end = start + timedelta(days=self.forward_days + 7)
            hist = yf.Ticker(ticker).history(start=start.strftime("%Y-%m-%d"),
                                              end=end.strftime("%Y-%m-%d"))["Close"]
            if len(hist) < 2:
                return None
            return float((hist.iloc[-1] - hist.iloc[0]) / hist.iloc[0])
        except Exception:
            return None

    def run(self) -> dict:
        signals = self._load_signals()
        if not signals:
            return {"error": "No signals found. Run seed_backtest_signals.py first."}

        signal_returns = []
        returns_list = []
        for sig in signals:
            ret = self._fetch_return(sig["ticker"], sig["generated_at"])
            if ret is None:
                continue
            signal_returns.append((sig["signal"], ret))
            returns_list.append(ret)

        if not signal_returns:
            return {"error": "Could not fetch price data for any signals."}

        return {
            "n_signals": len(signal_returns),
            "directional_accuracy": round(directional_accuracy(signal_returns), 3),
            "sharpe_ratio": round(sharpe_ratio(returns_list), 3),
            "mean_return": round(sum(returns_list) / len(returns_list), 4),
            "max_drawdown": round(max_drawdown(sorted(returns_list)), 4),
            "forward_days": self.forward_days,
            "disclaimer": "Educational use only. Not investment advice.",
        }
```

- [ ] **Step 2: Commit**

```bash
git add backtesting/engine.py
git commit -m "feat: BacktestEngine loads signals from Supabase and computes metrics via yfinance"
```

---

### Task 3: backtesting/report.py

**Files:**
- Create: `backtesting/report.py`

- [ ] **Step 1: Implement backtesting/report.py**

```python
import json

def print_backtest_report(results: dict) -> None:
    if "error" in results:
        print(f"Backtest error: {results['error']}")
        return
    print("\n=== Backtest Report ===")
    print(f"Signals evaluated : {results['n_signals']}")
    print(f"Forward window     : {results['forward_days']} days")
    print(f"Directional acc.   : {results['directional_accuracy']:.1%}")
    print(f"Mean return        : {results['mean_return']:.2%}")
    print(f"Sharpe ratio       : {results['sharpe_ratio']:.2f}")
    print(f"Max drawdown       : {results['max_drawdown']:.2%}")
    print(f"\n{results['disclaimer']}")
```

- [ ] **Step 2: Commit**

```bash
git add backtesting/report.py
git commit -m "feat: backtest report printer"
```

---

## P6 Done

```bash
pytest tests/test_backtesting.py -v
python -c "from backtesting.engine import BacktestEngine; print('OK')"
```
