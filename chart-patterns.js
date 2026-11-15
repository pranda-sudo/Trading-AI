// Experimental, non-trading chart pattern recognizer. Uses confirmed pivots only.
const TYPES={
 double_top:['Dvojitý vrchol','#fb7185'],double_bottom:['Dvojité dno','#34d399'],
 head_shoulders:['Hlava a ramena','#fb7185'],inverse_head_shoulders:['Obrácená H&R','#34d399'],
 ascending_triangle:['Rostoucí trojúhelník','#fbbf24'],descending_triangle:['Klesající trojúhelník','#fbbf24'],
 symmetric_triangle:['Symetrický trojúhelník','#c4b5fd'],rising_wedge:['Rostoucí klín','#fb923c'],
 falling_wedge:['Klesající klín','#38bdf8'],channel:['Cenový kanál','#60a5fa']
};
const avg=a=>a.reduce((s,x)=>s+x,0)/Math.max(1,a.length);
function pivots(bars,r=3){
 const out=[];for(let i=r;i<bars.length-r;i++){
  const v=bars[i],window=bars.slice(i-r,i+r+1);
  if(window.every((b,j)=>j===r||Number(v.high)>Number(b.high)))out.push({i,p:Number(v.high),side:'H'});
  if(window.every((b,j)=>j===r||Number(v.low)<Number(b.low)))out.push({i,p:Number(v.low),side:'L'});
 }return out.sort((a,b)=>a.i-b.i);
}
function regression(points){const mx=avg(points.map(p=>p.i)),my=avg(points.map(p=>p.p));const den=points.reduce((s,p)=>s+(p.i-mx)**2,0);const slope=den?points.reduce((s,p)=>s+(p.i-mx)*(p.p-my),0)/den:0;return {slope,at:i=>my+slope*(i-mx)}}
function scanPatterns(bars){
 if(bars.length<45)return [];
 const found=[],P=pivots(bars),hi=P.filter(p=>p.side==='H'),lo=P.filter(p=>p.side==='L');
 const recent=P.slice(-24),last=bars.length-1,price=Number(bars[last].close),tol=price*.006;
 const add=(type,points,score)=>{if(!points.length)return;const from=Math.min(...points.map(p=>p.i)),to=Math.max(...points.map(p=>p.i));if(last-to>70)return;found.push({type,points,from,to,score,color:TYPES[type][1],label:TYPES[type][0],status:'Kandidát – nepotvrzeno'})};
 for(let j=1;j<recent.length-1;j++){
  const a=recent[j-1],b=recent[j],c=recent[j+1];if(c.i-a.i<6||c.i-a.i>75)continue;
  if(a.side==='H'&&b.side==='L'&&c.side==='H'&&Math.abs(a.p-c.p)<=Math.max(tol,(a.p-b.p)*.22)&&Math.min(a.p,c.p)-b.p>tol*1.2)add('double_top',[a,b,c],.75);
  if(a.side==='L'&&b.side==='H'&&c.side==='L'&&Math.abs(a.p-c.p)<=Math.max(tol,(b.p-a.p)*.22)&&b.p-Math.max(a.p,c.p)>tol*1.2)add('double_bottom',[a,b,c],.75);
 }
 for(let j=0;j<recent.length-4;j++){
  const p=recent.slice(j,j+5),s=p.map(x=>x.side).join('');
  if(s==='HLHLH'&&p[2].p>Math.max(p[0].p,p[4].p)+tol&&Math.abs(p[0].p-p[4].p)<Math.max(tol,(p[2].p-p[1].p)*.4))add('head_shoulders',p,.8);
  if(s==='LHLHL'&&p[2].p<Math.min(p[0].p,p[4].p)-tol&&Math.abs(p[0].p-p[4].p)<Math.max(tol,(p[1].p-p[2].p)*.4))add('inverse_head_shoulders',p,.8);
 }
 // Bound regression to recent confirmed pivot highs/lows and classify slope and convergence.
 for(const span of [40,65]){
  const highs=hi.filter(p=>p.i>=last-span),lows=lo.filter(p=>p.i>=last-span);
  if(highs.length<3||lows.length<3)continue;
  const rh=regression(highs),rl=regression(lows),scale=price*.001;
  const sh=rh.slope,sl=rl.slope,flat=x=>Math.abs(x)<scale*.35;
  const upperNow=rh.at(last),lowerNow=rl.at(last),upperBefore=rh.at(last-span),lowerBefore=rl.at(last-span);
  if(upperNow<=lowerNow||upperBefore<=lowerBefore)continue;
  const narrowing=(upperNow-lowerNow)<(upperBefore-lowerBefore)*.8;
  const parallel=Math.abs(sh-sl)<scale*.45;
  let type=null;
  if(narrowing&&flat(sh)&&sl>scale*.45)type='ascending_triangle';
  else if(narrowing&&flat(sl)&&sh<-scale*.45)type='descending_triangle';
  else if(narrowing&&sh<-scale*.35&&sl>scale*.35)type='symmetric_triangle';
  else if(narrowing&&sh>scale*.35&&sl>scale*.35&&sl>sh)type='rising_wedge';
  else if(narrowing&&sh<-scale*.35&&sl<-scale*.35&&sh<sl)type='falling_wedge';
  else if(parallel&&Math.abs(sh)>scale*.3)type='channel';
  if(type)add(type,[...highs,...lows],.6);
 }
 // One best recent match per pattern, avoid covering the chart with labels.
 const best=new Map();for(const p of found){const old=best.get(p.type);if(!old||p.to>old.to||p.to===old.to&&p.score>old.score)best.set(p.type,p)}
 return [...best.values()].sort((a,b)=>b.to-a.to).slice(0,5);
}
export {scanPatterns,TYPES};
