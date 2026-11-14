"""Run a research backtest and archive immutable results on the VPS.
Usage: py -3.11 C:\\AITrading\\research\\run_and_archive.py pattern_session_backtest.py
Never stores credentials. Does not place results in public GitHub.
"""
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parent
ALLOWED={"pattern_session_backtest.py","rsi_lab.py","session_lab.py","conservative_backtest.py","asia_five_markets.py","usa_five_markets.py"}
COLUMNS=["run_id","started_utc","script","script_sha256","status","exit_code","log_path","result_count","notes"]
def main():
    script=sys.argv[1] if len(sys.argv)>1 else "pattern_session_backtest.py"
    if script not in ALLOWED:raise SystemExit("Unsupported test script: "+script)
    source=ROOT/script
    if not source.is_file():raise SystemExit("Missing script: "+str(source))
    started=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:8]
    archive=Path(os.getenv("TRADING_TEST_ARCHIVE",str(ROOT/"test_results")))
    archive.mkdir(parents=True,exist_ok=True)
    log=archive/(run_id+"-"+source.stem+".log")
    results=[]
    command=[sys.executable,str(source)]+sys.argv[2:]
    with log.open("w",encoding="utf-8") as f:
        process=subprocess.Popen(command,cwd=str(ROOT),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",bufsize=1)
        for line in process.stdout:
            print(line,end="",flush=True)
            f.write(line)
            if line.startswith(("RESULT ","SIDE ","PATTERN_COUNTS ")):
                results.append(line.strip())
        exit_code=process.wait()
    record={"run_id":run_id,"started_utc":started,"script":script,
            "script_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
            "status":"OK" if exit_code==0 and not any(x.startswith("ERROR ") for x in log.read_text(encoding="utf-8").splitlines()) else "CHECK",
            "exit_code":exit_code,"log_path":str(log),"result_count":len(results),
            "notes":"Research only; no live trades; review missing costs and skipped symbols."}
    (archive/(run_id+".json")).write_text(json.dumps({"metadata":record,"results":results},ensure_ascii=False,indent=2),encoding="utf-8")
    index=archive/"index.csv"
    with index.open("a",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=COLUMNS)
        if f.tell()==0:writer.writeheader()
        writer.writerow(record)
    print("\nARCHIVED",str(archive),"RUN",run_id,"STATUS",record["status"])
    return exit_code
if __name__=="__main__":sys.exit(main())
