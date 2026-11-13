"""Export recent closed MT5 M1 candles to CSV for upload_history.py.
Read-only: never places orders. Run on the Windows VPS with MT5 logged in.
Usage: py C:\\AItrading\\collector\\export_m1.py
Optional: set MT5_M1_DAYS=30, MT5_M1_BATCH=5000.
"""
import csv
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import MetaTrader5 as mt5

SYMBOLS = {"XAUUSD": "XAUUSD", "US30": ".US30Cash", "DE40": ".DE40Cash",
           "USTECH": ".USTECHCash", "US500": ".US500Cash"}
OUT = Path(os.getenv("MT5_HISTORY_DIR", r"C:\AItrading\collector\history"))
DAYS = max(1, int(os.getenv("MT5_M1_DAYS", "30")))
BATCH = max(100, min(10000, int(os.getenv("MT5_M1_BATCH", "5000"))))
TERMINAL = os.getenv("TRADING_AI_MT5_PATH", "").strip()
EXPECTED_LOGIN = os.getenv("TRADING_AI_MT5_LOGIN", "").strip()
FIELDS = ("time_utc", "open", "high", "low", "close", "tick_volume", "spread", "real_volume")

def main():
    if not (mt5.initialize(path=TERMINAL, timeout=20000) if TERMINAL else mt5.initialize(timeout=20000)):
        raise RuntimeError(f"Cannot connect to MT5: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None:
            raise RuntimeError("Log into RoboForex MT5 first")
        if EXPECTED_LOGIN and str(account.login) != EXPECTED_LOGIN:
            raise RuntimeError("Connected to a different MT5 account")
        cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS)
        OUT.mkdir(parents=True, exist_ok=True)
        for name, broker_symbol in SYMBOLS.items():
            if not mt5.symbol_select(broker_symbol, True):
                print("SKIP unavailable", broker_symbol, mt5.last_error(), flush=True)
                continue
            rows = {}
            offset = 1  # skip current unfinished bar
            while True:
                bars = mt5.copy_rates_from_pos(broker_symbol, mt5.TIMEFRAME_M1, offset, BATCH)
                if bars is None:
                    print("MT5 history error", broker_symbol, mt5.last_error(), flush=True)
                    break
                if len(bars) == 0:
                    break
                oldest = None
                for bar in bars:
                    epoch = int(bar["time"])
                    oldest = epoch if oldest is None else min(oldest, epoch)
                    dt = datetime.fromtimestamp(epoch, timezone.utc)
                    if dt >= cutoff:
                        rows[epoch] = (dt.isoformat(), float(bar["open"]), float(bar["high"]),
                                       float(bar["low"]), float(bar["close"]),
                                       int(bar["tick_volume"]), int(bar["spread"]),
                                       int(bar["real_volume"]))
                if oldest is None or datetime.fromtimestamp(oldest, timezone.utc) < cutoff or len(bars) < BATCH:
                    break
                offset += len(bars)
            if not rows:
                print("NO M1 HISTORY", name, "- open M1 chart in MT5 and load older bars", flush=True)
                continue
            path = OUT / f"{name}_M1.csv"
            with path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(FIELDS)
                writer.writerows(rows[k] for k in sorted(rows))
            print("OK", name, "M1", len(rows), "candles", "from",
                  datetime.fromtimestamp(min(rows), timezone.utc).isoformat(),
                  "to", datetime.fromtimestamp(max(rows), timezone.utc).isoformat(), flush=True)
        print("Export completed. Next run upload_history.py", flush=True)
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main()
