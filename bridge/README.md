# Trading AI – MT5 read-only quote bridge

**Stav:** Zdrojový kód připraven, zatím nenasazeno na VPS. MT5 není připojeno.

## Architektura
Windows VPS s běžícím přihlášeným MT5 -> Python FastAPI (pouze čtení symbol_info_tick) -> HTTPS reverse proxy -> GitHub Pages frontend.

Veřejný endpoint `GET /api/quotes` poskytuje pouze Bid/Ask/spread, čas posledního ticku a stav live/stale/unavailable. Nikdy číslo účtu, heslo, obchodní pozice ani příkazy. Není určen pro soukromá data.

## Instalace na Windows VPS
1. Nainstaluj Python 3.10+ a spusť RoboForex MT5, ideálně na odděleném demo/investor účtu.
2. Ověř názvy symbolů v Market Watch a nastav odpovídající proměnné prostředí podle `.env.example` (soubor se sám nenačítá).
3. `py -m pip install -r bridge/requirements.txt`
4. Z kořene repozitáře spusť `py -m uvicorn bridge.server:app --host 127.0.0.1 --port 8765`
5. Na VPS otestuj `http://127.0.0.1:8765/api/quotes`.
6. Pro veřejný přístup nastav HTTPS reverse proxy (např. Caddy/Nginx) na vlastní subdoméně; vystav pouze GET /api/quotes a /api/health, zapni rate limiting a omezení přístupu. **Nevystavuj port 8765 přímo internetu.**
7. Ve Strategy Lab zadej HTTPS adresu API, např. `https://data.example.cz/api/quotes`. V prohlížeči se uloží jen na aktuální stránce, nikoli do GitHub repozitáře.

## Limity a bezpečnost
- GitHub Pages neumí spouštět Python ani připojit MT5 přímo.
- CORS povoluje pouze `https://pranda-sudo.github.io`; CORS **není autentizace**. Veřejný read-only endpoint je dostupný i mimo prohlížeč; nikdy nevystavuj privátní informace.
- Čerstvost kotací je 30 s; při výpadku budou označeny stale/disconnected. Tato první verze nemá persistentní úložiště, autentizaci ani HA.
- Neimplementuje zadávání obchodů ani backtesting; historická data jsou samostatný projekt.
- Data mohou podléhat licenčním omezením RoboForexu. Před veřejným zobrazováním/redistribucí kotací ověř podmínky brokera. Pokud veřejná redistribuce není dovolena, nasadit autentizovaný přístup pro vlastní použití.
- Pro produkční provoz doplnit monitoring, watchdog/restart, HTTPS konfiguraci, firewall a rate limit.
