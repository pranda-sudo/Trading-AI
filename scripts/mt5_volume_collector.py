"""Read-only pilot: closed M1 bars and UTC daily tick-volume VWAP/profile proxies."""
import argparse
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
import MetaTrader5 as mt5
import numpy as np

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--terminal", required=True)
    p.add_argument("--symbol", default="XAUUSD")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--bin", type=float, default=1.0)
    p.add_argument("--out", default="data")
    a = p.parse_args()
    if not 1 <= a.days <= 90 or not 0 < a.bin:
        p.error("Invalid days or price bin")
    if not mt5.initialize(a.terminal):
        raise RuntimeError(mt5.last_error())
    try:
        account = mt5.account_info()
        if account is None or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise RuntimeError("Demo account required")
        if not mt5.symbol_select(a.symbol, True):
            raise RuntimeError("Symbol unavailable: " + a.symbol)
        end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        start = end.replace(hour=0, minute=0) - timedelta(days=a.days)
        bars = mt5.copy_rates_range(a.symbol, mt5.TIMEFRAME_M1, start, end-timedelta(seconds=1))
        if bars is None or not len(bars):
            raise RuntimeError(mt5.last_error())
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        with (out / "m1.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(bars.dtype.names)
            w.writerows(bars.tolist())
        days = bars["time"] // 86400
        with (out / "daily_profile.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["utc_date","bars","tick_volume","vwap_proxy","sigma","poc_proxy","vah_proxy","val_proxy"])
            for day in np.unique(days):
                b = bars[days == day]
                v = b["tick_volume"].astype(float)
                price = (b["high"]+b["low"]+b["close"])/3
                if v.sum() <= 0:
                    continue
                mean = np.average(price, weights=v)
                sigma = np.sqrt(np.average((price-mean)**2, weights=v))
                idx = np.floor(price/a.bin).astype(int)
                lo = int(idx.min())
                hist = np.bincount(idx-lo, weights=v)
                poc = int(hist.argmax())
                left = right = poc
                total = hist[poc]
                while total < .7*hist.sum() and (left>0 or right<len(hist)-1):
                    lv = hist[left-1] if left>0 else -1
                    rv = hist[right+1] if right<len(hist)-1 else -1
                    if lv >= rv:
                        left -= 1
                        total += hist[left]
                    else:
                        right += 1
                        total += hist[right]
                w.writerow([datetime.fromtimestamp(int(day)*86400,timezone.utc).date(),len(b),v.sum(),mean,sigma,(lo+poc+.5)*a.bin,(lo+right+1)*a.bin,(lo+left)*a.bin])
        print(f"OK: {len(bars)} M1 bars; files in {out.resolve()}")
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main()
