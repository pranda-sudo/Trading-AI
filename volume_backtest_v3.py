"""Research-only comparison of original, reversed, and VWAP/Delta disagreement strategies.
Requires pandas and numpy. No broker connection or order execution.
"""
import argparse
import json
from pathlib import Path
import pandas as pd
from volume_backtest_v2 import run


def evaluate(df, mode, start_hour, end_hour, spread):
    data = df.copy()
    if mode == 'delta_disagreement':
        # Existing V2 signal requires delta to align with VWAP; to test the
        # disagreement hypothesis, invert delta and cumulative delta BEFORE
        # signal generation. This keeps price/VWAP direction unchanged.
        data['delta'] = -pd.to_numeric(data['delta'], errors='coerce')
        data['cum_delta'] = -pd.to_numeric(data['cum_delta'], errors='coerce')
    trades, metrics = run(data, spread=spread, reverse=mode == 'reverse',
                          start_hour=start_hour, end_hour=end_hour)
    return trades, metrics


def main():
    p = argparse.ArgumentParser()
    p.add_argument('csv')
    p.add_argument('--out', default='v3_results')
    p.add_argument('--point', type=float, default=0.01,
                   help='MT5 symbol point size, verify in symbol specification')
    p.add_argument('--spread', type=float, default=0.35,
                   help='Fallback spread in price units when CSV spread missing')
    p.add_argument('--start-hour', type=int, default=8)
    p.add_argument('--end-hour', type=int, default=22)
    args = p.parse_args()
    if args.point <= 0 or args.spread < 0 or not 0 <= args.start_hour < args.end_hour <= 24:
        p.error('Invalid point, spread or hours')
    df = pd.read_csv(args.csv)
    if 'spread' in df:
        df['spread'] = pd.to_numeric(df['spread'], errors='coerce') * args.point
        df['spread'] = df['spread'].fillna(args.spread)
    else:
        df['spread'] = args.spread
    df['time'] = pd.to_datetime(df['time'], utc=True)
    df = df.sort_values('time').reset_index(drop=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    # A strict chronological split; indicators are warmed up inside each segment.
    cut = int(len(df) * 0.7)
    splits = {'development': df.iloc[:cut].copy(), 'holdout': df.iloc[cut:].copy()}
    rows = []
    for split_name, part in splits.items():
        for mode in ('original', 'reverse', 'delta_disagreement'):
            trades, metrics = evaluate(part, mode, args.start_hour, args.end_hour, args.spread)
            trades.to_csv(out / f'{split_name}_{mode}_trades.csv', index=False)
            row = {'sample': split_name, 'strategy': mode, 'first_bar': str(part.time.iloc[0]),
                   'last_bar': str(part.time.iloc[-1]), **metrics}
            rows.append(row)
    pd.DataFrame(rows).to_csv(out / 'comparison.csv', index=False)
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    print('Saved:', out / 'comparison.csv')
    print('NOTE: This is exploratory. No commissions, slippage, news filter, H1 EMA or VWAP retest logic.')
    print('NOTE: Confirm timestamps and the MT5 symbol point value before interpreting results.')

if __name__ == '__main__':
    main()
