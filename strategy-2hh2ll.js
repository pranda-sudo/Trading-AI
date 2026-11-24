// 2HH2LL research detector. Zones must be supplied before the setup begins.
const validBar=b=>b&&['high','low'].every(k=>Number.isFinite(+b[k]))&&+b.high>=+b.low;
export function detect2HH2LL(first,second,third,zone,side){
 if(!validBar(first)||!validBar(second)||!validBar(third)||!zone||!Number.isFinite(zone.low)||!Number.isFinite(zone.high)||zone.low>zone.high||!['LONG','SHORT'].includes(side))return null;
 const long=side==='LONG';
 const structure=long?+second.high<+first.high&&+second.low<+first.low:+second.high>+first.high&&+second.low>+first.low;
 if(!structure)return null;
 const touch=[first,second,third].some(b=>+b.low<=zone.high&&+b.high>=zone.low);
 const trigger=long?+second.high:+second.low;
 const hit=long?+third.high>=trigger:+third.low<=trigger;
 if(!touch)return {side,state:'WATCH',trigger,zone};
 return {side,state:hit?'TRIGGER':'READY',trigger,zone};
}
// Historical support/resistance zones, derived only from bars before the setup.
// Research defaults: two confirmed pivots, four bars on each side, ATR tolerance.
export function priorZones(rows,reference){
 if(rows.length<65||!Number.isFinite(reference)||reference<=0)return [];
 const a=rows.slice(-240);if(!a.every(validBar))return [];
 const tr=a.slice(-15).slice(1).map((b,i)=>Math.max(+b.high-+b.low,Math.abs(+b.high-+a[a.length-15+i].close),Math.abs(+b.low-+a[a.length-15+i].close)));
 const atr=tr.reduce((s,v)=>s+v,0)/tr.length;
 const width=Math.max(atr*.3,reference*.00012);
 if(!Number.isFinite(width)||width<=0)return [];
 const clusters=[];
 for(let i=4;i<a.length-4;i++)for(const side of ['LONG','SHORT']){
  const low=side==='LONG',p=+(low?a[i].low:a[i].high);
  if(![1,2,3,4].every(d=>low?p<+a[i-d].low&&p<=+a[i+d].low:p>+a[i-d].high&&p>=+a[i+d].high))continue;
  const c=clusters.find(x=>x.side===side&&Math.abs(x.center-p)<=width);
  if(c){c.center=(c.center*c.count+p)/(c.count+1);c.count++;}else clusters.push({side,center:p,count:1});
 }
 return ['LONG','SHORT'].flatMap(side=>clusters.filter(c=>c.side===side&&c.count>=2&&(side==='LONG'?c.center<reference:c.center>reference)).sort((a,b)=>Math.abs(a.center-reference)-Math.abs(b.center-reference)).slice(0,1).map(c=>({...c,low:c.center-width,high:c.center+width})));
}
