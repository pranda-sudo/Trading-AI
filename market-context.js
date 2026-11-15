// Trading AI – tržní kontext. Orientační seance, nikoli brokerem potvrzené hodiny.
// Makroekonomické události se čtou ze synchronizované tabulky economic_events.
(()=>{'use strict';
const CSS=`#market-context{margin-bottom:18px}#market-context .mc-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}#market-context .mc-tile{background:#202f46;border-radius:12px;padding:16px}#market-context .mc-title{font-size:13px;color:#9fb1c9;margin-bottom:9px}#market-context .mc-value{font-size:19px;font-weight:700}#market-context .mc-note{font-size:12px;color:#b3c3d7;line-height:1.5;margin-top:10px}#market-context a{color:#8dc0ff}#market-context .mc-alert{color:#ffcd79}#market-context .mc-good{color:#6cdbb0}@media(max-width:850px){#market-context .mc-grid{grid-template-columns:1fr}}`;
const style=document.createElement('style');style.textContent=CSS;document.head.append(style);
const panel=document.createElement('section');panel.className='card';panel.id='market-context';panel.innerHTML=`<h2>Tržní kontext · seance, zprávy a geopolitika</h2><div class="mc-grid"><div class="mc-tile"><div class="mc-title">Obchodní seance (orientačně)</div><div id="mc-session" class="mc-value">Načítám…</div><div id="mc-clock" class="mc-note"></div></div><div class="mc-tile"><div class="mc-title">Makroekonomický kalendář</div><div class="mc-value mc-good" style="font-size:17px">Propojeno s kalendářem MT5 (RoboForex)</div><div id="mc-macro" class="mc-note" role="status">Načítám dvě nejbližší zprávy…</div><div class="mc-note"><a href="./economic-calendar.html">Všechny ekonomické zprávy a události →</a><div style="font-size:11px;margin-top:6px;color:#9fb1c9">* DE40: nepřímý vliv významných zpráv z USA. Časy dle zařízení.</div></div></div><div class="mc-tile"><div class="mc-title">Geopolitická rizika</div><div class="mc-value mc-alert">Automatický feed zatím nepřipojen</div><div class="mc-note">Zprávy o konfliktech, clech a sankcích je nutné ověřit z důvěryhodných zdrojů. <a href="https://www.reuters.com/world/" target="_blank" rel="noopener noreferrer">Reuters World</a></div></div></div><p class="mc-note" id="mc-guidance">Časy seancí jsou orientační. Skutečné obchodní hodiny a případné přestávky se řídí specifikací symbolu v RoboForex MT5. Bez ověřeného kalendáře a zpravodajského feedu aplikace nemůže potvrdit, že nehrozí zásadní zpráva.</p>`;
const main=document.querySelector('main');if(!main)return;const quote=document.querySelector('#live-quote-panel');if(quote)quote.insertAdjacentElement('afterend',panel);else main.prepend(panel);
const timeFmt=(zone)=>new Intl.DateTimeFormat('cs-CZ',{timeZone:zone,hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date());
const minutes=(zone)=>{const [h,m]=timeFmt(zone).split(':').map(Number);return h*60+m};
const inWindow=(m,a,b)=>m>=a&&m<b;
function refresh(){const now=new Date(),day=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',weekday:'short'}).format(now),weekday=!['Sat','Sun'].includes(day),ld=minutes('Europe/London'),ny=minutes('America/New_York'),tk=minutes('Asia/Tokyo');const active=[];if(weekday&&inWindow(tk,9*60,15*60))active.push('Tokio');if(weekday&&inWindow(ld,8*60,17*60))active.push('Londýn');if(weekday&&inWindow(ny,9*60+30,16*60))active.push('Wall Street (akcie)');document.getElementById('mc-session').textContent=active.length?active.join(' + '):'Mimo hlavní seance';document.getElementById('mc-clock').textContent='Praha '+timeFmt('Europe/Prague')+' · Londýn '+timeFmt('Europe/London')+' · New York '+timeFmt('America/New_York')+' · Tokio '+timeFmt('Asia/Tokyo');}
refresh();setInterval(refresh,30000);
// Český překlad běžných názvů MT5. Neznámé názvy ponecháváme v originále.
const macroTerms=[
 [/\\bFed Vice Chair for Supervision\\b/gi,'Viceguvernér Fedu pro bankovní dohled'],
 [/\\bExecutive Board Member\\b/gi,'Člen výkonné rady'],
 [/\\bMauderer Speech\\b/gi,'Projev Maudererové'],
 [/\\bBarr Speech\\b/gi,'Projev Barra'],
 [/\\bSpeech\\b/gi,'– projev'],
 [/\\bNonfarm Payrolls\\b/gi,'Změna zaměstnanosti mimo zemědělství (NFP)'],
 [/\\bUnemployment Rate\\b/gi,'Míra nezaměstnanosti'],
 [/\\bConsumer Price Index\\b/gi,'Index spotřebitelských cen (CPI)'],
 [/\\bCore CPI\\b/gi,'Jádrová inflace CPI'],
 [/\\bProducer Price Index\\b/gi,'Index cen výrobců (PPI)'],
 [/\\bInterest Rate Decision\\b/gi,'Rozhodnutí o úrokových sazbách'],
 [/\\bFOMC Meeting Minutes\\b/gi,'Zápis ze zasedání Fedu'],
 [/\\bFOMC Statement\\b/gi,'Prohlášení Fedu'],
 [/\\bECB Press Conference\\b/gi,'Tisková konference ECB'],
 [/\\bGDP\\b/g,'HDP'],
 [/\\bRetail Sales\\b/gi,'Maloobchodní tržby'],
 [/\\bManufacturing PMI\\b/gi,'Index aktivity ve výrobě (PMI)'],
 [/\\bServices PMI\\b/gi,'Index aktivity ve službách (PMI)'],
 [/\\bGerman\\b/gi,'Německo:'],
 [/\\bEurozone\\b/gi,'Eurozóna:'],
 [/\\bPreliminary\\b/gi,'Předběžný'],
 [/\\bFinal\\b/gi,'Konečný'],
 [/\\bMoM\\b/gi,'meziměsíčně'],
 [/\\bYoY\\b/gi,'meziročně']
];
function macroCzech(title){let result=String(title||'');for(const [pattern,replacement] of macroTerms)result=result.replace(pattern,replacement);return result;}
function macroInstruments(e){
 const c=String(e.currency||'').toUpperCase();
 if(c==='EUR')return ['DE40'];
 if(c==='USD')return ['XAUUSD','US30','USTECH','US500','DE40*'];
 return [];
}
function macroCountdown(time){
 const ms=Date.parse(time)-Date.now();if(!Number.isFinite(ms))return 'Čas neznámý';
 if(ms<=0)return 'Právě probíhá / zveřejněno';
 const mins=Math.ceil(ms/60000),days=Math.floor(mins/1440),hours=Math.floor(mins%1440/60),minutes=mins%60;
 return 'Za '+(days?days+' d ':'')+(hours?hours+' h ':'')+minutes+' min';
}
function refreshMacroCountdowns(){
 document.querySelectorAll('#mc-macro [data-macro-time]').forEach(el=>{el.textContent=macroCountdown(el.dataset.macroTime)});
}
async function refreshMacro(){
 const target=document.getElementById('mc-macro');if(!target)return;
 try{
  const {createClient}=await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.95.3/+esm');
  const db=createClient('https://hatzdirgwutbdarpgwro.supabase.co','sb_publishable_FfWSpPjZSer3hnytJ1q9PA_yM6mEORu');
  const now=new Date(),until=new Date(now.getTime()+30*86400000);
  const {data,error}=await db.from('economic_events').select('event_time,title,currency,importance').gte('event_time',now.toISOString()).lte('event_time',until.toISOString()).in('currency',['USD','EUR']).gte('importance',2).order('event_time',{ascending:true}).limit(2);
  if(error)throw error;
  target.replaceChildren();
  if(!data?.length){target.textContent='V následujících 30 dnech nejsou načteny důležité události USD/EUR. Zkontroluj úplnost synchronizace.';return}
  for(const e of data){
   const item=document.createElement('div');item.style.cssText='padding:9px 0;border-bottom:1px solid #35465f';
   const top=document.createElement('div');top.style.cssText='font-weight:700;color:#e8f0ff;font-size:14px';
   top.textContent=new Date(e.event_time).toLocaleString('cs-CZ',{day:'numeric',month:'numeric',hour:'2-digit',minute:'2-digit'})+' · '+e.currency+' · '+(Number(e.importance)>=3?'🔴 Vysoká':'🟠 Střední');
   const name=document.createElement('div');name.style.cssText='font-size:13px;line-height:1.4;margin-top:4px;color:#b8cbe5';name.textContent=macroCzech(e.title);
   const affected=document.createElement('div');affected.style.cssText='font-size:12px;color:#8dc0ff;margin-top:5px';affected.textContent='Trhy: '+macroInstruments(e).join(' · ');
   const countdown=document.createElement('div');countdown.style.cssText='font-size:12px;color:#ffd38c;margin-top:5px';countdown.dataset.macroTime=e.event_time;countdown.textContent=macroCountdown(e.event_time);
   item.append(top,name,affected,countdown);target.append(item);
  }
 }catch(error){target.textContent='Aktuální zprávy se nepodařilo načíst: '+error.message}
}
refreshMacro();setInterval(refreshMacro,300000);setInterval(refreshMacroCountdowns,30000);
})();