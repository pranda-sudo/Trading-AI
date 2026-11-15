"""Forward-only XAUUSD USA shadow-trade monitor (NO orders).
First invocation establishes an activation timestamp and records no old trades.
Subsequent invocations compare newly completed simulated trades with a fixed
60-minute news-entry blackout. No live broker execution is performed.
Requires SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY and requests on trusted VPS.
"""
import os,json,math,sys,requests
from pathlib import Path
from datetime import datetime,timezone,timedelta
import conservative_backtest as bt
from news_blackout_lab import fetch_events,compare,subset
from session_lab import summarize

ROOT=Path(__file__).resolve().parent
STATE=ROOT/"results"/"xauusd_forward_state.json"
WINDOW=60
def utc(s):return bt.dt(s)
def now():return datetime.now(timezone.utc)
def save(state):
    STATE.parent.mkdir(exist_ok=True)
    tmp=STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state,indent=2,ensure_ascii=False),encoding="utf-8")
    tmp.replace(STATE)
def publish(state,kept,blocked):
    url=os.environ["SUPABASE_URL"].rstrip("/")
    key=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    stats=summarize(kept)
    payload={"id":"XAUUSD_USA","activated_utc":state["activated_utc"],
      "last_check_utc":state["last_check_utc"],"window_minutes":WINDOW,
      "cost_price_units":state["cost_price_units"],"total_trades":len(kept)+len(blocked),
      "kept_trades":len(kept),"blocked_trades":len(blocked),
      "net_r":stats["net_R"],"winrate_pct":stats["winrate_pct"],
      "profit_factor":stats["profit_factor"],"max_drawdown_r":stats["max_drawdown_R"],
      "expectancy_r":stats["expectancy_R"],"status":"research"}
    response=requests.post(url+"/rest/v1/xauusd_shadow_summary",json=payload,
      headers={"apikey":key,"Authorization":"Bearer "+key,
               "Prefer":"resolution=merge-duplicates,return=minimal",
               "Content-Type":"application/json"},timeout=30)
    response.raise_for_status()

def main():
    cost=float(os.getenv("BACKTEST_COST_XAUUSD","0.30"))
    if not math.isfinite(cost) or cost<=0:raise ValueError("Invalid cost")
    STATE.parent.mkdir(exist_ok=True)
    if not STATE.exists():
        state={"activated_utc":now().isoformat(),"cost_price_units":cost,"window_minutes":WINDOW,
               "trades":{},"last_check_utc":None,"mode":"shadow-research-no-orders"}
        save(state)
        print("INITIALIZED",STATE,"at",state["activated_utc"])
        print("Only FUTURE trade entries will be recorded. Run again later.")
        return
    state=json.loads(STATE.read_text(encoding="utf-8"))
    if state.get("mode")!="shadow-research-no-orders" or state.get("window_minutes")!=WINDOW:
        raise RuntimeError("Incompatible state")
    if abs(float(state["cost_price_units"])-cost)>1e-9:
        raise RuntimeError("Cost assumption changed; cannot mix results")
    activated=utc(state["activated_utc"])
    # Conservative backtest outputs only fully simulated trades, but its final
    # bar can still be forming in an imperfect feed. Require a 4-hour delay.
    mature=now()-timedelta(hours=4)
    trades=sorted(subset(bt.test("XAUUSD",cost=cost),"USA"),key=lambda x:utc(x["time"]))
    candidates=[t for t in trades if activated<utc(t["time"])<=mature]
    if candidates:
        events=fetch_events(utc(candidates[0]["time"])-timedelta(hours=2),
                            utc(candidates[-1]["time"])+timedelta(hours=2))
        if not events:raise RuntimeError("No calendar events: refusing to classify safe trades")
        for t in candidates:
            entry=utc(t["time"])
            # Do not assume no events on a day with missing calendar coverage.
            # Check existence of calendar data in +/- 24h; still only a heuristic.
            if not any(abs((utc(e["event_time"])-entry).total_seconds())<=86400 for e in events):
                print("SKIP unverified calendar coverage",t["time"]);continue
            _,excluded=compare([t],events,"XAUUSD",WINDOW)
            key=t["time"]+"|"+t["side"]
            item={"time":t["time"],"side":t["side"],"entry":t["entry"],
                  "R":t["R"],"blocked_by_news":bool(excluded)}
            if key in state["trades"] and state["trades"][key]!=item:
                raise RuntimeError("Historical simulated trade changed: investigate feed before continuing")
            state["trades"][key]=item
    state["last_check_utc"]=now().isoformat()
    save(state)
    rows=sorted(state["trades"].values(),key=lambda x:x["time"])
    kept=[t for t in rows if not t["blocked_by_news"]]
    blocked=[t for t in rows if t["blocked_by_news"]]
    publish(state,kept,blocked)
    print("PUBLISHED shadow summary to Supabase")
    print("FORWARD SHADOW XAUUSD USA; activation",state["activated_utc"])
    print("All completed simulated trades",len(rows),summarize(rows))
    print("Kept with +/-60min news filter",len(kept),summarize(kept))
    print("Blocked by news",len(blocked),summarize(blocked))
    print("STATE",STATE)
    print("NOT REAL FILLS. Simulated trades are computed retrospectively; no intrabar live signal feed.")
    print("This tracker does NOT resimulate subsequent entries after excluded trades.")

if __name__=="__main__":main()
