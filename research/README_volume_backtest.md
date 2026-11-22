# Volume Backtest v1 (research only)

Standalone backtester for **XAUUSD M5**, no live trading.

## Input
CSV with headers:
`time,open,high,low,close,volume,delta,cum_delta,vwap`
Optional `spread` column in **XAUUSD price units**.

The existing ClusterDelta history CSV is **not** directly compatible. It contains indicator/buffer/value rows and must first be joined by `bar_time_mt5` with MT5 OHLC M5 data. Confirm which VWAP buffer is the actual central VWAP and validate every field; do not assume buffer numbers. Reject MT5 EMPTY_VALUE, zero/missing VWAP and invalid timestamps. Use only candles whose indicators were known at close. Time is **MT5 server time**; verify timezone/DST before setting session hours.

## Install / run (Windows VPS PowerShell)
```powershell
py -m pip install pandas numpy
py research/volume_backtest_v1.py data/xauusd_m5_normalized.csv --spread 0.35 --start-hour 8 --end-hour 22 --out trades.csv
```
The 0.35 spread is an **illustrative assumption**, not measured RoboForex costs. Use actual historical spread, commissions and slippage before interpreting results.

## Strategy
At closed bar: price relative to daily VWAP, volume above trailing 20-bar mean, signed Delta and cumulative Delta confirmation. Entry at next bar open. ATR(14) stop (1.5x), target (1.5R), max 24 bars, session cutoff. When both SL and TP touch in a bar, stop wins. No overlapping trades. Results in R and price units, not USD.

## Limitations
- No economic-news exclusion yet; no fees/commissions or realistic variable slippage.
- Does not infer true exchange order flow from MT5 tick volume.
- Missing/invalid values and broker-to-futures source mismatch need validation.
- Intrabar fills are approximate; gap handling is conservative for stops.
- No out-of-sample, walk-forward or robustness testing yet.
- Do not deploy to live trading.

Next: build validated normalization/export step from the collector, then test on real data and add news filtering and cost model.
