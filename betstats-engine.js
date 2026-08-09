/* BetStats 2.0 — local probability / confidence engine
 * No external dependencies. Probabilities are model estimates, not guarantees.
 */
(function () {
  'use strict';

  const clamp = (x, lo=0, hi=1) => Math.max(lo, Math.min(hi, x));
  const num = (x, fallback=0) => {
    const n = Number(x);
    return Number.isFinite(n) ? n : fallback;
  };
  const avg = (a,b) => (a+b)/2;

  function weightedMean(values, weights) {
    let s=0,w=0;
    values.forEach((v,i)=>{ if(Number.isFinite(v) && v>0){ const ww=weights[i]||1; s+=v*ww; w+=ww; }});
    return w ? s/w : null;
  }

  // Recent form multiplier. Intentionally small: form should not overpower structural data.
  function formFactor(form) {
    if (!Array.isArray(form) || !form.length) return 1;
    const pts = {W:1, D:0.45, L:0};
    let s=0,w=0;
    form.slice(-5).forEach((r,i)=>{
      const ww=i+1; s += (pts[String(r).toUpperCase()] ?? 0.45)*ww; w+=ww;
    });
    const score = w ? s/w : 0.5;
    return 0.93 + score*0.14; // 0.93..1.00
  }

  function sampleScore(stats) {
    const n = num(stats && stats.total_matches,0);
    return clamp(n/15,0,1);
  }

  function poissonPmf(k, lambda) {
    if (lambda <= 0) return k===0 ? 1 : 0;
    let p = Math.exp(-lambda);
    for(let i=1;i<=k;i++) p *= lambda/i;
    return p;
  }

  function overProb(lambda, line) {
    const need=Math.floor(line)+1;
    let under=0;
    for(let k=0;k<need;k++) under += poissonPmf(k,lambda);
    return clamp(1-under);
  }

  function bttsProb(homeLambda, awayLambda) {
    return clamp(1-Math.exp(-homeLambda)-Math.exp(-awayLambda)+Math.exp(-(homeLambda+awayLambda)));
  }

  function estimateLambdas(m) {
    const hs=m.home_stats||{}, as=m.away_stats||{};
    const hSc=num(hs.avg_goals_scored), hCon=num(hs.avg_goals_conceded);
    const aSc=num(as.avg_goals_scored), aCon=num(as.avg_goals_conceded);
    const hXg=num(hs.avg_xg), aXg=num(as.avg_xg);

    const hBase = avg(hSc, aCon);
    const aBase = avg(aSc, hCon);
    let hl = hBase > 0 ? hBase : 1.25;
    let al = aBase > 0 ? aBase : 1.05;

    // xG is usually a better shot-quality signal when available.
    if(hXg>0) hl = weightedMean([hl,hXg],[0.55,0.45]);
    if(aXg>0) al = weightedMean([al,aXg],[0.55,0.45]);

    hl *= formFactor(hs.form);
    al *= formFactor(as.form);

    // Soft home advantage; keep it small to avoid overfitting.
    hl *= 1.045;
    al *= 0.965;

    return {home: clamp(hl,0.15,4.5), away: clamp(al,0.15,4.0)};
  }

  function dataQuality(m) {
    const hs=m.home_stats||{}, as=m.away_stats||{};
    const checks=[
      num(hs.total_matches)>=10 && num(as.total_matches)>=10,
      num(hs.avg_goals_scored)>0 && num(as.avg_goals_scored)>0,
      num(hs.avg_goals_conceded)>0 && num(as.avg_goals_conceded)>0,
      num(hs.avg_xg)>0 && num(as.avg_xg)>0,
      Array.isArray(hs.form)&&hs.form.length>=4 && Array.isArray(as.form)&&as.form.length>=4,
      num(hs.avg_shots)>0 && num(as.avg_shots)>0,
      num(hs.avg_corners)>0 && num(as.avg_corners)>0,
      Array.isArray(m.h2h) && m.h2h.length>=2
    ];
    const base=checks.filter(Boolean).length/checks.length;
    const sample=(sampleScore(hs)+sampleScore(as))/2;
    return Math.round(clamp(base*0.70+sample*0.30,0,1)*100);
  }

  function model(m) {
    if(!m || m.sport==='volleyball') return null;
    const {home,away}=estimateLambdas(m);
    const total=home+away;
    const btts=bttsProb(home,away);
    const o15=overProb(total,1.5);
    const o25=overProb(total,2.5);
    const o35=overProb(total,3.5);

    const hs=m.home_stats||{}, as=m.away_stats||{};
    // A secondary empirical signal. It is blended conservatively with Poisson.
    const empirical=(key, fallback)=> {
      const vals=[num(hs[key],NaN),num(as[key],NaN)].filter(Number.isFinite);
      return vals.length ? vals.reduce((a,b)=>a+b,0)/vals.length/100 : fallback;
    };
    const probs={
      btts: clamp(btts*0.72 + empirical('btts_pct',btts)*0.28),
      o15: clamp(o15*0.72 + empirical('over15_pct',o15)*0.28),
      o25: clamp(o25*0.72 + empirical('over25_pct',o25)*0.28),
      o35: clamp(o35*0.72 + empirical('over35_pct',o35)*0.28)
    };

    const dq=dataQuality(m);
    const sample=(sampleScore(hs)+sampleScore(as))/2;
    const xgAvailable= num(hs.avg_xg)>0 && num(as.avg_xg)>0;
    const agreement=Math.round(clamp(0.55 + Math.abs(probs.o25-empirical('over25_pct',probs.o25))*-0.7,0.35,0.98)*100);
    const confidence=Math.round(clamp(
      0.42 + dq/100*0.28 + sample*0.15 + (xgAvailable?0.08:0) + agreement/100*0.07,
      0,1
    )*100);

    const fair={};
    Object.keys(probs).forEach(k=>fair[k]=probs[k]>0 ? +(1/probs[k]).toFixed(2):null);

    const markets=[
      {key:'btts',type:'BTTS',prob:probs.btts,icon:'🎯'},
      {key:'o15',type:'Over 1.5',prob:probs.o15,icon:'⚽'},
      {key:'o25',type:'Over 2.5',prob:probs.o25,icon:'⚽'},
      {key:'o35',type:'Over 3.5',prob:probs.o35,icon:'⚽'}
    ].map(x=>{
      const odds=num(m.odds && m.odds[x.key]);
      const edge=odds>1 ? x.prob-(1/odds) : null;
      const ev=odds>1 ? x.prob*odds-1 : null;
      const marketScore=Math.round(clamp(
        x.prob*0.48 + confidence/100*0.27 + dq/100*0.18 + (edge!==null?clamp(edge*4,0,0.07):0)*1.0,
        0,1
      )*100);
      const green = x.prob>=0.65 && confidence>=75 && dq>=70 && agreement>=65;
      const value = edge!==null && edge>=0.04 && ev>0 && confidence>=70 && dq>=70;
      return {...x,probPct:Math.round(x.prob*100),fairOdds:fair[x.key],odds:odds||null,
        edgePct:edge===null?null:+(edge*100).toFixed(1),evPct:ev===null?null:+(ev*100).toFixed(1),
        score:marketScore,green,value,status:value?'VALUE':green?'GREEN':'SKIP'};
    });

    return {
      version:'2.0-goals-ensemble-v1',
      lambdas:{home:+home.toFixed(2),away:+away.toFixed(2),total:+total.toFixed(2)},
      btts:Math.round(probs.btts*100), o15:Math.round(probs.o15*100),
      o25:Math.round(probs.o25*100), o35:Math.round(probs.o35*100),
      dataQuality:dq, confidence, modelAgreement:agreement,
      markets, fairOdds:fair,
      top:markets.filter(x=>x.green).sort((a,b)=>b.score-a.score)
    };
  }

  function radar(matches, options={}) {
    const arr=(matches||[]).map(m=>({m,a:model(m)})).filter(x=>x.a);
    const picks=[];
    arr.forEach(({m,a})=>a.markets.forEach(x=>{
      if(x.status!=='SKIP') picks.push({...x,match:m,analysis:a});
    }));
    picks.sort((a,b)=> (b.score-a.score) || (b.prob-a.prob));
    return {
      analyzed:arr.length,
      markets:arr.reduce((n,x)=>n+x.a.markets.length,0),
      green:picks.filter(x=>x.green).length,
      value:picks.filter(x=>x.value).length,
      elite:picks.filter(x=>x.score>=85 && x.green).length,
      picks:picks.slice(0,options.limit||10)
    };
  }

  window.BetStatsEngine={version:'2.0-goals-ensemble-v1',model,radar,dataQuality};
})();
