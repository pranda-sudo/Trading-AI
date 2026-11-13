import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
LOGS = ROOT / "logs"
TERMINAL = os.environ.get("TRADING_AI_MT5_PATH", r"C:\AItrading\petr\terminal64.exe")
EXPECTED_LOGIN = int(os.environ.get("TRADING_AI_MT5_LOGIN", "68531109"))
INTERVAL = max(30, int(os.environ.get("TRADING_AI_INTERVAL_SECONDS", "60")))
BARS = max(3, min(500, int(os.environ.get("TRADING_AI_BARS_PER_POLL", "10"))))
SYMBOLS = {"XAUUSD": "XAUUSD", "US30": ".US30Cash", "DE40": ".DE40Cash", "USTECH": ".USTECHCash", "US500": ".US500Cash"}
FRAMES = {"M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}
FIELDS = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
LOCK = ROOT / "collector.lock"


def append_closed_bars(path, rates):
    last = -1
    if path.exists():
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 4096))
            for line in reversed(f.read().decode("utf-8", errors="replace").splitlines()):
                try:
                    last = int(line.split(",")[0].strip().strip('"'))
                    break
                except (ValueError, IndexError):
                    pass
    added = 0
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if path.stat().st_size == 0:
            writer.writerow(FIELDS)
        for bar in rates[:-1]:
            timestamp = int(bar["time"])
            if timestamp <= last:
                continue
            writer.writerow([int(bar[k]) if k in ("time", "tick_volume", "spread", "real_volume") else float(bar[k]) for k in FIELDS])
            last = timestamp
            added += 1
    return added


def poll():
    if not mt5.initialize(path=TERMINAL, timeout=10000):
        raise RuntimeError(f"MT5 connection failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None or account.login != EXPECTED_LOGIN or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise RuntimeError("SAFETY STOP: incorrect account or not DEMO")
        snapshot = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "source": "RoboForex MT5 demo", "markets": {}}
        for name, symbol in SYMBOLS.items():
            info = mt5.symbol_info(symbol)
            if info is None:
                logging.warning("Symbol not found: %s", symbol)
                continue
            if not info.visible and not mt5.symbol_select(symbol, True):
                logging.warning("Cannot select %s", symbol)
                continue
            tick = mt5.symbol_info_tick(symbol)
            item = {"symbol": symbol, "bid": float(tick.bid) if tick else None, "ask": float(tick.ask) if tick else None,
                    "tick_time_utc": datetime.fromtimestamp(tick.time, timezone.utc).isoformat() if tick else None, "timeframes": {}}
            for label, frame in FRAMES.items():
                rates = mt5.copy_rates_from_pos(symbol, frame, 0, BARS)
                if rates is None or len(rates) < 2:
                    logging.warning("Missing bars %s %s: %s", name, label, mt5.last_error())
                    continue
                added = append_closed_bars(DATA / f"{name}_{label}.csv", rates)
                item["timeframes"][label] = {"new_closed_bars": added, "last_closed_utc": datetime.fromtimestamp(int(rates[-2]["time"]), timezone.utc).isoformat()}
            snapshot["markets"][name] = item
        temp = DATA / "latest.json.tmp"
        temp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, DATA / "latest.json")
        return len(snapshot["markets"])
    finally:
        mt5.shutdown()


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(LOGS / "collector.log", encoding="utf-8"), logging.StreamHandler(sys.stdout)])
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except FileExistsError:
        raise SystemExit("Collector already running, or stale collector.lock. Verify before removing the lock.")
    try:
        logging.info("Starting read-only demo data collection")
        while True:
            start = time.monotonic()
            try:
                logging.info("Updated %s markets", poll())
            except Exception:
                logging.exception("Polling error; retry next interval")
            time.sleep(max(1, INTERVAL - (time.monotonic() - start)))
    except KeyboardInterrupt:
        logging.info("Stopped")
    finally:
        mt5.shutdown()
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
