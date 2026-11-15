// Conditional, qualitative hypotheses, never deterministic trading signals.
export function economicScenarios(e){
 const title=(e.title||'').toLowerCase(),usd=e.currency==='USD',eur=e.currency==='EUR';
 const rates=/interest rate|rate decision|federal funds|refinancing rate|deposit facility|monetary policy/.test(title);
 const inflation=/cpi|consumer price|pce|inflation|producer price/.test(title);
 const employment=/nonfarm|payroll|unemployment|employment change|jobless/.test(title);
 if(rates){
  return [
   (usd?'Fed / USD':eur?'ECB / EUR':'Centrální banka')+': porovnávej skutečné rozhodnutí s očekáváním, nikoli jen směr změny sazeb.',
   usd?'Překvapivě přísnější Fed: často silnější USD a výnosy → tlak na XAUUSD a US500/USTECH/US30; DE40 může reagovat nepřímo.':'Překvapivě přísnější ECB: často silnější EUR; DE40 může čelit tlaku vyšších výnosů, ale záleží na ekonomickém výhledu.',
   usd?'Překvapivě mírnější Fed: často podpora XAUUSD a akcií; při obavách z recese mohou akcie i klesat.':'Překvapivě mírnější ECB: potenciální podpora DE40, ale slabší EUR a obavy o ekonomiku mohou efekt změnit.',
   'Po rozhodnutí sleduj tiskovou konferenci, projekce a očekávanou trajektorii dalších sazeb.'
  ];
 }
 if(inflation)return [
  'Vyšší inflace než konsenzus může zvýšit očekávání sazeb a výnosy dluhopisů.',
  usd?'USD: často negativní pro XAUUSD a americké akcie; výsledek závisí na výnosech a očekávání Fedu.':'EUR: možný dopad na očekávání ECB a DE40.',
  'Nižší inflace může mít opačný efekt, pokud trh neřeší výrazné zpomalení ekonomiky.'
 ];
 if(employment)return [
  'Silnější americký trh práce může podpořit dolar a výnosy, ale i akcie díky lepšímu růstu.',
  'Slabší data mohou podpořit očekávání snížení sazeb, nebo vyvolat obavy z recese.',
  'Pro XAUUSD, US30, US500 a USTECH nelze bez dalších informací stanovit jednoznačný směr.'
 ];
 return [
  'Sleduj překvapení proti očekávání a reakci USD, dluhopisových výnosů a volatility.',
  usd?'Možný dopad: XAUUSD, US30, US500, USTECH; DE40 nepřímo.':eur?'Možný dopad: DE40 a nepřímo ostatní trhy.':'Přímý dopad na sledované instrumenty není jednoznačný.',
  'Bez ověřeného ekonomického kontextu nelze předem stanovit spolehlivý LONG/SHORT.'
 ];
}
