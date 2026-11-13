"""Research-only session-gated backtest across five RoboForex MT5 markets.
DE40: Europe 07-12 UTC only.
XAUUSD/US30/USTECH/US500: Asia 00-07 and USA 12-21 UTC only.
USA is broken down hourly, by direction, and into 12-15/15-18/18-21.
This does not alter live signals, submit orders or validate future profitability.
"""
import json
import math
import os
import conservative_backtest as bt
from session_lab import summarize

MARKETS = ("XAUUSD", "US30", "DE40", "USTECH", "US500")
WINDOWS = {"DE40": (("EUROPE", 7, 12),)}
for _symbol in ("XAUUSD", "US30", "USTECH", "US500"):
    WINDOWS[_symbol] = (("ASIA", 0, 7), ("USA", 12, 21))

def emit(symbol, label, trades):
    m = summarize(trades)
    print(f"{symbol:7} {label:20} " + json.dumps(m, ensure_ascii=False), flush=True)
    return m

def main():
    print("SESSION GATED FIVE MARKET RESEARCH | UTC | NO LIVE TRADING", flush=True)
    print("DE40 EUROPE 07-12; other four ASIA 00-07 and USA 12-21.")
    print("Fixed UTC windows are proxies: NOT exact DST-adjusted exchange sessions.")
    print("USA filters are diagnostic, NOT optimized on a new independent holdout.")
    print("All results need broker tick costs, real news blackouts and unseen validation.")
    summary = []
    for symbol in MARKETS:
        name = f"BACKTEST_COST_{symbol}"
        raw = os.getenv(name)
        if raw is None:
            print(f"SKIP {symbol}: set {name} to verified round-trip cost in price units.", flush=True)
            continue
        try:
            cost = float(raw)
            if not math.isfinite(cost) or cost < 0:
                raise ValueError("cost must be finite and nonnegative")
            trades = sorted(bt.test(symbol, cost=cost), key=lambda t:t["time"])
            print(f"\n--- {symbol} | cost={cost} price units ---", flush=True)
            emit(symbol, "ALL HOURS BASELINE", trades)
            accepted = []
            for session, start, end in WINDOWS[symbol]:
                rows = [t for t in trades if start <= bt.dt(t["time"]).hour < end]
                accepted.extend(rows)
                m = emit(symbol, session + " ALL", rows)
                summary.append((symbol, session, m))
                for side in ("LONG", "SHORT"):
                    emit(symbol, session + " " + side, [t for t in rows if t["side"] == side])
                for hour in range(start, end):
                    emit(symbol, f"{session} {hour:02d}:00", [t for t in rows if bt.dt(t["time"]).hour == hour])
                if session == "USA":
                    for label, a, b in (("USA 12-15",12,15),("USA 15-18",15,18),("USA 18-21",18,21)):
                        emit(symbol, label, [t for t in rows if a <= bt.dt(t["time"]).hour < b])
            emit(symbol, "ALLOWED WINDOWS", sorted(accepted,key=lambda t:t["time"]))
        except Exception as exc:
            print(f"ERROR {symbol}: {type(exc).__name__}: {exc}", flush=True)
    print("\n--- SESSION COMPARISON (descriptive, NOT predicted win probabilities) ---")
    for symbol, session, m in summary:
        print(f"{symbol:7} {session:7} " + json.dumps(m, ensure_ascii=False))
    print("RESEARCH ONLY: previously inspected history; no untouched holdout.")
    print("NO LIVE DEPLOYMENT: verify bid/ask, spread spikes, commission, slippage, swaps,")
    print("broker hours, DST, news and rolling forward tests before using any filter.")

if __name__ == "__main__":
    main()
