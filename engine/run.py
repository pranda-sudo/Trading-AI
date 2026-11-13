"""Usage: python -m engine.run data.csv --output results.json"""
import argparse
import json
from dataclasses import asdict
from .scalper import Config, load_csv, backtest

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--output",default="results.json")
    parser.add_argument("--stop-distance",type=float,default=2.0)
    parser.add_argument("--spread",type=float,default=0.15)
    args=parser.parse_args()
    cfg=Config(stop_distance=args.stop_distance,spread=args.spread)
    result=backtest(load_csv(args.csv),cfg)
    with open(args.output,"w",encoding="utf-8") as f:
        json.dump({"config":asdict(cfg),**result},f,indent=2,ensure_ascii=False)
    print(json.dumps(result["summary"],ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
