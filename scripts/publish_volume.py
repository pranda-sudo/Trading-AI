"""Publish derived profiles only; read-only with respect to MT5."""
import os,json,csv,argparse,urllib.request
from pathlib import Path
from datetime import datetime,timezone
p=argparse.ArgumentParser()
p.add_argument("--root",default=r"C:\AItrading\volume")
a=p.parse_args()
root=Path(a.root)
url=os.environ["SUPABASE_URL"].rstrip("/")
if url!="https://hatzdirgwutbdarpgwro.supabase.co": raise RuntimeError("Wrong project")
key=os.environ.get("SUPABASE_SECRET_KEY") or os.environ["SUPABASE_SERVICE_ROLE_KEY"]
now=datetime.now(timezone.utc).isoformat()
rows=[]
for file,period,field in [("daily_profile.csv","daily","utc_date"),("weekly_profile.csv","weekly","utc_week"),("tick_profile.csv","tick_daily","utc_date")]:
    with (root/"data_year"/"XAUUSD"/"bin_1"/file).open(newline="",encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(dict(symbol="XAUUSD",period=period,period_start=r[field],payload=r,updated_at=now))
live=json.loads((root/"live_v4"/"latest.json").read_text(encoding="utf-8"))
if live["symbol"]!="XAUUSD": raise RuntimeError("Wrong symbol")
rows.append(dict(symbol="XAUUSD",period="live",period_start="latest",payload=live,updated_at=now))
headers={"apikey":key,"Content-Type":"application/json","Prefer":"resolution=merge-duplicates,return=minimal"}
if not key.startswith("sb_secret_"): headers["Authorization"]="Bearer "+key
for i in range(0,len(rows),100):
    req=urllib.request.Request(url+"/rest/v1/volume_profiles?on_conflict=symbol,period,period_start",data=json.dumps(rows[i:i+100],allow_nan=False).encode(),headers=headers,method="POST")
    with urllib.request.urlopen(req,timeout=30) as res: print("OK",res.status,i,flush=True)
print("Published",len(rows),"profiles")
