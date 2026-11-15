"""Audit MT5 historical calendar timestamps against independently verified UTC releases.
No database writes, no trades. Uses CSV export from TradingAICalendarHistory.mq5.
Reference CSV columns: event_key,verified_utc,source_url
Only use official/reliable publication timestamps; do not guess from price charts.
Run: py -3.11 audit_calendar_timezone.py --calendar PATH --references PATH
"""
import argparse,csv,collections,datetime as dt,json,statistics
from pathlib import Path

def parse(value):
    value=value.strip()
    if value.endswith("Z"):value=value[:-1]+"+00:00"
    result=dt.datetime.fromisoformat(value)
    if result.tzinfo is None:raise ValueError("Reference time must have UTC offset")
    return result.astimezone(dt.timezone.utc)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--calendar",required=True)
    p.add_argument("--references",required=True)
    p.add_argument("--output",default="results/calendar_timezone_audit.json")
    a=p.parse_args()
    with open(a.calendar,encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f,delimiter=";")
        if not {"event_key","event_time"}.issubset(reader.fieldnames or []):raise ValueError("Invalid MT5 calendar headers")
        events={r["event_key"]:r for r in reader if r.get("event_key")}
    comparisons=[];errors=[]
    with open(a.references,encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if not {"event_key","verified_utc","source_url"}.issubset(reader.fieldnames or []):raise ValueError("Expected event_key,verified_utc,source_url")
        for r in reader:
            try:
                key=r["event_key"].strip()
                if not key or key not in events:raise ValueError("Unknown event_key")
                if not r["source_url"].startswith("https://"):raise ValueError("Source URL required")
                recorded=parse(events[key]["event_time"])
                verified=parse(r["verified_utc"])
                difference=(recorded-verified).total_seconds()/60
                comparisons.append({"event_key":key,"mt5_export_utc":recorded.isoformat(),
                  "verified_utc":verified.isoformat(),"difference_minutes":difference,
                  "month":verified.strftime("%Y-%m"),"source_url":r["source_url"]})
            except (ValueError,KeyError) as ex:errors.append({"event_key":r.get("event_key"),"error":str(ex)})
    by_month=collections.defaultdict(list)
    for r in comparisons:by_month[r["month"]].append(r["difference_minutes"])
    monthly={month:{"n":len(vals),"offset_median_minutes":statistics.median(vals),
             "differences_minutes":sorted(set(vals))} for month,vals in sorted(by_month.items())}
    # Require independent checks across both seasonal halves and multiple years.
    winter={r["verified_utc"][:7] for r in comparisons if int(r["verified_utc"][5:7]) in (11,12,1,2)}
    summer={r["verified_utc"][:7] for r in comparisons if int(r["verified_utc"][5:7]) in (5,6,7,8)}
    sufficient=len(comparisons)>=12 and len(winter)>=3 and len(summer)>=3 and not errors
    verified=sufficient and all(abs(r["difference_minutes"])<=1 for r in comparisons)
    report={"status":"PASS" if verified else "NOT_VERIFIED","reference_count":len(comparisons),
      "winter_months":len(winter),"summer_months":len(summer),
      "calendar_rows":len(events),"monthly":monthly,"comparisons":comparisons,"errors":errors,
      "limitations":["Checks only the supplied independently verified reference events",
        "A PASS does not prove that every historical timestamp is correct",
        "Never apply blanket offsets based on best backtest profit"]}
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("AUDIT",report["status"],"references",len(comparisons),"winter months",len(winter),"summer months",len(summer))
    for month,row in monthly.items():print(month,row)
    for error in errors:print("ERROR",error)
    print("SAVED",path)
    if not verified:raise SystemExit(2)

if __name__=="__main__":main()
