"""Compare ASIA 00:00-07:00 UTC across five RoboForex MT5 symbols.
Exploratory historical analysis only. NO orders. NOT a validated strategy.
Run: py -3.11 C:\\AITrading\\research\\asia_five_markets.py
Requires conservative_backtest.py and walk_forward.py in the same directory.
"""
import os
import json
from datetime import datetime, timezone
import conservative_backtest as bt
from session_lab import summarize

SYMBOLS = ("XAUUSD", "US30", "DE40", "USTECH", "US500")
# Broker-specific CFD execution costs are NOT interchangeable.
# Price units per symbol; set from real MT5 tick/spread and commission analysis.
COST_ENV = {
    "XAUUSD": "BACKTEST_COST_XAUUSD",
    "US30": "BACKTEST_COST_US30",
    "DE40": "BACKTEST_COST_DE40",
    "USTECH": "BACKTEST_COST_USTECH",
    "US500": "BACKTEST_COST_US500",
}

def report(symbol, name, rows):
    m = summarize(rows)
    print(f"{symbol:7} {name:15} " + json.dumps(m, ensure_ascii=False))
    return m

def main():
    print("ASIA FIVE-MARKET LAB | 00:00-07:00 UTC | entry timestamps | research only")
    print("UTC window is a simplified proxy, not precise exchange hours or DST.")
    print("Results are based on previously examined history; no untouched holdout.")
    print("IMPORTANT: Costs MUST be independently verified for each RoboForex symbol.")
    summary = []
    for symbol in SYMBOLS:
        raw = os.getenv(COST_ENV[symbol])
        if raw is None:
            print(f"SKIP {symbol}: set {COST_ENV[symbol]} to realistic round-trip price-unit cost.")
            continue
        try:
            cost = float(raw)
            if cost < 0:
                raise ValueError("negative cost")
            trades = sorted(bt.test(symbol, cost=cost), key=lambda t:t["time"])
            asia = [t for t in trades if 0 <= bt.dt(t["time"]).hour < 7]
            print(f"\n--- {symbol} | cost={cost} price units (verify bid/ask, commission, slippage) ---")
            report(symbol, "ALL HOURS", trades)
            m = report(symbol, "ASIA ALL", asia)
            report(symbol, "ASIA LONG", [t for t in asia if t["side"] == "LONG"])
            report(symbol, "ASIA SHORT", [t for t in asia if t["side"] == "SHORT"])
            for hour in range(7):
                report(symbol, f"ASIA {hour:02d}:00", [t for t in asia if bt.dt(t["time"]).hour == hour])
            cut = int(len(trades)*0.7)
            cutoff = bt.dt(trades[cut]["time"]) if trades and cut < len(trades) else None
            if cutoff:
                report(symbol, "ASIA EARLY", [t for t in asia if bt.dt(t["time"]) < cutoff])
                report(symbol, "ASIA LATE", [t for t in asia if bt.dt(t["time"]) >= cutoff])
            summary.append((symbol, m))
        except Exception as exc:
            print(f"ERROR {symbol}: {type(exc).__name__}: {exc}")
    print("\n--- ASIA COMPARISON (exploratory; do not rank as future probabilities) ---")
    for symbol, m in sorted(summary, key=lambda x: x[1].get("expectancy_R") if x[1].get("expectancy_R") is not None else -1e9, reverse=True):
        print(symbol, json.dumps(m, ensure_ascii=False))
    print("NOT LIVE READY: real tick-level costs, market sessions, swaps, news, spread spikes,")
    print("survivorship/selection bias, and rolling future unseen validation remain unresolved.")

if __name__ == "__main__":
    main()
