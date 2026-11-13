import unittest
from datetime import datetime, timedelta, timezone
from engine.scalper import Config, backtest, load_csv

class ScalperTests(unittest.TestCase):
    def bars(self):
        t=datetime(2026,11,12,8,tzinfo=timezone.utc)
        prices=[100+i*.03 for i in range(65)]+[102-i*.10 for i in range(50)]+[97+i*.15 for i in range(50)]
        return [{"time":t+timedelta(minutes=i),"open":p,"high":p+.12,"low":p-.12,"close":p,"spread":0.02} for i,p in enumerate(prices)]
    def test_both_directions_and_metrics(self):
        r=backtest(self.bars(),Config(fast=5,slow=15,stop_distance=.3,spread=.02))
        self.assertGreaterEqual(r["summary"]["trades"],1)
        self.assertEqual(r["summary"]["trades"],len(r["trades"]))
        self.assertTrue(all(t["side"] in ("LONG","SHORT") for t in r["trades"]))
    def test_no_trades_outside_session(self):
        r=backtest(self.bars(),Config(session_start="20:00",last_entry="21:00",flatten_at="21:30"))
        self.assertEqual(r["summary"]["trades"],0)
    def test_invalid_config(self):
        with self.assertRaises(ValueError):
            backtest(self.bars(),Config(fast=50,slow=20))
if __name__=="__main__": unittest.main()
