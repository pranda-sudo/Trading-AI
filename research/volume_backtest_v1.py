"""Trading AI: research-only XAUUSD M5 VWAP/Delta backtester.

Input: normalized CSV columns:
time,open,high,low,close,volume,delta,cum_delta,vwap
Optional: spread (price units). Timestamps must be MT5 server time.
No trading API, no live orders. Requires Python 3.10+, pandas, numpy.
"""
import argparse
import json
import numpy as np
import pandas as pd

REQUIRED = ["time", "open", "high", "low", "close", "volume", "delta", "cum_delta", "vwap"]

def run(df, spread=0.35, sl_atr=1.5, rr=1.5, max_bars=24,
        start_hour=8, end_hour=22, volume_factor=1.2):
    missing = set(REQUIRED) - set(df.columns)
    if missing:
        raise ValueError(f"Missing CSV columns: {sorted(missing)}")
    d = df.copy()
    d["time"] = pd.to_datetime(d["time"], errors="raise")
    d = d.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    for col in REQUIRED[1:]:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    if "spread" in d:
        d["spread"] = pd.to_numeric(d["spread"], errors="coerce").fillna(spread)
    else:
        d["spread"] = spread
    if (d["spread"] < 0).any():
        raise ValueError("Negative spread")
    prev = d["close"].shift(1)
    tr = pd.concat([(d.high-d.low), (d.high-prev).abs(),
                    (d.low-prev).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(14, min_periods=14).mean()
    d["vol_mean"] = d.volume.shift(1).rolling(20, min_periods=20).mean()
    d["cum_prev"] = d.cum_delta.shift(1)
    d["signal"] = 0
    valid = d[REQUIRED[1:]].notna().all(axis=1) & (d.vwap > 0) & (d.atr > 0)
    active = (d.time.dt.hour >= start_hour) & (d.time.dt.hour < end_hour)
    liquid = d.volume > d.vol_mean * volume_factor
    d.loc[valid & active & liquid & (d.close > d.vwap) &
          (d.delta > 0) & (d.cum_delta > d.cum_prev), "signal"] = 1
    d.loc[valid & active & liquid & (d.close < d.vwap) &
          (d.delta < 0) & (d.cum_delta < d.cum_prev), "signal"] = -1

    trades = []
    i = 20
    while i < len(d)-1:
        signal = int(d.at[i, "signal"])
        if not signal:
            i += 1
            continue
        entry_idx = i+1
        entry = d.iloc[entry_idx]
        if (entry.time.date() != d.at[i, "time"].date() or
                entry.time.hour >= end_hour or pd.isna(entry.open)):
            i += 1
            continue
        half = float(entry.spread)/2
        entry_price = float(entry.open) + signal*half
        risk = float(d.at[i, "atr"]) * sl_atr
        stop = entry_price - signal*risk
        target = entry_price + signal*risk*rr
        exit_price, exit_reason, exit_idx = None, None, None
        last = min(len(d)-1, entry_idx+max_bars-1)
        for j in range(entry_idx, last+1):
            bar = d.iloc[j]
            if bar.time.date() != entry.time.date() or bar.time.hour >= end_hour:
                # Close at prior completed bar, not the next day's open.
                k = max(entry_idx, j-1)
                exit_idx = k
                exit_price = float(d.at[k, "close"]) - signal*float(d.at[k, "spread"])/2
                exit_reason = "session"
                break
            # Conservative: stop first when both stop and target touched.
            hit_sl = bar.low <= stop if signal == 1 else bar.high >= stop
            hit_tp = bar.high >= target if signal == 1 else bar.low <= target
            if hit_sl or hit_tp:
                exit_idx = j
                exit_price = stop if hit_sl else target
                # Gap through stop: use worse opening executable price.
                if hit_sl:
                    opened_exit = float(bar.open) - signal*float(bar.spread)/2
                    exit_price = min(stop, opened_exit) if signal == 1 else max(stop, opened_exit)
                exit_reason = "stop" if hit_sl else "target"
                break
        if exit_idx is None:
            exit_idx = last
            exit_price = float(d.at[last, "close"]) - signal*float(d.at[last, "spread"])/2
            exit_reason = "time"
        pnl = signal*(exit_price-entry_price)
        trades.append(dict(signal_time=str(d.at[i,"time"]), entry_time=str(entry.time),
                           exit_time=str(d.at[exit_idx,"time"]), side="LONG" if signal==1 else "SHORT",
                           entry=entry_price, exit=exit_price, risk=risk, pnl_price=pnl,
                           r_multiple=pnl/risk, reason=exit_reason,
                           session=("Asia" if entry.time.hour < 8 else
                                    "Europe" if entry.time.hour < 14 else "US")))
        i = exit_idx+1
    t = pd.DataFrame(trades)
    if t.empty:
        return t, {"trades":0, "note":"No trades matched conditions"}
    wins = t.pnl_price[t.pnl_price>0].sum()
    losses = -t.pnl_price[t.pnl_price<0].sum()
    equity = t.r_multiple.cumsum()
    dd = (equity-equity.cummax().clip(lower=0)).min()
    metrics = dict(trades=len(t), win_rate=round(float((t.pnl_price>0).mean()),4),
                   profit_factor=round(float(wins/losses),3) if losses else None,
                   total_r=round(float(t.r_multiple.sum()),3),
                   max_drawdown_r=round(float(dd),3),
                   by_session=t.groupby("session").agg(trades=("r_multiple","size"),
                       total_r=("r_multiple","sum")).round(3).to_dict("index"))
    return t, metrics

def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv", help="Normalized MT5+ClusterDelta M5 CSV")
    p.add_argument("--spread", type=float, default=0.35, help="Price units, NOT points")
    p.add_argument("--start-hour", type=int, default=8, help="MT5 server hour")
    p.add_argument("--end-hour", type=int, default=22, help="MT5 server hour")
    p.add_argument("--out", default="backtest_trades.csv")
    args = p.parse_args()
    if not 0 <= args.start_hour < args.end_hour <= 24:
        p.error("Invalid session hours")
    trades, metrics = run(pd.read_csv(args.csv), spread=args.spread,
                          start_hour=args.start_hour, end_hour=args.end_hour)
    trades.to_csv(args.out, index=False)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    print("Trades saved:", args.out)

if __name__ == "__main__":
    main()
