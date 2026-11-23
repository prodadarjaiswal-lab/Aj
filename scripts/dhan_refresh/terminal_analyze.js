/* Aj Trading Terminal: Analyze tab (chart, technical, value, buy timing) and the Terminal summary.
   Runs after the desk script, so it can use D, today, sig, tested, NAMES, side, VM, NV, IDXKEY, LIVE, loadDetail, tab, esc. */
(function(){
const $=id=>document.getElementById(id);
const E=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const F=(x,d)=>x==null||!isFinite(x)?"–":Number(x).toLocaleString("en-IN",{maximumFractionDigits:d==null?(Math.abs(x)>=1000?0:2):d});
const P=(x,d=1)=>x==null||!isFinite(x)?"–":(x>0?"+":"")+(x*100).toFixed(d)+"%";
const C=x=>x==null?"":x>0?"good":x<0?"bad":"";
const MK=window.TMK||{groups:{}},WK=window.TWK||{};
const TODAY=(typeof today!=="undefined"?today:(D.today||{}).stocks)||{},RS=((D.rs||{}).stocks)||{};
const SIGS=(typeof sig!=="undefined"?sig:(D.model||{}).signals)||{},TESTED=(typeof tested!=="undefined"?tested:[]),SIDE=(typeof side!=="undefined"?side:"up");
const NM=(D.model||{}).names||{},VMR=((D.vm||{}).rules)||{},VMT=((D.vm||{}).today)||{},VMN=((D.vm||{}).names)||{};
const VSIDE=D.regimeUp===false?"weak":"up",VTEST=Object.keys(VMR).filter(k=>VMR[k]["tested_"+VSIDE]&&k!=="lt_winner");
const SHORT={mom12:"12-month leader",rs6:"6-month leader vs Nifty",stack:"Trend stack",accum:"Accumulation",recovered:"Recovered above 200-day"};

/* ---------- the universe: indices, ETFs, MCX, then every NSE stock ---------- */
const INS={},ALIAS={NIFTY:"Nifty 50",BANKNIFTY:"Nifty Bank",GOLD:"GOLD",SILVER:"SILVER"};
Object.entries(MK.groups||{}).forEach(([g,rows])=>rows.forEach(r=>{INS[r.k]={k:r.k,name:r.name,kind:g==="Indices"?"Index":g==="ETFs"?"ETF":"MCX",seg:r.seg,sid:r.sid,mk:r}}));
const SID={};Object.entries(D.lsid||{}).forEach(([id,s])=>SID[s]=id);((D.board||{}).rows||[]).forEach(r=>{if(r.sid)SID[r.s]=r.sid});(WK.stocks||[]).forEach(r=>SID[r.s]=r.sid);
(D.ix||[]).forEach(([s,n])=>{if(!INS[s])INS[s]={k:s,name:n,kind:"Stock",seg:"NSE_EQ",sid:SID[s]}});
const find=q=>{q=String(q||"").trim();if(!q)return null;if(INS[q])return INS[q];const u=q.toUpperCase();if(ALIAS[u]&&INS[ALIAS[u]])return INS[ALIAS[u]];
  const s=u.split(" · ")[0].trim();if(INS[s])return INS[s];return Object.values(INS).find(x=>x.k.toUpperCase()===s||x.name.toUpperCase()===u)||null};

/* ---------- prices ---------- */
function live(x){const q=window.TLIVE;let a=q&&x.sid!=null&&(q[x.seg]||{})[String(x.sid)];if(a&&a[0])return{ltp:a[0],pc:a[4]||null,t:window.TLIVE_T};
  const e=typeof LIVE!=="undefined"&&LIVE.eq&&LIVE.eq[x.k];return e&&e.ltp?{ltp:e.ltp,pc:e.pc||null,t:LIVE.t}:null}
function closes(x){
  if(x.mk){const h=x.mk.hist;if(h&&h.c&&h.c.length>20)return{c:h.c.slice(),d:h.d.slice()};return{c:(x.mk.spark||[]).slice(),d:null}}
  let ch=((D.chart||{}).s||{})[x.k];if(ch&&ch.x&&!ch.c)ch={c:ch.x.map(v=>ch.b+v/ch.k)};
  if(ch&&ch.c&&ch.c.length>20){const n=ch.c.length;return{c:ch.c.slice(),d:(D.chart.d||[]).slice(-n)}}
  return{c:[],d:null}}

/* ---------- indicators on daily closes (rules as in the scanner skills) ---------- */
const sma=(a,n,i=a.length-1)=>i+1<n?null:a.slice(i-n+1,i+1).reduce((s,v)=>s+v,0)/n;
function emaS(a,n){const k=2/(n+1),o=[];let e=null;a.forEach((v,i)=>{e=i<n-1?null:i===n-1?a.slice(0,n).reduce((s,x)=>s+x,0)/n:v*k+e*(1-k);o.push(e)});return o}
function rsi(a,n=14){if(a.length<n+1)return null;let g=0,l=0;for(let i=1;i<=n;i++){const d=a[i]-a[i-1];g+=Math.max(d,0);l+=Math.max(-d,0)}g/=n;l/=n;
  for(let i=n+1;i<a.length;i++){const d=a[i]-a[i-1];g=(g*(n-1)+Math.max(d,0))/n;l=(l*(n-1)+Math.max(-d,0))/n}return l===0?100:100-100/(1+g/l)}
const ret=(a,n)=>a.length>n&&a[a.length-1-n]?a[a.length-1]/a[a.length-1-n]-1:null;
function feats(x){
  const S=closes(x),L=live(x);let c=S.c.filter(v=>v!=null&&isFinite(v));
  if(L&&c.length&&Math.abs(L.ltp/c[c.length-1]-1)>1e-6)c=c.concat([L.ltp]);
  const t=x.kind==="Stock"?(TODAY[x.k]||((D.prof||{})[x.k])||{}):{},r=x.kind==="Stock"?(RS[x.k]||{}):{},pr=(D.prof||{})[x.k]||{};
  const f={n:c.length,last:L?L.ltp:c.length?c[c.length-1]:(t.c||t.last||null),live:L,prev:L&&L.pc?L.pc:c.length>1?c[c.length-2]:null};
  const m20=sma(c,20),m50=sma(c,50),m200=sma(c,200),last=c[c.length-1];
  f.vs50=m50?last/m50-1:t.vs50!=null?t.vs50/100:null;
  f.vs200=m200?last/m200-1:t.vs200!=null?t.vs200/100:r.vs200!=null?r.vs200/100:null;
  f.cross=m50&&m200?m50/m200-1:(f.vs50!=null&&f.vs200!=null?(1+f.vs200)/(1+f.vs50)-1:null);
  f.rsi=c.length>30?rsi(c):t.rsi!=null?t.rsi:r.rsi;
  if(c.length>40){const e12=emaS(c,12),e26=emaS(c,26),m=c.map((_,i)=>e12[i]!=null&&e26[i]!=null?e12[i]-e26[i]:null),mv=m.filter(v=>v!=null),sg=emaS(mv,9);f.macd=mv[mv.length-1];f.macdSig=sg[sg.length-1];f.macdUp=f.macdSig!=null?f.macd>f.macdSig:null}
  else f.macdUp=t.macd?/above/.test(t.macd):null;
  if(c.length>=20){const w=c.slice(-20),sd=Math.sqrt(w.reduce((s,v)=>s+(v-m20)**2,0)/20);f.bbPos=sd?(last-(m20-2*sd))/(4*sd):null;f.bbW=m20?4*sd/m20:null}
  f.r1m=ret(c,21)??pr.r1m??r.r1m;f.r3m=ret(c,63)??pr.r3m??r.r3m;f.r6m=ret(c,126)??r.r6m;f.r1y=c.length>=240?c[c.length-1]/c[0]-1:pr.r1y??null;
  if(c.length>=120){const w=c.slice(-252);f.hi52=last/Math.max(...w)-1;f.lo52=last/Math.min(...w)-1}else f.hi52=t.hi52!=null?t.hi52/100:null;
  if(c.length>30){const rr=c.slice(-64).map((v,i,a)=>i?Math.log(v/a[i-1]):0).slice(1),mu=rr.reduce((s,v)=>s+v,0)/rr.length;f.vol=Math.sqrt(rr.reduce((s,v)=>s+(v-mu)**2,0)/rr.length*252)}
  const nf=closes(INS["Nifty 50"]||{mk:null}).c;f.rs3=x.k==="Nifty 50"?null:(r.rs3!=null?r.rs3:(t.rs3!=null?t.rs3/100:(f.r3m!=null&&ret(nf,63)!=null?f.r3m-ret(nf,63):null)));
  f.adx=t.adx;f.di=t.di;f.st=t.st;f.volx=t.volx;f.atr=t.atr||(f.last&&t.atr_pct?f.last*t.atr_pct/100:null);
  const st=[];if(c.length>=26){if(last>Math.max(...c.slice(-21,-1)))st.push("20-day closing high");const pole=c[c.length-6]/c[c.length-16]-1,fl=c.slice(-5);
    if(pole>0.10&&(Math.max(...fl)-Math.min(...fl))/Math.min(...fl)<=0.05)st.push("Bull flag");const mp=sma(c,20,c.length-2);if(c[c.length-2]<mp&&last>m20)st.push("Reclaimed 20-day average");
    const rp=rsi(c.slice(0,-1));if(f.rsi<30)st.push("Oversold (RSI under 30)");if(rp<30&&last>c[c.length-2])st.push("Oversold bounce")}
  f.setups=st;
  f.sigs=x.kind==="Stock"?TESTED.filter(k=>(t.new||t.on||[]).includes(k)).map(k=>({k,name:NM[k]||k,o:((SIGS[k]||{}).out||{})[SIDE]||{}})):[];
  f.warn=x.kind==="Stock"?((t.on||[]).filter(k=>/downtrend|fade|weak/.test(k))):[];
  if(x.kind==="Stock"){const fd=pr.fund||{},v=((D.n50||{})[x.k]||{}).val||((D.nval||{})[x.k]||{}).val||{};
    f.v={pe:fd.pe??r.pe,pes:fd.pe_sec??r.pe_sec,pb:fd.pb??r.pb,roce:fd.roce??r.roce,de:fd.de??r.de,dy:fd.dy??r.dy,prom:fd.prom??r.prom,dfii:fd.d_fii??r.d_fii,
      cheap:r.value,gap:v.gap,gimpl:v.g_impl,g3:v.g3,fair:v.fair_at_g3,sus:(((D.nval||{})[x.k]||{}).fund||{}).verdict,ind:fd.industry||r.ind,
      rules:((VMT[x.k]||{}).on||[]).filter(k=>VTEST.includes(k))};f.v.loss=(f.v.pe!=null&&f.v.pe<=0)||(f.v.pes!=null&&f.v.pes<=0);if(f.v.loss)f.v.pes=null}
  return f}

/* ---------- buy timing: 3 months, 6 months, 1 year ---------- */
function horizons(x,f){
  const ck=(label,v)=>({label,ok:v==null?null:!!v});
  const h3=[ck("Above its 50-day average",f.vs50==null?null:f.vs50>0),ck("MACD above its signal line",f.macdUp),ck("Up over 3 months",f.r3m==null?null:f.r3m>0),
    ck("Beating the Nifty over 3 months",f.rs3==null?null:f.rs3>0),ck("RSI between 40 and 70 (not stretched)",f.rsi==null?null:f.rsi>=40&&f.rsi<=70)];
  if(x.kind==="Stock")h3.push(ck("A back-tested buy signal fired",f.sigs.length>0));
  const h6=[ck("Above its 200-day average",f.vs200==null?null:f.vs200>0),ck("50-day average above 200-day",f.cross==null?null:f.cross>0),
    ck("Up over 6 months",f.r6m==null?null:f.r6m>0),ck("Within 20% of its 52-week high",f.hi52==null?null:f.hi52>-0.20)];
  if(x.kind==="Stock")h6.push(ck("A tested 6-month value rule is on",(f.v||{}).rules?f.v.rules.length>0:null));
  let h12;
  if(x.kind==="Stock"){const v=f.v||{};h12=[ck("Company is profitable",!v.loss),ck("Price fair or cheap for its growth",v.loss?false:v.gap!=null?v.gap<0.05:v.cheap?/cheap|fair/i.test(v.cheap):v.pes!=null?v.pes<=1.1:null),
    ck("P/E not above its sector",v.loss?false:v.pes==null?null:v.pes<=1),ck("Return on capital 15% or more",v.roce==null?null:v.roce>=15),ck("Debt below equity",v.de==null?null:v.de<1),
    ck("Promoters hold 40% or more",v.prom==null?null:v.prom>=40),ck("Above its 200-day average",f.vs200==null?null:f.vs200>0)]}
  else h12=[ck("Above its 200-day average",f.vs200==null?null:f.vs200>0),ck("50-day average above 200-day",f.cross==null?null:f.cross>0),
    ck("Up over 1 year",f.r1y==null?null:f.r1y>0),ck("Within 15% of its 52-week high",f.hi52==null?null:f.hi52>-0.15)];
  const corr=!!WK.correction;
  return[["3 months",h3,corr?0.8:0.75],["6 months",h6,0.75],["1 year",h12,0.75]].map(([lab,cks,bar])=>{const k=cks.filter(c=>c.ok!=null),p=k.filter(c=>c.ok).length,s=k.length?p/k.length:null;
    const v=s==null||k.length<3?["Not enough data","azm"]:s>=bar&&!(lab==="3 months"&&f.warn.length)?["Good to buy","good"]:s<=0.4?["Avoid","bad"]:["Wait","warn"];return{lab,cks,p,n:k.length,v}})}
window.azHorizons=sym=>{const x=find(sym);return x?horizons(x,feats(x)):null};

/* ---------- chart ---------- */
function chart(x,f){const S=closes(x);let c=S.c;if(!c.length)return`<p class="note">No price history for this one yet.</p>`;
  const L=f.live;if(L&&Math.abs(L.ltp/c[c.length-1]-1)>1e-6)c=c.concat([L.ltp]);
  const n=c.length,m50=c.map((_,i)=>sma(c,50,i)),m200=c.map((_,i)=>sma(c,200,i)),W=640,H=240,l=8,r=56,tp=10,b=22;
  const all=[...c,...m50.filter(v=>v),...m200.filter(v=>v)];let lo=Math.min(...all),hi=Math.max(...all);const pd=(hi-lo)*0.05||1;lo-=pd;hi+=pd;
  const X=i=>l+i/(n-1)*(W-l-r),Y=v=>tp+(1-(v-lo)/(hi-lo))*(H-tp-b),path=a=>a.map((v,i)=>v==null?null:[X(i),Y(v)]).filter(Boolean).map((p,i)=>(i?"L":"M")+p[0].toFixed(1)+" "+p[1].toFixed(1)).join("");
  const up=c[n-1]>=c[0],col=up?"var(--up)":"var(--down)",ticks=[0,1,2,3,4].map(i=>lo+(hi-lo)*i/4);
  const ds=S.d||[],lbl=[0,Math.floor(n/2),n-1].map(i=>[i,ds[i]||""]).filter(z=>z[1]);
  return`<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${E(x.name)} price, ${n} days">
   ${ticks.map(v=>`<line x1="${l}" x2="${W-r}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)" stroke-width=".5"/><text x="${W-r+4}" y="${Y(v)+3}" style="font-size:10px;fill:var(--mute)">${F(v,v>=1000?0:1)}</text>`).join("")}
   <path d="${path(c)}L${X(n-1)} ${H-b}L${X(0)} ${H-b}Z" fill="${col}" opacity=".08"/>
   <path d="${path(m200)}" fill="none" stroke="var(--mute)" stroke-width="1.2" stroke-dasharray="4 3"/>
   <path d="${path(m50)}" fill="none" stroke="var(--accent)" stroke-width="1.2"/>
   <path d="${path(c)}" fill="none" stroke="${col}" stroke-width="1.8"/>
   <circle cx="${X(n-1)}" cy="${Y(c[n-1])}" r="3" fill="${col}"/>
   ${lbl.map(([i,d])=>`<text x="${X(i)}" y="${H-6}" text-anchor="${i===0?"start":i===n-1?"end":"middle"}" style="font-size:10px;fill:var(--mute)">${E(d)}</text>`).join("")}
  </svg><p class="note"><span style="color:${col}">━</span> price &nbsp;<span style="color:var(--accent)">━</span> 50-day average &nbsp;<span style="color:var(--mute)">┅</span> 200-day average · ${n} trading days</p>`}

/* ---------- tiles ---------- */
const tile=(k,v,cl,sub)=>`<div class="azt ${cl||""}"><span>${E(k)}</span><b>${v}</b>${sub?`<small>${sub}</small>`:""}</div>`;
function techTiles(x,f){const g=(v,a,b)=>v==null?"":v>a?"good":v<b?"bad":"warn";
  const T=[tile("vs 50-day avg",P(f.vs50),C(f.vs50)),tile("vs 200-day avg",P(f.vs200),f.vs200!=null&&Math.abs(f.vs200)<0.0005?"":C(f.vs200)),tile("50-day vs 200-day",f.cross==null?"–":f.cross>0?"Above":"Below",C(f.cross),f.cross==null?"":f.cross>0?"golden cross side":"death cross side"),
   tile("RSI (14)",F(f.rsi,0),f.rsi==null?"":f.rsi>75||f.rsi<30?"warn":f.rsi>=50?"good":"bad",f.rsi>70?"overbought":f.rsi<30?"oversold":""),
   tile("MACD",f.macdUp==null?"–":f.macdUp?"Above signal":"Below signal",f.macdUp==null?"":f.macdUp?"good":"bad"),
   tile("Bollinger position",f.bbPos==null?"–":Math.round(f.bbPos*100)+"%",f.bbPos==null?"":f.bbPos>1||f.bbPos<0?"warn":"",f.bbW!=null?"band width "+P(f.bbW,1).replace("+",""):""),
   tile("1 month",P(f.r1m),C(f.r1m)),tile("3 months",P(f.r3m),C(f.r3m)),tile("6 months",P(f.r6m),C(f.r6m)),tile("1 year",P(f.r1y),C(f.r1y)),
   tile("From 52-week high",P(f.hi52),f.hi52==null?"":f.hi52>-0.05?"good":f.hi52<-0.25?"bad":"warn"),tile("vs Nifty, 3 months",P(f.rs3),C(f.rs3)),
   tile("Volatility (yearly)",f.vol==null?"–":(f.vol*100).toFixed(0)+"%","")];
  if(x.kind==="Stock")T.push(tile("ADX (trend strength)",F(f.adx,0),f.adx==null?"":f.adx>=25?"good":"",f.di?f.di+" in control":""),tile("Supertrend",f.st?f.st==="up"?"Up":"Down":"–",f.st?f.st==="up"?"good":"bad":""),
    tile("Volume vs normal",f.volx==null?"–":F(f.volx,2)+"×",f.volx>1.5?"good":""),tile("ATR (daily range)",f.atr?"₹"+F(f.atr,1):"–",""));
  const S=[...f.sigs.map(s=>`<span class="tag good" title="${E(s.name)}">✓ ${E(s.name)}${s.o.hit10!=null?` · beat Nifty ${Math.round(s.o.hit10*100)}% of ${F(s.o.n,0)} times`:""}</span>`),
    ...f.setups.map(s=>`<span class="tag">${E(s)}</span>`),...f.warn.map(s=>`<span class="tag bad">${E(s)}</span>`)];
  return`<div class="azg">${T.join("")}</div>${S.length?`<div class="row" style="gap:6px;margin-top:10px">${S.join("")}</div>`:`<p class="note" style="margin-top:8px">No setup or tested signal on the last close.</p>`}`}
function valTiles(x,f){if(x.kind!=="Stock")return`<p class="note">${x.kind==="MCX"?"A commodity has no earnings, so there is no value check. The 1-year view uses trend only.":x.kind==="ETF"?"An ETF holds a basket, so value checks on one company do not apply. The 1-year view uses trend only.":"An index has no single company value. The 1-year view uses trend only."}</p>`;
  const v=f.v||{};if(v.pe==null&&v.roce==null&&v.gap==null)return`<p class="note">No fundamentals for this stock yet.</p>`;
  const T=[tile("P/E",v.loss?"Loss-making":F(v.pe,1),v.loss?"bad":""),tile("P/E vs sector",v.pes==null?"–":F(v.pes,2)+"×",v.pes==null?"":v.pes<=0.8?"good":v.pes>1.3?"bad":"warn",v.pes==null?"":v.pes<1?"cheaper than peers":"dearer than peers"),
   tile("Price / book",F(v.pb,1),""),tile("Return on capital",v.roce==null?"–":F(v.roce,1)+"%",v.roce==null?"":v.roce>=15?"good":v.roce<8?"bad":"warn"),
   tile("Debt / equity",F(v.de,2),v.de==null?"":v.de<=0.5?"good":v.de>1.5?"bad":"warn"),tile("Dividend yield",v.dy==null?"–":F(v.dy,2)+"%",""),
   tile("Promoter holding",v.prom==null?"–":F(v.prom,1)+"%",v.prom==null?"":v.prom>=50?"good":v.prom<30?"warn":""),
   tile("FII change (quarter)",v.dfii==null?"–":(v.dfii>0?"+":"")+F(v.dfii,2)+" pts",C(v.dfii))];
  if(v.gap!=null)T.push(tile("Growth priced in",P(v.gimpl,0).replace("+","")+"/yr",v.gap<0.05?"good":"bad","delivered "+P(v.g3,0).replace("+","")+"/yr"+(v.fair?` · value ≈ ₹${F(v.fair,0)}`:"")));
  if(v.cheap)T.push(tile("Value score",E(v.cheap[0].toUpperCase()+v.cheap.slice(1)),/cheap/i.test(v.cheap)?"good":/expens|rich/i.test(v.cheap)?"bad":"warn"));
  const R=v.rules.map(k=>{const s=(VMR[k]||{})["6m_"+VSIDE]||{};return`<span class="tag good">✓ ${E(SHORT[k]||VMN[k]||k)}${s.lift!=null?` · +${(s.lift*100).toFixed(1)}% vs average stock over 6 months, tested`:""}</span>`});
  return`<div class="azg">${T.join("")}</div>${R.length?`<div class="row" style="gap:6px;margin-top:10px">${R.join("")}</div>`:""}${v.sus?`<p class="note" style="margin-top:8px">Sustainable growth check: ${E(v.sus)}.</p>`:""}`}
function timing(H){return`<div class="azh">${H.map(h=>`<div class="azhc"><span class="sub">${h.lab}</span><b class="${h.v[1]}">${h.v[0]}</b><small>${h.p} of ${h.n} checks pass</small>
   <ul>${h.cks.map(c=>`<li class="${c.ok==null?"azm":c.ok?"good":"bad"}">${c.ok==null?"·":c.ok?"✓":"✗"} ${E(c.label)}</li>`).join("")}</ul></div>`).join("")}</div>
   <p class="note">Rule checks on today's chart and accounts, not a forecast. ${WK.correction?"Market is in a correction, so the 3-month bar is higher. ":""}Research software, not advice.</p>`}

/* ---------- Analyze ---------- */
let CUR=null,LAST=0;
function head(x,f){const L=f.live,ch=f.prev&&f.last?f.last/f.prev-1:null,H=horizons(x,f);
  return`<div class="row" style="justify-content:space-between;align-items:flex-end;gap:12px"><div><span class="sub">${E(x.kind)}${x.mk&&x.mk.contract?" · "+E(x.mk.contract):""}${f.v&&f.v.ind?" · "+E(f.v.ind):""}</span>
   <h2 style="margin:2px 0 0;font-size:1.5rem">${E(x.k)} <span class="note" style="font-weight:400">${x.name!==x.k?E(x.name):""}</span></h2></div>
   <div style="text-align:right"><b style="font-size:1.6rem">${x.kind==="Index"?"":"₹"}${F(f.last)}</b> <span class="${C(ch)}">${P(ch,2)}</span><br><span class="note">${L?`LIVE ${E(String(L.t||"").slice(11,19))} IST`:"last close"}</span></div></div>
   <div class="row" style="gap:8px;margin-top:10px">${H.map(h=>`<span class="tag ${h.v[1]}">${h.lab}: ${h.v[0]}</span>`).join("")}</div>`}
function render(){const x=CUR;if(!x)return;const f=feats(x);LAST=Date.now();
  $("az-head").innerHTML=head(x,f);$("az-chart").innerHTML=chart(x,f);$("az-tech").innerHTML=techTiles(x,f);$("az-val").innerHTML=valTiles(x,f);$("az-time").innerHTML=timing(horizons(x,f));
  $("az-body").hidden=false;$("az-empty").hidden=true}
function open(q){const x=find(q);if(!x){$("az-empty").hidden=false;$("az-empty").textContent=`Nothing found for "${q}". Pick from the list.`;return}
  CUR=x;$("az-q").value="";try{SHOWN=x.kind==="Stock"?x.k:SHOWN}catch(e){}try{localStorage.setItem("az-last",x.k)}catch(e){}
  render();if(x.kind==="Stock"&&typeof loadDetail==="function")loadDetail(x.k).then(()=>{if(CUR===x)render()}).catch(()=>{})}
window.azGo=q=>{try{tab("analyze")}catch(e){}open(q);window.scrollTo(0,0)};
window.azOpen=open;
try{show=function(s){open(s)}}catch(e){}
const dl=$("az-list");if(dl){const opt=x=>`<option value="${E(x.k)}">${E(x.name)} · ${x.kind}</option>`;const all=Object.values(INS);
  dl.innerHTML=all.filter(x=>x.kind!=="Stock").map(opt).join("")+all.filter(x=>x.kind==="Stock").sort((a,b)=>a.k<b.k?-1:1).map(opt).join("")}
const qi=$("az-q");qi.addEventListener("change",()=>{if(find(qi.value))open(qi.value)});qi.addEventListener("keydown",e=>{if(e.key==="Enter")open(qi.value)});
$("az-quick").innerHTML=["Nifty 50","Nifty Bank","NIFTYBEES","GOLD","SILVER","CRUDEOIL"].filter(k=>INS[k]).map(k=>`<button class="chip" data-az="${E(k)}">${E(INS[k].name.replace(/ \(.*$/,""))}</button>`).join("");
document.addEventListener("click",e=>{const b=e.target.closest("[data-az]");if(b)window.azGo(b.dataset.az)});
$("az-proof").onclick=()=>{const p=$("proof");p.hidden=!p.hidden;$("az-proof").textContent=p.hidden?"Show proof":"Hide proof";if(!p.hidden)p.scrollIntoView()};
document.addEventListener("tlive",()=>{if(CUR&&!$("az").hidden&&Date.now()-LAST>15000)render();sumLive()});
{let s=null;try{s=localStorage.getItem("az-last")}catch(e){}open(s&&find(s)?s:"Nifty 50")}

/* ---------- Terminal summary: what worked, in one place ---------- */
const vchip=h=>h?h.map(z=>`<td class="${z.v[1]}">${z.v[0]==="Good to buy"?"Buy":z.v[0]==="Not enough data"?"–":z.v[0]}</td>`).join(""):"<td></td><td></td><td></td>";
function sum(){const el=$("tm-sum");if(!el)return;const S=WK.signals||[],R=WK.stocks||[];
  const lt=Object.keys(VMT).map(s=>{const on=(VMT[s].on||[]).filter(k=>VTEST.includes(k));if(on.length<2||!INS[s])return null;const h=window.azHorizons(s);return h&&h[2].v[1]==="good"?{s,on,h,r:RS[s]||{}}:null})
    .filter(Boolean).sort((a,b)=>b.on.length-a.on.length||((a.r.pe_sec||9)-(b.r.pe_sec||9))).slice(0,12);
  el.innerHTML=`<div class="row" style="justify-content:space-between"><span class="pill ${WK.correction?"fail":"pass"}">${E(WK.label||"–")}</span><span class="note">Tap any name to analyze</span></div>
   <div><h3 style="font-size:15px;margin-bottom:6px">Signals that worked</h3><div class="scroll"><table><tr><th>Signal</th><th class="n">Won</th><th class="n">Avg vs Nifty, 10 days</th></tr>
    ${S.length?S.map(s=>`<tr><td style="white-space:normal">${E(s.name)}</td><td class="n">${s.hit10==null?"–":Math.round(s.hit10*100)+"%"}</td><td class="n ${s.x10>0?"up":"down"}">${s.x10==null?"–":P(s.x10,2)}</td></tr>`).join(""):`<tr><td class="note">None passes for this market. No trades.</td></tr>`}</table></div></div>
   <div><h3 style="font-size:15px;margin-bottom:6px">Buy now (short term)</h3><div class="scroll"><table><tr><th>Stock</th><th class="n">Live</th><th class="n">Stop</th><th class="n">Target</th><th class="n">Qty</th><th>3M</th><th>6M</th><th>1Y</th></tr>
    ${R.length?R.map(r=>`<tr class="go" data-mk="${E(r.s)}"><td><button class="lnk" data-mk="${E(r.s)}">${E(r.s)}</button></td><td class="n" data-lv="${E(r.s)}">${F(r.c)}</td><td class="n down">${F(r.stop)}</td><td class="n up">${F(r.tgt)}</td><td class="n">${r.qty}</td>${vchip(window.azHorizons(r.s))}</tr>`).join(""):`<tr><td class="note">No stock has a working signal today.</td></tr>`}</table></div></div>
   <div><h3 style="font-size:15px;margin-bottom:6px">Hold 6 to 12 months</h3><div class="scroll"><table><tr><th>Stock</th><th>Tested rules on</th><th class="n">P/E vs sector</th><th class="n">ROCE</th><th>3M</th><th>6M</th><th>1Y</th></tr>
    ${lt.length?lt.map(z=>`<tr class="go" data-mk="${E(z.s)}"><td><button class="lnk" data-mk="${E(z.s)}">${E(z.s)}</button></td><td style="white-space:normal">${z.on.map(k=>E(SHORT[k]||k)).join(", ")}</td><td class="n">${z.r.pe_sec==null?"–":z.r.pe_sec<=0?"loss":F(z.r.pe_sec,2)+"×"}</td><td class="n">${z.r.roce==null?"–":F(z.r.roce,0)+"%"}</td>${vchip(z.h)}</tr>`).join(""):`<tr><td class="note">No stock passes both the tested rules and the 1-year checks today.</td></tr>`}</table></div></div>`}
function sumLive(){document.querySelectorAll("#tm-sum [data-lv]").forEach(td=>{const x=INS[td.dataset.lv],L=x&&live(x);if(L){const c=L.pc?L.ltp/L.pc-1:null;td.innerHTML=`${F(L.ltp)} <small class="${c>0?"up":c<0?"down":""}">${c==null?"":P(c,2)}</small>`}})}
try{sum()}catch(e){console.error("sum",e)}
})();
