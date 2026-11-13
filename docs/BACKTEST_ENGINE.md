# Backtesting engine V0.1

Implementováno: Python 3.10+ (stdlib), CSV OHLC import, SMA crossover LONG/SHORT, SL/TP, spread, skluz, komise, denní limit počtu vstupů, limit realizované denní ztráty, uzavření pozice na konci seance, export JSON, unit testy.

Spuštění: `python -m unittest discover -s tests -v` a `python -m engine.run cesta/k/minutovym_datum.csv --stop-distance 2 --spread 0.15`.

CSV: `time,open,high,low,close,spread`; ISO-8601 timestamp s časovým posunem, seřazeno vzestupně. Spread a vzdálenost SL v **cenových jednotkách**, nikoliv pipech nebo bodech MT5.

**Omezení:** Experimentální výzkumný engine, ne MT5 EA. Vstup na open následující svíčky po potvrzeném signálu; SL má prioritu, pokud SL a TP zasáhne stejná svíčka. Nezahrnuje margin, velikosti kontraktů, funding/swap, obchodní kalendář ani tick-level exekuci. Daily stop počítá realizované P/L; pro produkční verzi doplnit floating P/L. Ukončení na konci seance je simulace na dostupných svíčkách, ne garance uzavření skutečného příkazu. Časová pásma a DST nutno ověřit proti brokerovi.

Před jakýmkoli nasazením: kalibrace instrumentů, validace spreadu, komise a skluzu, odstranění biasů, tickový backtest, walk-forward, out-of-sample a demo forward test. Žádná live exekuce ani slib zisku.
