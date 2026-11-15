"""Sync MT5 calendar CSV (Common Files) to Supabase. Run hourly on VPS.
Requires environment: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (server only).
Optional MT5_CALENDAR_CSV points to MetaTrader terminal Common/Files/trading_ai_calendar.csv.
Never embed service keys in GitHub or browser code.
"""
import csv, json, os, sys, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone

def locate():
    override=os.getenv("MT5_CALENDAR_CSV")
    if override:return Path(override)
    appdata=Path(os.environ.get("APPDATA",""))
    common=appdata/"MetaQuotes"/"Terminal"/"Common"/"Files"/"trading_ai_calendar.csv"
    return common

def numeric(s):
    if not s:return None
    try:return float(s)
    except ValueError:return None

def run():
    url=os.getenv("SUPABASE_URL","").rstrip("/")
    key=os.getenv("SUPABASE_SERVICE_ROLE_KEY","")
    if not url.startswith("https://") or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY as VPS environment variables")
    source=locate()
    if not source.is_file():raise FileNotFoundError(f"Calendar CSV not found: {source}")
    rows=[]
    with source.open("r",encoding="cp1252",newline="") as stream:
        for item in csv.DictReader(stream,delimiter=";"):
            if not item.get("event_key") or not item.get("event_time"):continue
            try:datetime.fromisoformat(item["event_time"].replace("Z","+00:00"))
            except ValueError:continue
            rows.append({
              "event_key":item["event_key"],"event_id":int(item["event_id"]),
              "value_id":int(item["value_id"]),"event_time":item["event_time"],
              "currency":item["currency"],"country":item.get("country"),
              "title":item["title"],"importance":int(item["importance"]),
              "previous_value":numeric(item.get("previous_value")),
              "forecast_value":numeric(item.get("forecast_value")),
              "actual_value":numeric(item.get("actual_value")),
              "unit":item.get("unit"),"source":"MT5 calendar"
            })
    if not rows:print("No calendar events available; verify MT5 calendar connection.");return
    original_count=len(rows)
    unique_rows={}
    for row in rows:
        unique_rows[row["event_key"]]=row
    rows=list(unique_rows.values())
    if len(rows)!=original_count:
        print(f"Removed {original_count-len(rows)} duplicate event_key rows")
    endpoint=url+"/rest/v1/economic_events?on_conflict=event_key"
    for start in range(0,len(rows),150):
        payload=json.dumps(rows[start:start+150]).encode()
        request=urllib.request.Request(endpoint,data=payload,method="POST",headers={
          "apikey":key,"Authorization":"Bearer "+key,"Content-Type":"application/json",
          "Prefer":"resolution=merge-duplicates,return=minimal"})
        try:
            with urllib.request.urlopen(request,timeout=45) as response:response.read()
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"Supabase HTTP {error.code}: {error.read(400).decode(errors='replace')}") from error
    print(f"Synced {len(rows)} MT5 calendar rows at {datetime.now(timezone.utc).isoformat()}")
if __name__=="__main__":
    try:run()
    except Exception as error:print("Calendar sync failed:",error,file=sys.stderr);sys.exit(1)
