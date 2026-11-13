"""Read-only MetaTrader 5 collector for Windows VPS.
Requires a running, logged-in MT5 terminal. No order_send calls.
Exports closed candles to CSV compatible with engine/scalper.py.
"""
import argparse
import csv
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

TIMEFRAMES = {"M1": "TIMEFRAME_M1", "M5": "TIMEFRAME_M5", "M15": "TIMEFRAME_M15", "H1": "TIMEFRAME_H1"}

def connect(mt5, terminal_path=None):
    options = {"path": terminal_path} if terminal_path else {}
    if not mt5.initialize(**options):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    account = mt5.account_info()
    if account is None:
        mt5.shutdown()
        raise RuntimeError("MT5 terminal is not logged in")
    return account

def export_rates(mt5, symbol, timeframe, start, end, output):
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Symbol not found or unavailable: {symbol}")
    rates = mt5.copy_rates_range(symbol, getattr(mt5, TIMEFRAMES[timeframe]), start, end)
    if rates is None:
        raise RuntimeError(f"MT5 copy_rates_range failed: {mt5.last_error()}")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    # MT5 bar timestamps are UTC; do not include the currently forming candle.
    tf_seconds = {"M1":60,"M5":300,"M15":900,"H1":3600}[timeframe]
    now = datetime.now(timezone.utc).timestamp()
    count = 0
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time","open","high","low","close","spread"])
        for r in rates:
            stamp = int(r["time"])
            if stamp + tf_seconds > now:
                continue
            # MT5 rates spread is expressed in points; convert to price units.
            info = mt5.symbol_info(symbol)
            if info is None or info.point <= 0:
                raise RuntimeError("Missing symbol point size")
            spread = max(0, float(r["spread"]) * info.point)
            writer.writerow([datetime.fromtimestamp(stamp,timezone.utc).isoformat(),
                             r["open"],r["high"],r["low"],r["close"],spread])
            count += 1
    os.replace(tmp, output)
    return count

def main():
    p=argparse.ArgumentParser(description="Read-only MT5 candle export")
    p.add_argument("--symbol",required=True,help="Exact symbol name as shown in MT5 Market Watch")
    p.add_argument("--timeframe",choices=TIMEFRAMES,default="M1")
    p.add_argument("--days",type=int,default=30)
    p.add_argument("--output",required=True)
    p.add_argument("--terminal-path",default=os.getenv("MT5_TERMINAL_PATH"))
    args=p.parse_args()
    if args.days<1: p.error("--days must be >= 1")
    try:
        import MetaTrader5 as mt5
    except ImportError as e:
        raise SystemExit("Install dependencies: pip install -r connectors/requirements.txt") from e
    connect(mt5,args.terminal_path)
    try:
        end=datetime.now(timezone.utc)
        start=end-timedelta(days=args.days)
        n=export_rates(mt5,args.symbol,args.timeframe,start,end,args.output)
        print(f"Exported {n} closed {args.timeframe} bars for {args.symbol} to {args.output}")
    finally:
        mt5.shutdown()

if __name__=="__main__":
    main()
