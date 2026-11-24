// Live clock validation. Never modifies raw MT5 candle keys.
// Only a short recent interval may use the inferred offset; no historical DST claims.
const MIN=60000;
export function inferClock(rows,now=Date.now()){
 const a=rows.slice(-3);
 if(a.length<3)return null;
 const raw=a.map(r=>Date.parse(r.candle_time)),received=a.map(r=>Date.parse(r.received_at));
 if(raw.some(t=>!Number.isFinite(t))||received.some(t=>!Number.isFinite(t)))return null;
 if(raw[1]-raw[0]!==MIN||raw[2]-raw[1]!==MIN)return null;
 if(now-received[2]<-10000||now-received[2]>2*MIN)return null;
 const candidates=[0,120,180].filter(offset=>raw.every((t,i)=>{
   const close=t-offset*MIN+MIN,lag=received[i]-close;
   return lag>=-2000&&lag<=4*MIN;
 })&&now-(raw[2]-offset*MIN+MIN)>=-2000&&now-(raw[2]-offset*MIN+MIN)<=3*MIN);
 return candidates.length===1?{offset:candidates[0],anchor:raw[2],checkedAt:now}:null;
}
export function candleUtc(value,clock,now=Date.now()){
 const t=Date.parse(value);
 if(!clock||now-clock.checkedAt>2*MIN||now-clock.checkedAt<-10000||!Number.isFinite(t)||t>clock.anchor||t<clock.anchor-4*60*MIN)return NaN;
 return t-clock.offset*MIN;
}
export function quoteIsFresh(q,now=Date.now(),maxAge=45000){
 const t=Date.parse(q?.quote_time),r=Date.parse(q?.received_at);
 return Number.isFinite(t)&&Number.isFinite(r)&&now-t>=0&&now-t<=maxAge&&now-r>=0&&now-r<=60000&&r-t>=-2000&&Number(q.bid)>0&&Number(q.ask)>=Number(q.bid);
}
