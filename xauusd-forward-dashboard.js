import {createClient} from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.95.3/+esm";
const db=createClient("https://hatzdirgwutbdarpgwro.supabase.co","sb_publishable_FfWSpPjZSer3hnytJ1q9PA_yM6mEORu");
const root=document.createElement("section");root.className="card";root.id="xauusd-forward-dashboard";
root.innerHTML='<div class="row"><h2>XAUUSD · Forward Shadow</h2><span class="pill">Výzkum · bez obchodování</span></div><p class="note" id="shadow-status">Načítám ověřené statistiky…</p><div class="stats"><div class="stat"><small>Dokončené simulace</small><strong id="shadow-total">—</strong></div><div class="stat"><small>Prošlo filtrem ±60 min</small><strong id="shadow-kept">—</strong></div><div class="stat"><small>Blokováno zprávami</small><strong id="shadow-blocked">—</strong></div><div class="stat"><small>Čistý výsledek</small><strong id="shadow-net">—</strong></div><div class="stat"><small>Úspěšnost</small><strong id="shadow-win">—</strong></div><div class="stat"><small>Profit factor</small><strong id="shadow-pf">—</strong></div><div class="stat"><small>Max. drawdown</small><strong id="shadow-dd">—</strong></div><div class="stat"><small>Průměrné R</small><strong id="shadow-exp">—</strong></div></div><p class="note">Zpětné vyhodnocení nových simulovaných obchodů; nejde o živé virtuální exekuce ani investiční doporučení. Náklady jsou modelované.</p>';
document.querySelector("main")?.prepend(root);
const set=(id,value)=>{const el=document.getElementById(id);if(el)el.textContent=value};
const num=(v,d=2)=>v===null||v===undefined?"—":Number(v).toLocaleString("cs-CZ",{maximumFractionDigits:d,minimumFractionDigits:d});
async function refresh(){
 try{
  const {data:{user},error:authError}=await db.auth.getUser();
  if(authError||!user){set("shadow-status","Přihlas se pro zobrazení statistik.");return}
  const {data,error}=await db.from("xauusd_shadow_summary").select("*").eq("id","XAUUSD_USA").maybeSingle();
  if(error)throw error;
  if(!data){set("shadow-status","Čekám na první synchronizaci z VPS.");return}
  const checked=data.last_check_utc?new Date(data.last_check_utc):null;
  const stale=!checked||Date.now()-checked.getTime()>45*60*1000;
  set("shadow-status",(stale?"⚠ Data nejsou aktuální · ":"Aktualizováno · ")+(checked?checked.toLocaleString("cs-CZ"):"bez záznamu"));
  set("shadow-total",String(data.total_trades));set("shadow-kept",String(data.kept_trades));set("shadow-blocked",String(data.blocked_trades));
  set("shadow-net",num(data.net_r)+" R");set("shadow-win",data.winrate_pct===null?"—":num(data.winrate_pct)+" %");
  set("shadow-pf",num(data.profit_factor));set("shadow-dd",num(data.max_drawdown_r)+" R");set("shadow-exp",num(data.expectancy_r,3)+" R");
 }catch(e){set("shadow-status","Statistiky se nepodařilo načíst. Zkontroluj přihlášení a synchronizaci.");}
}
refresh();setInterval(refresh,60000);
