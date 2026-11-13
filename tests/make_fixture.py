"""Generate SYNTHETIC OHLC only; never treat as real market prices."""
import csv
from datetime import datetime, timedelta, timezone

def main(path="/tmp/scalper_fixture.csv"):
    start=datetime(2026,11,12,8,0,tzinfo=timezone.utc)
    prices=[100+i*.03 for i in range(65)]+[102-i*.10 for i in range(50)]+[97+i*.15 for i in range(50)]
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f)
        w.writerow(["time","open","high","low","close","spread"])
        for i,p in enumerate(prices):
            w.writerow([(start+timedelta(minutes=i)).isoformat(),p,p+.12,p-.12,p,0.02])
    print(f"Synthetic fixture written to {path}")

if __name__=="__main__":
    main()
