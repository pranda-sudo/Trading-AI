# GitHub-only testovací režim

V této fázi se **nepřipojuje MT5, RoboForex ani žádný reálný obchodní účet**.

Po každém pushi do engine/ nebo tests/ spustí GitHub Actions:
1. Python unit testy.
2. Generování umělých OHLC svíček.
3. Smoke test backtestu Scalper V1.
4. Uložení JSON výsledků jako GitHub Actions artifact.

Manuální spuštění: GitHub → Actions → Scalper V1 tests → Run workflow.

Lokálně: `python -m unittest discover -s tests -v`, pak `python -m tests.make_fixture` a `python -m engine.run /tmp/scalper_fixture.csv --output /tmp/scalper_results.json --stop-distance 0.3 --spread 0.02`.

**Pozor:** Umělá data ověřují, že software běží. Nevypovídají nic o skutečné ziskovosti. Pro ekonomické vyhodnocení potřebujeme licencovaná nebo vlastní reálná historická data, oddělený out-of-sample test a věrné obchodní náklady. Výsledky z Actions nejsou automaticky zobrazované na GitHub Pages.
