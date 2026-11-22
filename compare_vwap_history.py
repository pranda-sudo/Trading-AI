#!/usr/bin/env python3
"""Compare ClusterDelta M5 VWAP to MT5 tick-volume typical-price VWAP (research only)."""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True)
    p.add_argument("--terminal",default=None)
    p.add_argument("--symbol",default="XAUUSD")
    p.add_argument("--out",default="vwap_comparison")
    a=p.parse_args()
    src=Path(a.csv)
    if not src.exists(): raise SystemExit("CSV not found: "+str(src))
    df=pd.read_csv(src,sep=";",dtype=str,encoding="utf-8-sig")
    required={"indicator","buffer","bar_time_mt5","value"}
    if not required.issubset(df.columns): raise SystemExit("Missing columns: "+str(required-set(df.columns)))
    v=df[(df.indicator=="ClusterDelta VWAP") & (df.buffer=="0")].copy()
    v["time"]=pd.to_datetime(v.bar_time_mt5,format="%Y.%m.%d %H:%M",utc=True,errors="coerce")
    v["cd_vwap"]=pd.to_numeric(v.value,errors="coerce")
    v=v.dropna(subset=["time","cd_vwap"])
    v=v[v.cd_vwap>0].sort_values("time").drop_duplicates("time",keep="last")
    if v.empty: raise SystemExit("No positive ClusterDelta VWAP values.")
    kwargs={"path":a.terminal} if a.terminal else {}
    if not mt5.initialize(**kwargs): raise SystemExit("MT5 init failed: "+str(mt5.last_error()))
    try:
        info=mt5.symbol_info(a.symbol)
        if info is None: raise SystemExit("Symbol not found: "+a.symbol)
        rates=mt5.copy_rates_range(a.symbol,mt5.TIMEFRAME_M5,v.time.min().to_pydatetime(),v.time.max().to_pydatetime())
        if rates is None or len(rates)==0: raise SystemExit("No MT5 M5 rates: "+str(mt5.last_error()))
    finally:
        mt5.shutdown()
    m=pd.DataFrame(rates)
    m["time"]=pd.to_datetime(m.time,unit="s",utc=True)
    m["typical"]=(m.high+m.low+m.close)/3
    # Session convention is an assumption; inspect reset behavior before interpreting.
    m["day"]=m.time.dt.floor("D")
    m["weight"]=m.tick_volume.astype(float)
    m["pv"]=m.typical*m.weight
    m["mt5_vwap"]=m.groupby("day").pv.cumsum()/m.groupby("day").weight.cumsum().replace(0,np.nan)
    z=v[["time","cd_vwap"]].merge(m[["time","close","mt5_vwap","tick_volume"]],on="time",how="inner")
    z["diff"]=z.mt5_vwap-z.cd_vwap
    z["abs_diff"]=z["diff"].abs()
    z["different_side"]=((z.close>z.mt5_vwap)!=(z.close>z.cd_vwap)) & (z.close!=z.mt5_vwap) & (z.close!=z.cd_vwap)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    z.to_csv(out/"matched.csv",index=False)
    day=z.assign(day=z.time.dt.strftime("%Y-%m-%d")).groupby("day").agg(bars=("time","size"),mean_abs_diff=("abs_diff","mean"),max_abs_diff=("abs_diff","max"),different_side=("different_side","sum"))
    day.to_csv(out/"daily.csv")
    print("CD nonzero bars:",len(v),"matched:",len(z),"MT5 bars:",len(m))
    print("Period:",z.time.min() if len(z) else "-", "to",z.time.max() if len(z) else "-")
    if len(z):
        print("Mean absolute difference USD:",round(z.abs_diff.mean(),4))
        print("Median absolute difference USD:",round(z.abs_diff.median(),4))
        print("Maximum absolute difference USD:",round(z.abs_diff.max(),4))
        print("Different price/VWAP side:",int(z.different_side.sum()),"/",len(z),f"({z.different_side.mean()*100:.2f}%)")
        print("Days:",len(day))
    print("Saved:",out/"matched.csv",out/"daily.csv")
    print("WARNING: MT5 VWAP uses typical-price * tick-volume, UTC midnight reset; ClusterDelta methodology/reset may differ.")
    print("WARNING: Different-side is NOT a full strategy signal comparison; this does not validate profitability.")

if __name__=="__main__": main()
