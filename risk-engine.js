// Trading AI research risk policy v1. No order execution.
export const POLICY=Object.freeze({riskPct:.25,dailyPct:1,weeklyPct:3,minRR:2,maxTrades:4,maxConcurrent:1,maxConsecutiveLosses:2,newsMinutes:60,maxQuoteAgeMs:45000});
const finite=x=>typeof x==='number'&&Number.isFinite(x);
export function assessRisk(x){
 const reasons=[];
 const fail=m=>reasons.push(m);
 const {equity,dayStartEquity,weekStartEquity,dayPnl,weekPnl,tradesToday,openTrades,consecutiveLosses,entry,stop,target,tickSize,tickValue,volumeMin,volumeStep,volumeMax,roundTripCostPerLot,slippagePrice,spread,maxSpread,side}=x;
 const positive=v=>finite(v)&&v>0;
 const nonnegative=v=>finite(v)&&v>=0;
 const count=v=>Number.isInteger(v)&&v>=0;
 if(!positive(equity)||!positive(dayStartEquity)||!positive(weekStartEquity)||!finite(dayPnl)||!finite(weekPnl)||!count(tradesToday)||!count(openTrades)||!count(consecutiveLosses)||x.ledgerVerified!==true)fail('Neověřený stav virtuálního účtu');
 if(x.quoteFresh!==true)fail('Neaktuální kotace');
 if(x.calendarClear!==true)fail('Makro filtr nepotvrzen');
 if(x.trendConfirmed!==true)fail('Trend nepotvrzen');
 if(x.volumeConfirmed!==true)fail('Volume nepotvrzen');
 if(x.patternConfirmed!==true)fail('Pattern nepotvrzen');
 if(x.zoneConfirmed!==true)fail('Zóna nepotvrzena');
 if(x.sessionAllowed!==true)fail('Obchodní seance nebo uzavření před nocí nepotvrzeno');
 if(!nonnegative(spread)||!positive(maxSpread)||spread>maxSpread)fail('Spread neověřen nebo nad limitem');
 if(tradesToday>=POLICY.maxTrades)fail('Denní počet obchodů vyčerpán');
 if(openTrades>=POLICY.maxConcurrent)fail('Již otevřený obchod');
 if(consecutiveLosses>=POLICY.maxConsecutiveLosses)fail('Dvě ztráty za sebou');
 const direction=side==='LONG'?1:side==='SHORT'?-1:0;
 if(!direction||![entry,stop,target].every(positive)||direction*(entry-stop)<=0||direction*(target-entry)<=0)fail('Neplatné SL / TP');
 if(![tickSize,tickValue,volumeMin,volumeStep,volumeMax].every(positive)||volumeMax<volumeMin||!nonnegative(roundTripCostPerLot)||!nonnegative(slippagePrice))fail('Neověřené parametry kontraktu nebo náklady');
 let plannedLoss=null,netRR=null,lots=null,budget=null;
 if([equity,dayStartEquity,weekStartEquity].every(positive)&&finite(dayPnl)&&finite(weekPnl)){
  budget=Math.min(equity*POLICY.riskPct/100,dayStartEquity*POLICY.dailyPct/100+Math.min(dayPnl,0),weekStartEquity*POLICY.weeklyPct/100+Math.min(weekPnl,0));
  if(budget<=0)fail('Limit ztráty vyčerpán');
 }
 if(direction&&[entry,stop,target,tickSize,tickValue,volumeMin,volumeStep,volumeMax].every(positive)&&direction*(entry-stop)>0&&direction*(target-entry)>0&&nonnegative(roundTripCostPerLot)&&nonnegative(slippagePrice)&&budget>0){
  // entry and exits must be executable-side prices; do not add spread twice.
  const loss=(Math.abs(entry-stop)+slippagePrice)/tickSize*tickValue+roundTripCostPerLot;
  const gain=(Math.abs(target-entry)-slippagePrice)/tickSize*tickValue-roundTripCostPerLot;
  netRR=gain/loss;
  if(netRR<POLICY.minRR)fail('Čisté R:R pod 1:2');
  const cap=Math.min(volumeMax,budget/loss);
  lots=cap<volumeMin?0:Number((volumeMin+Math.floor((cap-volumeMin)/volumeStep+1e-9)*volumeStep).toPrecision(12));
  if(lots*loss>budget+1e-8){lots=Math.max(0,lots-volumeStep);}
  if(lots<volumeMin){lots=0;fail('Minimální lot překračuje riziko');}
  plannedLoss=lots*loss;
 }
 return {decision:reasons.length?'WAIT':'PAPER_ELIGIBLE',reasons,budget,lots,plannedLoss,netRR};
}
