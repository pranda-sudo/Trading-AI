// Economic risk mapping for the five tracked instruments. No trade execution.
export const TRACKED_SYMBOLS=['XAUUSD','US30','DE40','USTECH','US500'];
export function relevantEconomicEvent(symbol,e){
 const currency=String(e.currency||'').toUpperCase(),country=String(e.country||'').toLowerCase(),title=String(e.title||'').toLowerCase();
 const german=/germany|german|deutschland|deutsch/.test(country+' '+title);
 if(symbol==='DE40')return currency==='EUR'||german||(currency==='USD'&&Number(e.importance)>=3);
 return currency==='USD';
}
export function economicRisk(symbol,events,now=new Date()){
 const timestamp=now.getTime();
 const relevant=(events||[]).filter(e=>relevantEconomicEvent(symbol,e)&&Number(e.importance)>=2&&Number.isFinite(Date.parse(e.event_time)));
 const enriched=relevant.map(e=>({...e,minutes:(Date.parse(e.event_time)-timestamp)/60000}));
 const high=enriched.filter(e=>Number(e.importance)>=3);
 // Conservative advisory windows: 30 min before to 30 min after high-impact events.
 const active=high.filter(e=>e.minutes>=-30&&e.minutes<=30).sort((a,b)=>Math.abs(a.minutes)-Math.abs(b.minutes));
 const upcoming=high.filter(e=>e.minutes>30&&e.minutes<=1440).sort((a,b)=>a.minutes-b.minutes);
 const medium=enriched.filter(e=>Number(e.importance)===2&&e.minutes>=-15&&e.minutes<=15);
 return {status:active.length?'high':medium.length?'medium':upcoming.length?'upcoming':'clear',active,upcoming,medium,
  relevant:enriched.sort((a,b)=>Math.abs(a.minutes)-Math.abs(b.minutes)).slice(0,5)};
}
