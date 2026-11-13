// Historické signály pouze z již uzavřených svíček. Bez použití budoucích cen při rozhodnutí.
// Výsledky jsou hypotetické: bez spreadu, skluzu a poplatků; nejedná se o backtest exekuce.
export function historicalSignals(rows,{maxSignals=8}={}){
 const a=rows.map(r=>({time:r.candle_time,open:+r.open,high:+r.high,low:+r.low,close:+r.close})),n=a.length;
 if(n<65)return [];
 const ema=(len)=>{let e=a[0].close;return a.map(x=>(e=x.close*2/(len+1)+e*(1-2/(len+1))))};
 const fast=ema(20),slow=ema(50),tr=a.map((x,i)=>i?Math.max(x.high-x.low,Math.abs(x.high-a[i-1].close),Math.abs(x.low-a[i-1].close)):x.high-x.low);
 const atr=tr.map((_,i)=>i>=13?tr.slice(i-13,i+1).reduce((v,z)=>v+z,0)/14:null);
 const found=[];let lastIndex=-30;
 for(let i=54;i<n-2;i++){
  if(i-lastIndex<12)continue;
  const c=a[i],p=a[i-1],vol=atr[i];if(!Number.isFinite(vol)||vol<=0)continue;
  const bullish=fast[i]>slow[i]&&fast[i]>fast[i-3]&&c.close>fast[i]&&p.close<=fast[i-1]&&c.close>c.open;
  const bearish=fast[i]<slow[i]&&fast[i]<fast[i-3]&&c.close<fast[i]&&p.close>=fast[i-1]&&c.close<c.open;
  if(!bullish&&!bearish)continue;
  const side=bullish?'LONG':'SHORT',entry=a[i+1].open;
  const stop=bullish?Math.min(...a.slice(i-4,i+1).map(x=>x.low))-vol*.2:Math.max(...a.slice(i-4,i+1).map(x=>x.high))+vol*.2;
  const risk=Math.abs(entry-stop);if(risk<vol*.3||risk>vol*3||!((bullish&&stop<entry)||(bearish&&stop>entry)))continue;
  const target=entry+(bullish?1:-1)*risk*2;
  let result='NEUZAVŘENO',exitIndex=null;
  for(let j=i+1;j<Math.min(n,i+51);j++){
   const x=a[j],hitSL=bullish?x.low<=stop:x.high>=stop,hitTP=bullish?x.high>=target:x.low<=target;
   if(hitSL||hitTP){result=hitSL?'SL':'TP';exitIndex=j;break} // Při zásahu obou úrovní v jedné svíčce konzervativně SL.
  }
  found.push({index:i+1,signalIndex:i,side,entry,stop,target,result,exitIndex,time:a[i+1].time});
  lastIndex=i;
 }
 return found.slice(-maxSignals);
}
export function paintSignals(ctx,rows,signals,{x,y,plotRight,plotTop,plotBottom,step}){
 ctx.save();ctx.font='bold 11px system-ui,sans-serif';
 for(const s of signals){
  const xx=x(s.index),yy=y(s.entry),isLong=s.side==='LONG',color=isLong?'#5de0b4':'#ff8895';
  const direction=isLong?-1:1,apex=yy+direction*10;
  ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(xx,apex);ctx.lineTo(xx-6,apex+direction* -11);ctx.lineTo(xx+6,apex+direction* -11);ctx.closePath();ctx.fill();
  const right=Math.min(plotRight,xx+Math.max(30,Math.min(75,step*22)));
  for(const [price,label,lineColor] of [[s.entry,'VSTUP','#8bb9ff'],[s.stop,'SL','#ff7d8a'],[s.target,'TP','#65dcb2']]){
   const py=y(price);if(py<plotTop||py>plotBottom)continue;
   ctx.strokeStyle=lineColor;ctx.setLineDash([3,3]);ctx.lineWidth=1.2;ctx.beginPath();ctx.moveTo(xx,py);ctx.lineTo(right,py);ctx.stroke();ctx.setLineDash([]);
   if(right-xx>38){ctx.fillStyle=lineColor;ctx.textAlign='left';ctx.fillText(label+' '+price.toFixed(2),right+3,py-3)}
  }
 }
 ctx.restore();
}
