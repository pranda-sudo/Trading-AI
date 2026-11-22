"""Read-only history diagnostic for XAUUSD MT5 and previously merged ClusterDelta CSV.
Does not claim access to MT5 custom indicator buffers.
"""
import argparse
from pathlib import Path
import pandas as pd

def describe(label, df, cols):
    if df is None or df.empty:
        print(f"{label}: no data")
        return
    t = pd.to_datetime(df["time"], errors="coerce", utc=True)
    print(f"{label}: rows={len(df)}, oldest={t.min()}, newest={t.max()}")
    for col in cols:
        if col in df.columns:
            x = pd.to_numeric(df[col], errors="coerce")
            valid = x.notna() & (x != 0 if col == "vwap" else True)
            dates = t[valid]
            print(f"  {col}: valid={int(valid.sum())}, oldest={dates.min() if len(dates) else 'none'}, newest={dates.max() if len(dates) else 'none'}")
        else:
            print(f"  {col}: MISSING")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=r"C:\AItrading\volume\test_data\merged_m5.csv")
    ap.add_argument("--terminal", default=r"C:\AItrading\petr\terminal64.exe")
    ap.add_argument("--symbol", default="XAUUSD")
    ap.add_argument("--bars", type=int, default=200000)
    a = ap.parse_args()
    p = Path(a.csv)
    print("=== EXISTING CLUSTERDELTA MERGED CSV ===")
    if p.exists():
        describe("CSV", pd.read_csv(p), ["volume", "delta", "cum_delta", "vwap", "spread"])
    else:
        print("CSV missing:", p)
    print("\n=== MT5 M5 PRICE HISTORY ===")
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("MetaTrader5 Python package not installed")
        return
    if not mt5.initialize(path=a.terminal):
        print("MT5 initialize failed:", mt5.last_error())
        return
    try:
        info = mt5.symbol_info(a.symbol)
        if info is None:
            print("Symbol not found:", a.symbol)
            return
        print(f"symbol={a.symbol}, point={info.point}, digits={info.digits}")
        rates = mt5.copy_rates_from_pos(a.symbol, mt5.TIMEFRAME_M5, 0, a.bars)
        if rates is None or len(rates) == 0:
            print("No bars:", mt5.last_error())
            return
        d = pd.DataFrame(rates)
        d["time"] = pd.to_datetime(d["time"], unit="s", utc=True)
        describe("MT5 M5 prices", d, ["tick_volume", "real_volume", "spread"])
        print("NOTE: MT5 chart history is limited by terminal availability and Max bars settings.")
        print("NOTE: Older MT5 prices DO NOT prove older ClusterDelta buffers exist.")
        print("NOTE: To extract historical ClusterDelta buffers, use the existing MQL5 indicator export or collector.")
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main()
