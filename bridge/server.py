"""Read-only MT5 quote bridge. Python 3.10+, Windows VPS, local MT5 terminal.
Public GET /api/quotes returns quotes only; no account details or trade execution.
Run behind HTTPS reverse proxy. Do not expose uvicorn directly to internet.
"""
import os
import threading
import time
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

SYMBOLS = {
    "XAUUSD": os.getenv("MT5_XAUUSD", "XAUUSD"),
    "US30": os.getenv("MT5_US30", "US30"),
    "DE40": os.getenv("MT5_DE40", "DE40"),
    "USTECH": os.getenv("MT5_USTECH", "USTECH"),
    "US500": os.getenv("MT5_US500", "US500"),
}
ALLOWED_ORIGIN = "https://pranda-sudo.github.io"
app = FastAPI(title="Trading AI Quote Bridge", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware, allow_origins=[ALLOWED_ORIGIN], allow_methods=["GET"], allow_headers=[])
lock = threading.Lock()
state = {"updated_at": None, "quotes": {}, "status": "starting"}

def poll_forever():
    import MetaTrader5 as mt5
    while True:
        try:
            if not mt5.initialize():
                raise RuntimeError("MT5 initialization failed")
            while True:
                now = datetime.now(timezone.utc)
                quotes = {}
                for canonical, native in SYMBOLS.items():
                    if not mt5.symbol_select(native, True):
                        quotes[canonical] = {"status": "unavailable"}
                        continue
                    tick = mt5.symbol_info_tick(native)
                    if tick is None or tick.bid <= 0 or tick.ask <= 0 or tick.ask < tick.bid:
                        quotes[canonical] = {"status": "unavailable"}
                        continue
                    tick_ts = getattr(tick, "time_msc", 0) / 1000 or tick.time
                    age = max(0, now.timestamp() - tick_ts)
                    quotes[canonical] = {
                        "status": "live" if age <= 30 else "stale",
                        "symbol": native,
                        "bid": float(tick.bid),
                        "ask": float(tick.ask),
                        "spread": float(tick.ask - tick.bid),
                        "tick_time": datetime.fromtimestamp(tick_ts, timezone.utc).isoformat(),
                        "age_seconds": round(age, 1),
                    }
                with lock:
                    state.update(updated_at=now.isoformat(), quotes=quotes, status="online")
                time.sleep(2)
        except Exception:
            with lock:
                state["status"] = "disconnected"
                state["quotes"] = {}
            time.sleep(5)
        finally:
            try: mt5.shutdown()
            except Exception: pass

@app.on_event("startup")
def startup():
    threading.Thread(target=poll_forever, daemon=True).start()

@app.get("/api/quotes")
def quotes():
    with lock:
        snapshot = {"updated_at": state["updated_at"], "status": state["status"], "quotes": {k:dict(v) for k,v in state["quotes"].items()}}
    # Recompute age so cached/stale values never appear fresh after a collector failure.
    now = datetime.now(timezone.utc)
    for q in snapshot["quotes"].values():
        if "tick_time" in q:
            age = max(0, (now - datetime.fromisoformat(q["tick_time"])).total_seconds())
            q["age_seconds"] = round(age, 1)
            q["status"] = "live" if age <= 30 and snapshot["status"] == "online" else "stale"
    return snapshot

@app.get("/api/health")
def health():
    with lock:
        return {"status": state["status"], "updated_at": state["updated_at"]}
