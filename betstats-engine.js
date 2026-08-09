/* BetStats 3.0 — selection, value, calibration & radar engine
 * Dependency-free. Estimates are not guarantees. Never use confidence as a guarantee.
 */
(function(){
'use strict';

const VERSION='3.0-ensemble-calibratable';
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const n=(x,d=0)=>{const v=Number(x);return Number.isFinite(v)?v:d};
const pct=x=>Math.round(clamp(x)*100);
const avg=a=>a.length?a.reduce((s,x)=>s+x,0)/a.length:null;
const finite=a=>a.filter(Number.isFinite);

function weighted(values,weights){
  let s=0,w=0; values.forEach((v,i)=>{if(Number.isFinite(v)){const q=weights[i]??1;s+=v*q;w+=q;}});
  return w?s/w:null;
}
function formScore(form){
  if(!Array.isArray(form)||!form.length)return .5;
  const p={W:1,D:.5,L:0};
  let s=0,w=0;
  form.slice(-5).forEach((r,i)=>{const q=i+1;s+=(p[String(r).toUpperCase()]??.5)*q;w+=q;});
  return w?s/w:.5;
}
function formFactor(form){return 0.92+formScore(form)*0.16;} // .92..1.08
function sampleFactor(stats){return clamp(n(stats?.total_matches)/15,0,1);}
function poisson(k,l){
  if(l<=0)return k===0?1:0;
  let p=Math.exp(-l); for(let i=1;i<=k;i++)p*=l/i; return p;
}
function distribution(lh,la,max=10){
  const h=Array.from({length:max+1},(_,k)=>poisson(k,lh));
  const a=Array.from({length:max+1},(_,k)=>poisson(k,la));
  return {h,a};
}
function probabilities(lh,la){
  const d=distribution(lh,la,10);
  let home=0,draw=0,away=0,btts=0,o15=0,o25=0,o35=0;
  for(let i=0;i<=10;i++)for(let j=0;j<=10;j++){
    const p=d.h[i]*d.a[j];
    if(i>j)home+=p; else if(i===j)draw+=p; else away+=p;
    if(i>0&&j>0)btts+=p;
    if(i+j>=2)o15+=p;
    if(i+j>=3)o25+=p;
    if(i+j>=4)o35+=p;
  }
  return {home,draw,away,btts,o15,o25,o35};
}
function overProb(l,line){
  let under=0;const need=Math.floor(line)+1;
  for(let k=0;k<need;k++)under+=poisson(k,l);
  return clamp(1-under);
}
function bttsProb(lh,la){return clamp(1-Math.exp(-lh)-Math.exp(-la)+Math.exp(-(lh+la)));}

function estimateLambdas(m){
  const h=m.home_stats||{},a=m.away_stats||{};
  const hs=n(h.avg_goals_scored),hc=n(h.avg_goals_conceded),as=n(a.avg_goals_scored),ac=n(a.avg_goals_conceded);
  const hx=n(h.avg_xg),ax=n(a.avg_xg);
  // Attack-vs-opponent-defense. xG gets a strong but bounded weight.
  let lh=weighted([hs,ac,hx],[.32,.28,.40])??1.25;
  let la=weighted([as,hc,ax],[.32,.28,.40])??1.05;
  if(!hx)lh=weighted([hs,ac],[.52,.48])??1.25;
  if(!ax)la=weighted([as,hc],[.52,.48])??1.05;
  lh*=formFactor(h.form); la*=formFactor(a.form);
  // Soft home advantage, not enough to overpower team data.
  lh*=1.055; la*=.955;
  // Shots on target are a weak secondary quality signal.
  const hsot=n(h.avg_shots_on_target),asot=n(a.avg_shots_on_target);
  if(hsot>0)lh*=clamp(1+(hsot-4)*.012,.94,1.06);
  if(asot>0)la*=clamp(1+(asot-4)*.012,.94,1.06);
  return {home:clamp(lh,.15,4.5),away:clamp(la,.15,4.0)};
}
function empirical(m,key,fallback){
  const h=n(m.home_stats?.[key],NaN),a=n(m.away_stats?.[key],NaN);
  const vals=finite([h,a]).filter(v=>v>=0&&v<=100).map(v=>v/100);
  return vals.length?avg(vals):fallback;
}
function shotSignal(m,key,base){
  const h=m.home_stats||{},a=m.away_stats||{};
  const hs=n(h.avg_shots_on_target),as=n(a.avg_shots_on_target);
  if(hs<=0||as<=0)return base;
  const sot=hs+as;
  // Weak monotonic prior; deliberately capped.
  if(key==='o25')return clamp(.35+(sot-6)*.035,.25,.72);
  if(key==='o15')return clamp(.60+(sot-6)*.025,.48,.88);
  if(key==='btts')return clamp(.45+(Math.min(hs,as)-2.5)*.08,.30,.78);
  return base;
}
function dataQuality(m){
  const h=m.home_stats||{},a=m.away_stats||{};
  const checks=[
    n(h.total_matches)>=10&&n(a.total_matches)>=10,
    n(h.avg_goals_scored)>0&&n(a.avg_goals_scored)>0,
    n(h.avg_goals_conceded)>0&&n(a.avg_goals_conceded)>0,
    n(h.avg_xg)>0&&n(a.avg_xg)>0,
    Array.isArray(h.form)&&h.form.length>=4&&Array.isArray(a.form)&&a.form.length>=4,
    n(h.avg_shots)>0&&n(a.avg_shots)>0,
    n(h.avg_shots_on_target)>0&&n(a.avg_shots_on_target)>0,
    n(h.avg_corners)>0&&n(a.avg_corners)>0,
    Array.isArray(m.h2h)&&m.h2h.length>=2
  ];
  const base=checks.filter(Boolean).length/checks.length;
  const sample=(sampleFactor(h)+sampleFactor(a))/2;
  return Math.round(clamp(base*.72+sample*.28)*100);
}
function spreadAgreement(vals){
  const v=finite(vals);
  if(v.length<2)return 55;
  const mean=avg(v), spread=Math.sqrt(avg(v.map(x=>(x-mean)**2)));
  return Math.round(clamp(.98-spread*2.7,.35,.98)*100);
}
function model(m){
  if(!m||m.sport==='volleyball')return null;
  const lhla=estimateLambdas(m),p=probabilities(lhla.home,lhla.away);
  const specs=[
    ['btts','BTTS',p.btts,'btts_pct'],
    ['o15','Over 1.5',p.o15,'over15_pct'],
    ['o25','Over 2.5',p.o25,'over25_pct'],
    ['o35','Over 3.5',p.o35,'over35_pct']
  ];
  const dq=dataQuality(m),sample=(sampleFactor(m.home_stats||{})+sampleFactor(m.away_stats||{}))/2;
  const markets=specs.map(([key,type,pois,empKey])=>{
    const emp=empirical(m,empKey,pois);
    const shot=shotSignal(m,key,pois);
    // Ensemble weights: structural goal model > empirical > shot proxy.
    const prob=clamp(pois*.58+emp*.27+shot*.15,.03,.97);
    const agreement=spreadAgreement([pois,emp,shot]);
    const odds=n(m.odds?.[key],NaN);
    const implied=Number.isFinite(odds)&&odds>1?1/odds:null;
    const edge=implied!==null?prob-implied:null;
    const ev=implied!==null?prob*odds-1:null;
    const fair=1/prob;
    const uncertainty=clamp((100-dq)*.42+(100-agreement)*.34+(1-sample)*24,0,55);
    const confidence=Math.round(clamp(98-uncertainty,40,96));
    const score=Math.round(clamp(prob*.46+(confidence/100)*.25+(dq/100)*.17+(agreement/100)*.12)*100);
    let status='SKIP';
    if(score>=88&&prob>=.68&&confidence>=82&&dq>=75&&agreement>=72)status='ELITE';
    else if(score>=78&&prob>=.63&&confidence>=76&&dq>=70&&agreement>=65)status='STRONG';
    else if(score>=68&&prob>=.58&&confidence>=70&&dq>=65)status='LEAN';
    const value=implied!==null&&edge>=.04&&ev>0&&confidence>=70&&dq>=70&&agreement>=65;
    const green=(status==='ELITE'||status==='STRONG');
    if(value)status='VALUE';
    const reasons=[];
    if(dq<70)reasons.push('słaba jakość danych');
    if(agreement<65)reasons.push('duży rozjazd modeli');
    if(sample<.55)reasons.push('mała próba');
    if(implied!==null&&edge<.02)reasons.push('brak wyraźnej przewagi nad kursem');
    if(!reasons.length)reasons.push('sygnały są spójne');
    const explanation=[
      {label:'Struktura goli / xG',value:pois,weight:.58},
      {label:'Dane historyczne',value:emp,weight:.27},
      {label:'Strzały / SoT',value:shot,weight:.15}
    ];
    return {key,type,prob,probPct:pct(prob),poissonProb:pct(pois),empiricalProb:pct(emp),shotProb:pct(shot),
      odds:Number.isFinite(odds)&&odds>1?odds:null,impliedPct:implied===null?null:pct(implied),
      fairOdds:+fair.toFixed(2),edgePct:edge===null?null:+(edge*100).toFixed(1),evPct:ev===null?null:+(ev*100).toFixed(1),
      agreement,confidence,dataQuality:dq,samplePct:Math.round(sample*100),score,status,green,value,reasons,explanation,
      icon:key==='btts'?'🎯':'⚽'};
  });
  // 1X2 market is useful as an informational probability; do not use it to create value for itself.
  const oneXtwo=probabilities(lhla.home,lhla.away);
  const oneXtwoMarkets=['home','draw','away'].map(k=>{
    const pr=oneXtwo[k],od=n(m.odds?.[k],NaN),imp=Number.isFinite(od)&&od>1?1/od:null,edge=imp!==null?pr-imp:null,ev=imp!==null?pr*od-1:null;
    return {key:k,prob:pr,probPct:pct(pr),odds:Number.isFinite(od)&&od>1?od:null,fairOdds:+(1/pr).toFixed(2),
      impliedPct:imp===null?null:pct(imp),edgePct:edge===null?null:+(edge*100).toFixed(1),evPct:ev===null?null:+(ev*100).toFixed(1)};
  });
  const avgConf=avg(markets.map(x=>x.confidence))||50;
  const avgAgree=avg(markets.map(x=>x.agreement))||50;
  const riskFlags=[];
  if(dq<65)riskFlags.push('LOW_DATA');
  if(avgAgree<60)riskFlags.push('MODEL_DISAGREEMENT');
  if(sample<.55)riskFlags.push('SMALL_SAMPLE');
  if(markets.some(x=>x.edgePct!==null&&x.edgePct<-5))riskFlags.push('MARKET_AGAINST_MODEL');
  const top=[...markets].filter(x=>x.green||x.value).sort((a,b)=>b.score-a.score);
  const explanations=markets.reduce((acc,x)=>{acc[x.key]=x.explanation;return acc},{});
  return {version:VERSION,lambdas:{home:+lhla.home.toFixed(2),away:+lhla.away.toFixed(2),total:+(lhla.home+lhla.away).toFixed(2)},
    btts:pct(p.btts),o15:pct(p.o15),o25:pct(p.o25),o35:pct(p.o35),dataQuality:dq,
    confidence:Math.round(avgConf),modelAgreement:Math.round(avgAgree),samplePct:Math.round(sample*100),
    markets,oneXtwo:oneXtwoMarkets,top,riskFlags,explanations,
    summary:top.length?top[0].status:'SKIP'};
}
function radar(matches,opts={}){
  const minDq=opts.minDataQuality??65,minConf=opts.minConfidence??70;
  const rows=[];
  (matches||[]).forEach(m=>{
    const a=model(m);if(!a)return;
    a.markets.forEach(x=>{
      if(x.dataQuality>=minDq&&x.confidence>=minConf&&x.status!=='SKIP')rows.push({...x,match:m,analysis:a});
    });
  });
  rows.sort((a,b)=>(b.score-a.score)||(b.prob-a.prob)||(b.evPct??-999)-(a.evPct??-999));
  return {analyzed:(matches||[]).filter(m=>m.sport!=='volleyball').length,markets:rows.length,
    green:rows.filter(x=>x.green).length,value:rows.filter(x=>x.value).length,elite:rows.filter(x=>x.status==='ELITE').length,
    picks:rows.slice(0,opts.limit||10)};
}
const LOG_KEY='betstats_prediction_log_v3';
function getLogs(){try{return JSON.parse(localStorage.getItem(LOG_KEY)||'[]')}catch(e){return[]}}
function saveLogs(rows){localStorage.setItem(LOG_KEY,JSON.stringify(rows.slice(-10000)));return rows}
function predictionKey(m,x){return [m.match_id,m.home,m.away,x.key,VERSION].join('|')}
function logPrediction(m,x,a){
  if(!m||!x)return null;
  const rows=getLogs(),key=predictionKey(m,x);
  if(rows.some(r=>r.key===key))return rows.find(r=>r.key===key);
  const rec={key,createdAt:new Date().toISOString(),matchId:m.match_id,home:m.home,away:m.away,
    league:m.league_name||m.league_id||'',leagueId:m.league_id||'',datetime:m.datetime||'',market:x.key,
    marketName:x.type,probability:+x.prob.toFixed(5),odds:x.odds,fairOdds:x.fairOdds,edgePct:x.edgePct,evPct:x.evPct,
    confidence:x.confidence,dataQuality:x.dataQuality,agreement:x.agreement,score:x.score,status:x.status,
    modelVersion:a.version,result:null,resultSource:null};
  rows.push(rec);saveLogs(rows);return rec;
}
function logMatches(matches){
  let c=0;(matches||[]).forEach(m=>{const a=model(m);if(!a)return;a.markets.forEach(x=>{if(x.status!=='SKIP'){if(logPrediction(m,x,a))c++}})});
  return c;
}
function normalize(s){return String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\([^)]*\)/g,'').replace(/[^a-z0-9]+/g,' ').trim()}
function parseScore(score){const m=String(score||'').match(/(\d+)\s*[:\-]\s*(\d+)/);return m?{h:+m[1],a:+m[2]}:null}
function marketWin(market,score){
  const s=parseScore(score);if(!s)return null;
  const total=s.h+s.a;
  if(market==='btts')return s.h>0&&s.a>0;
  if(market==='o15')return total>=2;
  if(market==='o25')return total>=3;
  if(market==='o35')return total>=4;
  if(market==='home')return s.h>s.a;
  if(market==='draw')return s.h===s.a;
  if(market==='away')return s.h<s.a;
  return null;
}
function resolveLogs(finished){
  const rows=getLogs();let changed=0;
  const fin=finished||[];
  rows.forEach(r=>{
    if(r.result!==null)return;
    const hit=fin.find(f=>{
      if(f.match_id&&r.matchId&&f.match_id===r.matchId)return true;
      return normalize(f.home)===normalize(r.home)&&normalize(f.away)===normalize(r.away)&&
        (String(f.datetime||'').slice(0,8)===String(r.datetime||'').slice(0,8)||!r.datetime);
    });
    if(hit){
      const w=marketWin(r.market,hit.score);
      if(w!==null){r.result=w?1:0;r.resultSource='finished_feed';r.finishedAt=new Date().toISOString();r.finalScore=hit.score;changed++}
    }
  });
  if(changed)saveLogs(rows);return changed;
}
function calibration(rows=getLogs()){
  const done=rows.filter(r=>r.result===0||r.result===1),bins=[];
  for(let lo=.5;lo<1;.05){
    const hi=Math.min(.999,lo+.05),v=done.filter(r=>r.probability>=lo&&r.probability<hi);
    if(!v.length)continue;
    bins.push({range:`${Math.round(lo*100)}-${Math.round(hi*100)}%`,count:v.length,predicted:+(avg(v.map(r=>r.probability))*100).toFixed(1),actual:+(avg(v.map(r=>r.result))*100).toFixed(1)});
  }
  return bins;
}
function performance(rows=getLogs()){
  const done=rows.filter(r=>r.result===0||r.result===1),wins=done.filter(r=>r.result===1).length;
  let pnl=0,withOdds=0;
  done.forEach(r=>{if(r.odds>1){withOdds++;pnl+=r.result?r.odds-1:-1}});
  const brier=done.length?avg(done.map(r=>(r.probability-r.result)**2)):null;
  const buckets={};
  done.forEach(r=>{const k=r.confidence>=90?'90+':r.confidence>=85?'85-89':r.confidence>=80?'80-84':r.confidence>=75?'75-79':'<75';(buckets[k]??=[]).push(r)});
  const byConfidence=Object.entries(buckets).map(([k,v])=>({bucket:k,n:v.length,winRate:+(avg(v.map(r=>r.result))*100).toFixed(1),avgProb:+(avg(v.map(r=>r.probability))*100).toFixed(1)}));
  const markets={};done.forEach(r=>{(markets[r.marketName]??=[]).push(r)});
  const byMarket=Object.entries(markets).map(([k,v])=>({market:k,n:v.length,winRate:+(avg(v.map(r=>r.result))*100).toFixed(1),avgProb:+(avg(v.map(r=>r.probability))*100).toFixed(1)})).sort((a,b)=>b.n-a.n);
  return {total:rows.length,settled:done.length,winRate:done.length?+(wins/done.length*100).toFixed(1):null,
    brier:brier===null?null:+brier.toFixed(4),roi:withOdds?+(pnl/withOdds*100).toFixed(1):null,withOdds,calibration:calibration(rows),byConfidence,byMarket};
}
window.BetStatsEngine={VERSION,version:VERSION,model,radar,dataQuality,logPrediction,logMatches,getLogs,resolveLogs,calibration,performance,marketWin,parseScore};
})();
