"""US session exploratory comparison for five MT5 CFD markets.
Uses the existing conservative_backtest and session_lab modules.
No order placement. UTC window 12:00-21:00 is a proxy, not exchange hours.
"""
import os
import json
import conservative_backtest as bt
from session_lab import summarize

SYMBOLS = ("XAUUSD", "US30", "DE40", "USTECH", "US500")
START_HOUR = 12
END_HOUR = 21

def report(symbol, label, rows):
    metrics = summarize(rows)
    print(f"{symbol:7} {label:17} " + json.dumps(metrics, ensure_ascii=False), flush=True)
    return metrics

def main():
    print("USA FIVE-MARKET LAB | 12:00-21:00 UTC | historical research only", flush=True)
    print("Window is an approximation; US DST, NYSE hours, CFD breaks and news are NOT modeled.")
    print("History has already been examined; no untouched out-of-sample validation.")
    comparison = []
    for symbol in SYMBOLS:
        env_name = f"BACKTEST_COST_{symbol}"
        raw = os.getenv(env_name)
        if raw is None:
            print(f"SKIP {symbol}: missing {env_name} (round-trip cost in symbol price units).", flush=True)
            continue
        try:
            cost = float(raw)
            if not (0 <= cost < float("inf")):
                raise ValueError("cost must be finite and nonnegative")
            trades = sorted(bt.test(symbol, cost=cost), key=lambda t: t["time"])
            usa = [t for t in trades if START_HOUR <= bt.dt(t["time"]).hour < END_HOUR]
            print(f"\n--- {symbol} | cost={cost} price units ---", flush=True)
            report(symbol, "ALL HOURS", trades)
            m = report(symbol, "USA ALL", usa)
            report(symbol, "USA LONG", [t for t in usa if t["side"] == "LONG"])
            report(symbol, "USA SHORT", [t for t in usa if t["side"] == "SHORT"])
            for hour in range(START_HOUR, END_HOUR):
                report(symbol, f"USA {hour:02d}:00", [t for t in usa if bt.dt(t["time"]).hour == hour])
            report(symbol, "USA 12-15", [t for t in usa if 12 <= bt.dt(t["time"]).hour < 15])
            report(symbol, "USA 15-18", [t for t in usa if 15 <= bt.dt(t["time"]).hour < 18])
            report(symbol, "USA 18-21", [t for t in usa if 18 <= bt.dt(t["time"]).hour < 21])
            comparison.append((symbol, m))
        except Exception as exc:
            print(f"ERROR {symbol}: {type(exc).__name__}: {exc}", flush=True)
    print("\n--- USA COMPARISON (descriptive, NOT future probabilities) ---")
    for symbol, metrics in sorted(comparison, key=lambda item: item[1].get("expectancy_R") if item[1].get("expectancy_R") is not None else float("-inf"), reverse=True):
        print(symbol, json.dumps(metrics, ensure_ascii=False))
    print("NOT LIVE READY: tick-level costs, swaps, real session calendars, news blackout,")
    print("slippage, fill quality and unseen rolling walk-forward validation are missing.")

if __name__ == "__main__":
    main()
