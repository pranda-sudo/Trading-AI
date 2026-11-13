"""Read-only upload of MT5 CSV candle history to private Supabase tables.
Run on Windows VPS. Requires SUPABASE_URL and SUPABASE_SECRET_KEY environment variables.
No inbound port, broker password, or trade permissions required.
"""
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = Path(os.getenv("MT5_HISTORY_DIR", r"C:\AItrading\collector\history"))
SYMBOLS = ("XAUUSD", "US30", "DE40", "USTECH", "US500")
FRAMES = ("M1", "M5", "M15", "H1", "H4", "D1")
URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SECRET_KEY"]
STATE = Path(os.getenv("UPLOAD_STATE_FILE", r"C:\AItrading\collector\upload_state.json"))
BATCH = 100
MAX_RETRIES = 5

def iso_time(raw):
    raw = str(raw).strip()
    if raw.isdigit():
        return datetime.fromtimestamp(int(raw), timezone.utc).isoformat()
    raw = raw.replace("Z", "+00:00")
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # MT5 candle timestamps are UTC
    return dt.astimezone(timezone.utc).isoformat()

def api_upsert(rows):
    """Upload a batch, retry temporary errors and show Supabase JSON errors."""
    body = json.dumps(rows, separators=(",", ":"), allow_nan=False).encode("utf-8")
    endpoint = URL + "/rest/v1/market_candles?on_conflict=symbol,timeframe,candle_time"
    for attempt in range(MAX_RETRIES):
        headers = {
            "apikey": KEY,
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }
        # New sb_secret_ API keys are opaque keys, not JWT bearer tokens.
        # Legacy service_role JWTs can be sent as Authorization: Bearer.
        if not KEY.startswith("sb_secret_"):
            headers["Authorization"] = "Bearer " + KEY
        req = Request(endpoint, data=body, method="POST", headers=headers)
        try:
            with urlopen(req, timeout=90) as response:
                if response.status not in (200, 201, 204):
                    raise RuntimeError("Unexpected API status " + str(response.status))
            return
        except HTTPError as exc:
            detail = exc.read(4096).decode("utf-8", errors="replace")
            if exc.code in (408, 429, 500, 502, 503, 504) and attempt < MAX_RETRIES - 1:
                wait = min(2 ** attempt * 3, 30)
                print(f"Temporary HTTP {exc.code}; retrying in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(
                f"Supabase HTTP {exc.code}; response: {detail}; "
                f"batch first={rows[0]['symbol']} {rows[0]['timeframe']} "
                f"{rows[0]['candle_time']}, last={rows[-1]['candle_time']}"
            ) from exc
        except (URLError, TimeoutError) as exc:
            if attempt == MAX_RETRIES - 1:
                raise RuntimeError("Supabase network error: " + str(exc)) from exc
            time.sleep(min(2 ** attempt * 3, 30))


def load_rows(path, symbol, frame, since):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(2048)
        f.seek(0)
        delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
        reader = csv.DictReader(f, delimiter=delimiter)
        for original in reader:
            r = {k.strip().lower().strip("<>"): v for k, v in original.items() if k}
            t = r.get("time_utc") or r.get("datetime") or (r["date"] + " " + r.get("time", "00:00:00") if r.get("date") else r.get("time"))
            if not t:
                raise ValueError(f"Missing time column in {path.name}; headers: {list(r)}")
            ts = iso_time(t)
            if since and ts <= since:
                continue
            yield {"symbol": symbol, "timeframe": frame, "candle_time": ts,
                   "open": float(r["open"]), "high": float(r["high"]),
                   "low": float(r["low"]), "close": float(r["close"]),
                   "tick_volume": int(float(r.get("tick_volume") or r.get("tickvol") or 0)),
                   "spread": int(float(r.get("spread") or 0)),
                   "real_volume": int(float(r.get("real_volume") or r.get("vol") or 0))}

def main():
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    total = 0
    for symbol in SYMBOLS:
        for frame in FRAMES:
            path = BASE / f"{symbol}_{frame}.csv"
            if not path.exists():
                print("SKIP missing", path)
                continue
            key = f"{symbol}_{frame}"
            batch = []
            try:
                for row in load_rows(path, symbol, frame, state.get(key)):
                    batch.append(row)
                    if len(batch) >= BATCH:
                        api_upsert(batch)
                        state[key] = batch[-1]["candle_time"]
                        STATE.parent.mkdir(parents=True, exist_ok=True)
                        STATE.write_text(json.dumps(state, indent=2))
                        total += len(batch)
                        batch.clear()
                if batch:
                    api_upsert(batch)
                    state[key] = batch[-1]["candle_time"]
                    STATE.parent.mkdir(parents=True, exist_ok=True)
                    STATE.write_text(json.dumps(state, indent=2))
                    total += len(batch)
                print("OK", key)
            except Exception as exc:
                print("ERROR", key, str(exc), file=sys.stderr)
                raise
    print("Uploaded", total, "candles")

if __name__ == "__main__":
    main()
