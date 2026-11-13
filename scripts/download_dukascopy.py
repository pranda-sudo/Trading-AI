#!/usr/bin/env python3
"""Download Dukascopy M1 sample using dukascopy-node CLI, normalize for Trading AI.
Requires Node.js/npx and network access. Never commits data to GitHub.
Usage: python scripts/download_dukascopy.py --symbol xauusd --from-date 2026-10-01 --to-date 2026-10-08
"""
import argparse
import csv
import os
from pathlib import Path
import subprocess
import tempfile
from datetime import datetime, timezone

SYMBOLS={"xauusd","usa500idxusd","usa30idxusd","usatechidxusd","deuidxeur"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbol",default="xauusd",choices=sorted(SYMBOLS))
    p.add_argument("--from-date",default="2026-10-01")
    p.add_argument("--to-date",default="2026-10-08")
    p.add_argument("--output",default=None)
    a=p.parse_args()
    start=datetime.fromisoformat(a.from_date)
    end=datetime.fromisoformat(a.to_date)
    if start>=end: p.error("from-date must be before to-date")
    if (end-start).days>31: p.error("Download at most 31 days per batch")
    output=Path(a.output or f"data/{a.symbol}_m1_{a.from_date}_{a.to_date}.csv")
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        cmd=["npx","--yes","dukascopy-node","-i",a.symbol,"-from",a.from_date,"-to",a.to_date,"-t","m1","-f","csv"]
        print("Downloading",a.symbol,a.from_date,a.to_date,flush=True)
        subprocess.run(cmd,cwd=tmp,check=True,timeout=900)
        candidates=list(Path(tmp).rglob("*.csv"))
        if len(candidates)!=1: raise RuntimeError(f"Expected one CSV, got {len(candidates)}. Inspect CLI output and source format.")
        with candidates[0].open(newline="",encoding="utf-8-sig") as src,output.open("w",newline="",encoding="utf-8") as dst:
            reader=csv.DictReader(src)
            if not reader.fieldnames or not all(k in reader.fieldnames for k in ("timestamp","open","high","low","close")):
                raise RuntimeError(f"Unexpected CSV columns: {reader.fieldnames}")
            writer=csv.writer(dst)
            writer.writerow(["time","open","high","low","close","spread"])
            count=0
            for row in reader:
                timestamp=datetime.fromtimestamp(int(row["timestamp"])/1000,timezone.utc).isoformat()
                writer.writerow([timestamp,row["open"],row["high"],row["low"],row["close"],""])
                count+=1
        if count==0: raise RuntimeError("Downloaded CSV contains no candles")
        print(f"Saved {count} candles to {output}")
        print("NOTE: Bid-side OHLC; spread absent. Set realistic spread in backtester. Keep data private.")
if __name__=="__main__":main()
