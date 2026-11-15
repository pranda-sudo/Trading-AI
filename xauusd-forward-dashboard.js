import {supabase as db} from "./auth.js";

const root=document.createElement("section");
root.className="card";root.id="xauusd-forward-dashboard";
root.innerHTML=`
<style>
#xauusd-forward-dashboard .shadow-head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
#xauusd-forward-dashboard .shadow-meta{display:flex;flex-wrap:wrap;gap:9px;margin:12px 0 16px}
#xauusd-forward-dashboard .shadow-chip{background:#202f46;border:1px solid #34465f;border-radius:10px;padding:9px 12px;color:#b8cce5;font-size:12px}
#xauusd-forward-dashboard .shadow-track{display:flex;height:14px;border-radius:10px;background:#34445b;overflow:hidden;margin:12px 0 8px}
#xauusd-forward-dashboard .shadow-allowed{background:#36bc95;width:0}
#xauusd-forward-dashboard .shadow-blocked{background:#edaa59;width:0}
#xauusd-forward-dashboard .shadow-legend{display:flex;gap:16px;flex-wrap:wrap;color:#b7c9df;font-size:12px}
#xauusd-forward-dashboard .shadow-legend b{color:#e8f2ff}
#xauusd-forward-dashboard .shadow-note{font-size:12px;line-height:1.6;color:#9eb0c8;margin:14px 0 0}
#xauusd-forward-dashboard .shadow-status{padding:12px 14px;border:1px solid #455672;background:#1b2a40;border-radius:10px;margin:12px 0}
#xauusd-forward-dashboard .shadow-status[data-state="stale"]{border-color:#ad7940;color:#ffd29a}
#xauusd-forward-dashboard .shadow-status[data-state="error"]{border-color:#c46b77;color:#ffadb8}
#xauusd-forward-dashboard .shadow-status[data-state="fresh"]{border-color:#398e75;color:#9aebcb}
#xauusd-forward-dashboard .stats{grid-template-columns:repeat(4,minmax(0,1fr))}
@media(max-width:850px){#xauusd-forward-dashboard .stats{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:460px){#xauusd-forward-dashboard .stats{grid-template-columns:1fr 1fr}#xauusd-forward-dashboard .stat{padding:10px}#xauusd-forward-dashboard .stat strong{font-size:17px}}
</style>
<div class="shadow-head"><div><small>Výzkumné sledování · americká seance</small><h2 style="margin:5px 0">XAUUSD · Forward Shadow</h2></div><button type="button" id="shadow-refresh">↻ Obnovit data</button></div>
<div class="shadow-status" id="shadow-status" role="status" aria-live="polite">Načítám výsledky ze Supabase…</div>
<div class="shadow-meta"><span class="shadow-chip" id="shadow-activation">Aktivace: —</span><span class="shadow-chip" id="shadow-last-check">Poslední kontrola: —</span><span class="shadow-chip" id="shadow-window">Makro filtr: —</span><span class="shadow-chip" id="shadow-cost">Modelované náklady: —</span></div>
<div class="stats">
<div class="stat"><small>Dokončené simulace</small><strong id="shadow-total">—</strong></div>
<div class="stat"><small>Prošlo filtrem zpráv</small><strong id="shadow-kept">—</strong></div>
<div class="stat"><small>Blokováno zprávami</small><strong id="shadow-blocked">—</strong></div>
<div class="stat"><small>Čistý výsledek</small><strong id="shadow-net">—</strong></div>
<div class="stat"><small>Úspěšnost</small><strong id="shadow-win">—</strong></div>
<div class="stat"><small>Profit factor</small><strong id="shadow-pf">—</strong></div>
<div class="stat"><small>Maximální drawdown</small><strong id="shadow-dd">—</strong></div>
<div class="stat"><small>Průměrný výsledek</small><strong id="shadow-exp">—</strong></div>
</div>
<div style="margin-top:18px"><strong>Vliv filtru ekonomických zpráv</strong><div class="shadow-track" role="img" id="shadow-bar" aria-label="Poměr povolených a blokovaných simulací"><div class="shadow-allowed" id="shadow-allowed"></div><div class="shadow-blocked" id="shadow-rejected"></div></div><div class="shadow-legend"><span>🟢 Prošlo: <b id="shadow-kept-percent">—</b></span><span>🟠 Blokováno: <b id="shadow-blocked-percent">—</b></span></div></div>
<p class="shadow-note" id="shadow-explanation">Nejde o skutečné ani virtuálně exekuované obchody. Strategie zpětně vyhodnocuje pouze nové dokončené simulace po aktivaci sledování. Výsledky nezahrnují skutečný skluz, plnění pokynů ani všechny dopady filtru na následné vstupy.</p>`;
document.querySelector("main")?.prepend(root);
const $=id=>root.querySelector("#"+id);
const set=(id,value)=>{const el=$(id);if(el)el.textContent=value};
const fmt=(v,d=2)=>v===null||v===undefined||v===""||!Number.isFinite(Number(v))?"—":Number(v).toLocaleString("cs-CZ",{maximumFractionDigits:d,minimumFractionDigits:d});
const date=v=>{const t=Date.parse(v||"");return Number.isFinite(t)?new Date(t).toLocaleString("cs-CZ",{dateStyle:"medium",timeStyle:"short"}):"—"};
let last=null,busy=false;
function status(message,state){const el=$("shadow-status");el.textContent=message;el.dataset.state=state}
function show(data){
 last=data;
 const checked=Date.parse(data.last_check_utc||"");
 const age=Date.now()-checked;
 const valid=Number.isFinite(checked)&&age>=-300000;
 const stale=!valid||age>45*60000;
 status(stale?"⚠ Synchronizace není aktuální. Poslední kontrola: "+date(data.last_check_utc):"● Synchronizace aktivní · poslední kontrola "+date(data.last_check_utc),stale?"stale":"fresh");
 set("shadow-activation","Aktivace: "+date(data.activated_utc));
 set("shadow-last-check","Poslední kontrola: "+date(data.last_check_utc));
 set("shadow-window","Makro filtr: ±"+(data.window_minutes??"—")+" min");
 set("shadow-cost","Modelované náklady: "+fmt(data.cost_price_units)+" cenové jednotky");
 const total=Number(data.total_trades),kept=Number(data.kept_trades),blocked=Number(data.blocked_trades);
 const countsOk=[total,kept,blocked].every(Number.isSafeInteger)&&total>=0&&kept>=0&&blocked>=0&&kept+blocked===total;
 set("shadow-total",countsOk?String(total):"—");
 set("shadow-kept",countsOk?String(kept):"—");
 set("shadow-blocked",countsOk?String(blocked):"—");
 const hasTrades=countsOk&&kept>0;
 set("shadow-net",hasTrades?fmt(data.net_r)+" R":"—");
 set("shadow-win",hasTrades&&data.winrate_pct!=null?fmt(data.winrate_pct)+" %":"—");
 set("shadow-pf",hasTrades?fmt(data.profit_factor):"—");
 set("shadow-dd",hasTrades?fmt(data.max_drawdown_r)+" R":"—");
 set("shadow-exp",hasTrades?fmt(data.expectancy_r,3)+" R":"—");
 const passed=countsOk&&total?100*kept/total:0;
 const rejected=countsOk&&total?100*blocked/total:0;
 $("shadow-allowed").style.width=passed+"%";$("shadow-rejected").style.width=rejected+"%";
 $("shadow-bar").setAttribute("aria-label",countsOk&&total?"Prošlo "+fmt(passed,1)+" %, blokováno "+fmt(rejected,1)+" %":"Zatím bez dokončených simulací");
 set("shadow-kept-percent",countsOk&&total?fmt(passed,1)+" %":"—");
 set("shadow-blocked-percent",countsOk&&total?fmt(rejected,1)+" %":"—");
 set("shadow-explanation",!countsOk?"⚠ Nekonzistentní počty obchodů. Zkontroluj publikaci na VPS.":total===0?"Sledování je inicializované, ale zatím nebyl dokončen žádný nový simulovaný obchod. To samo o sobě neznamená chybu.":"Výsledky se týkají dokončených retrospektivně simulovaných obchodů od aktivace. Nejde o reálné plnění ani živý signál. Filtr neprovádí novou simulaci následných vstupů po vyřazeném obchodu.");
}
async function refresh(){
 if(busy)return;busy=true;$("shadow-refresh").disabled=true;
 try{
  const {data:auth,error:authError}=await db.auth.getUser();
  if(authError||!auth?.user){status("Pro zobrazení statistik je nutné přihlášení.","error");return}
  const {data,error}=await db.from("xauusd_shadow_summary").select("id,activated_utc,last_check_utc,window_minutes,cost_price_units,total_trades,kept_trades,blocked_trades,net_r,winrate_pct,profit_factor,max_drawdown_r,expectancy_r").eq("id","XAUUSD_USA").maybeSingle();
  if(error)throw error;
  if(!data){status("Zatím není dostupný záznam XAUUSD_USA. Zkontroluj publikování na VPS a oprávnění k tabulce.","error");return}
  show(data);
 }catch(e){status("Nelze načíst statistiky ze Supabase. Poslední známé hodnoty mohou být zastaralé. Zkontroluj přihlášení, oprávnění a síť.","error");}
 finally{busy=false;$("shadow-refresh").disabled=false}
}
$("shadow-refresh").addEventListener("click",refresh);
refresh();setInterval(()=>{if(!document.hidden)refresh();else if(last)show(last)},60000);
document.addEventListener("visibilitychange",()=>{if(!document.hidden)refresh()});
