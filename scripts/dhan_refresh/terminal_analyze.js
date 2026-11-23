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
  f.r1m=ret(c,21)??pr.r1m??r.r1m;f.r3m=ret(c,63)??pr.r3m??r.r3m;f.r6m=ret(c,126)??r.r6m;f.r1y=c.length>252?ret(c,252):c.length>=240?c[c.length-1]/c[0]-1:pr.r1y??null;
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
let RNG=252,CH=null;const RNGS=[["3M",63],["6M",126],["1Y",252],["3Y",760]];
function chart(x,f){const S=closes(x);let c=S.c;if(!c.length)return`<p class="note">No price history for this one yet.</p>`;
  const L=f.live,dd=(S.d||[]).slice();if(L&&Math.abs(L.ltp/c[c.length-1]-1)>1e-6){c=c.concat([L.ltp]);dd.push("live")}
  const avail=RNGS.filter((z,i)=>i<3||c.length>300),rn=Math.min(RNG,c.length);
  let m50=c.map((_,i)=>sma(c,50,i)),m200=c.map((_,i)=>sma(c,200,i));const cut=Math.max(0,c.length-rn),ds0=dd.slice(cut);c=c.slice(cut);m50=m50.slice(cut);m200=m200.slice(cut);
  const n=c.length,W=640,H=240,l=8,r=56,tp=10,b=22;
  const all=[...c,...m50.filter(v=>v),...m200.filter(v=>v)];let lo=Math.min(...all),hi=Math.max(...all);const pd=(hi-lo)*0.05||1;lo-=pd;hi+=pd;
  const X=i=>l+i/(n-1)*(W-l-r),Y=v=>tp+(1-(v-lo)/(hi-lo))*(H-tp-b),path=a=>a.map((v,i)=>v==null?null:[X(i),Y(v)]).filter(Boolean).map((p,i)=>(i?"L":"M")+p[0].toFixed(1)+" "+p[1].toFixed(1)).join("");
  const up=c[n-1]>=c[0],col=up?"var(--up)":"var(--down)",ticks=[0,1,2,3,4].map(i=>lo+(hi-lo)*i/4);
  const ds=ds0,lbl=[0,Math.floor(n/2),n-1].map(i=>[i,ds[i]||""]).filter(z=>z[1]);
  CH={X,Y,c,ds:ds0,n,l,r,W,H,tp,b,cur:x.kind==="Index"?"":"₹"};
  return`<div class="row" style="gap:6px;margin-bottom:6px">${avail.map(([t,k])=>`<button class="chip${k===RNG?" on":""}" data-rng="${k}">${t}</button>`).join("")}<span class="note" id="az-hov" style="margin-left:auto"></span></div>
  <svg id="az-svg" viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${E(x.name)} price, ${n} days" style="touch-action:pan-y">
   ${ticks.map(v=>`<line x1="${l}" x2="${W-r}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)" stroke-width=".5"/><text x="${W-r+4}" y="${Y(v)+3}" style="font-size:10px;fill:var(--mute)">${F(v,v>=1000?0:1)}</text>`).join("")}
   <path d="${path(c)}L${X(n-1)} ${H-b}L${X(0)} ${H-b}Z" fill="${col}" opacity=".08"/>
   <path d="${path(m200)}" fill="none" stroke="var(--mute)" stroke-width="1.2" stroke-dasharray="4 3"/>
   <path d="${path(m50)}" fill="none" stroke="var(--accent)" stroke-width="1.2"/>
   <path d="${path(c)}" fill="none" stroke="${col}" stroke-width="1.8"/>
   <circle cx="${X(n-1)}" cy="${Y(c[n-1])}" r="3" fill="${col}"/>
   ${(()=>{const lv=levels(c,c[n-1]),z=[[lv.sup[0],"var(--up)","S"],[lv.res[0],"var(--down)","R"]].filter(q=>q[0]&&q[0].p>lo&&q[0].p<hi);return z.map(([q,cc,t])=>`<line x1="${l}" x2="${W-r}" y1="${Y(q.p)}" y2="${Y(q.p)}" stroke="${cc}" stroke-width=".8" stroke-dasharray="2 3"/><text x="${l+2}" y="${t==="S"?Y(q.p)+11:Y(q.p)-3}" style="font-size:10px;fill:${cc}">${t} ${F(q.p,q.p>=1000?0:1)}</text>`).join("")})()}
   <line id="az-x" x1="0" x2="0" y1="${tp}" y2="${H-b}" stroke="var(--ink)" stroke-width=".6" opacity="0"/><circle id="az-dot" r="3.5" fill="var(--ink)" opacity="0"/>
   ${lbl.map(([i,d])=>`<text x="${X(i)}" y="${H-6}" text-anchor="${i===0?"start":i===n-1?"end":"middle"}" style="font-size:10px;fill:var(--mute)">${E(d)}</text>`).join("")}
  </svg><p class="note"><span style="color:${col}">━</span> price &nbsp;<span style="color:var(--accent)">━</span> 50-day average &nbsp;<span style="color:var(--mute)">┅</span> 200-day average · <span style="color:var(--up)">┄</span> support <span style="color:var(--down)">┄</span> resistance · ${n} trading days. Hover or tap the chart for a day’s price.</p>`}
function hover(e){const sv=$("az-svg");if(!sv||!CH)return;const bx=sv.getBoundingClientRect(),px=(e.touches?e.touches[0].clientX:e.clientX)-bx.left,vx=px/bx.width*CH.W;
  const i=Math.max(0,Math.min(CH.n-1,Math.round((vx-CH.l)/(CH.W-CH.l-CH.r)*(CH.n-1)))),v=CH.c[i],x0=CH.X(i),ch=CH.c[CH.n-1]/v-1;
  const ln=$("az-x"),dt=$("az-dot");ln.setAttribute("x1",x0);ln.setAttribute("x2",x0);ln.setAttribute("opacity",".5");dt.setAttribute("cx",x0);dt.setAttribute("cy",CH.Y(v));dt.setAttribute("opacity","1");
  $("az-hov").innerHTML=`${E(CH.ds[i]||"")} · <b>${CH.cur}${F(v)}</b> · <span class="${C(ch)}">${P(ch)} since</span>`}
function bindChart(){const sv=$("az-svg");if(!sv)return;sv.addEventListener("mousemove",hover);sv.addEventListener("touchstart",hover,{passive:true});sv.addEventListener("touchmove",hover,{passive:true});
  sv.addEventListener("mouseleave",()=>{$("az-x").setAttribute("opacity","0");$("az-dot").setAttribute("opacity","0");$("az-hov").textContent=""})}
document.addEventListener("click",e=>{const b=e.target.closest("[data-rng]");if(b&&CUR){RNG=+b.dataset.rng;$("az-chart").innerHTML=chart(CUR,feats(CUR));bindChart()}});


/* ---------- support / resistance and past falls (daily closes) ---------- */
function levels(c,last){if(c.length<30||!last)return{sup:[],res:[]};const k=5,piv=[];
  for(let i=k;i<c.length-k;i++){const w=c.slice(i-k,i+k+1),v=c[i];if(v===Math.min(...w))piv.push([v,"L"]);else if(v===Math.max(...w))piv.push([v,"H"])}
  const cl=[];piv.sort((a,b)=>a[0]-b[0]).forEach(([v])=>{const z=cl[cl.length-1];if(z&&v/z.lo-1<=0.015){z.v.push(v);z.lo=Math.min(z.lo,v)}else cl.push({lo:v,v:[v]})});
  const L=cl.map(z=>({p:z.v.reduce((a,b)=>a+b,0)/z.v.length,n:z.v.length,src:"swing"}));
  const sup=L.filter(z=>z.p<last*0.997).sort((a,b)=>b.p-a.p).slice(0,2),res=L.filter(z=>z.p>last*1.003).sort((a,b)=>a.p-b.p).slice(0,2);
  const m50=sma(c,50),m200=sma(c,200);[[m50,"50-day average"],[m200,"200-day average"]].forEach(([m,n])=>{if(m&&m<last)sup.push({p:m,n:0,src:n})});
  if(!res.length&&c.length>=120){const h=Math.max(...c.slice(-252));if(h>last*1.003)res.push({p:h,n:1,src:"52-week high"})}
  sup.sort((a,b)=>b.p-a.p);return{sup,res}}
function falls(c,d){if(c.length<30)return{th:0.1,rows:[]};const run=th=>{const rows=[];let pk=0,tr=0,inF=false;
  for(let i=1;i<c.length;i++){if(!inF){if(c[i]>=c[pk]){pk=i;continue}if(c[i]/c[pk]-1<=-th){inF=true;tr=i}}
    else{if(c[i]<c[tr])tr=i;if(c[i]>=c[pk]){rows.push({pk,tr,rc:i});inF=false;pk=i}}}
  if(inF)rows.push({pk,tr,rc:null});return rows};
  let th=0.10,r=run(th);for(const t of [0.07,0.05]){if(r.filter(x=>x.rc!=null).length>=2)break;th=t;r=run(th)}
  const D=i=>d&&d[i]?d[i]:i+" bars ago";
  return{th,rows:r.map(x=>({peak:D(x.pk),trough:D(x.tr),fall:c[x.tr]/c[x.pk]-1,down:x.tr-x.pk,up:x.rc==null?null:x.rc-x.tr,rec:x.rc==null?null:D(x.rc),open:x.rc==null,now:x.rc==null?c[c.length-1]/c[x.pk]-1:null}))}}
function levelsHtml(x,f){const S=closes(x);let c=S.c.filter(v=>v!=null&&isFinite(v));const last=f.last;if(c.length<30)return"";
  const {sup,res}=levels(c,last),F=falls(c,S.d),R=F.rows,done=R.filter(r=>!r.open).map(r=>r.up).sort((a,b)=>a-b),med=done.length?done[Math.floor(done.length/2)]:null;
  const row=(z,kind)=>`<tr><td>${kind}</td><td class="n">${x.kind==="Index"?"":"₹"}${F_(z.p)}</td><td class="n ${kind==="Support"?"bad":"good"}">${P(z.p/last-1)}</td><td>${z.src==="swing"?`turned here ${z.n} time${z.n>1?"s":""}`:E(z.src)}</td></tr>`;
  return`<div class="azlv"><div><h3 style="font-size:14px;margin:12px 0 6px">Support and resistance</h3><div class="tw"><table><tr><th></th><th class="n">Level</th><th class="n">From price</th><th>Why</th></tr>
   ${res.slice().reverse().map(z=>row(z,"Resistance")).join("")}${sup.map(z=>row(z,"Support")).join("")||'<tr><td colspan="4" class="note">No support below in this year\'s data (price is at its lows).</td></tr>'}</table></div></div>
   <div><h3 style="font-size:14px;margin:12px 0 6px">Past falls of ${Math.round(F.th*100)}% or more, and how soon they recovered</h3>${R.length?`<div class="tw"><table><tr><th>Peak</th><th class="n">Fall</th><th>Bottom</th><th class="n">Days down</th><th class="n">Days to recover</th></tr>
   ${R.map(r=>`<tr><td>${E(r.peak)}</td><td class="n bad">${P(r.fall)}</td><td>${E(r.trough)}</td><td class="n">${r.down}</td><td class="n">${r.open?`<span class="warn">not yet (${P(r.now)} from peak)</span>`:r.up}</td></tr>`).join("")}</table></div>
   <p class="note">${med!=null?`Typical recovery: about ${med} trading days from the bottom back to the old peak. `:""}Based on ${c.length} trading days of closes${c.length>300?` (about ${Math.round(c.length/250)} years)`:""}.</p>`:`<p class="note">No fall of 5% or more in the last ${c.length} trading days.</p>`}</div></div>`}
const F_=x=>F(x);

/* ---------- risk and return, momentum oscillators (daily closes) ---------- */
function riskStats(x){const S=closes(x),c=S.c,d=S.d;if(c.length<120)return null;const n=Math.min(252,c.length-1),cc=c.slice(-n-1),r=cc.slice(1).map((v,i)=>v/cc[i]-1);
  const rf=((D.quant||{}).rf||0.07)/252,mu=r.reduce((a,b)=>a+b,0)/r.length,sd=Math.sqrt(r.reduce((a,b)=>a+(b-mu)**2,0)/r.length),dn=Math.sqrt(r.reduce((a,b)=>a+Math.min(0,b-rf)**2,0)/r.length);
  let pk=cc[0],mdd=0;cc.forEach(v=>{pk=Math.max(pk,v);mdd=Math.min(mdd,v/pk-1)});const ann=Math.pow(cc[cc.length-1]/cc[0],252/n)-1;
  const q=r.slice().sort((a,b)=>a-b),k=Math.max(1,Math.floor(q.length*0.05)),var95=-q[k-1],cvar=-q.slice(0,k).reduce((a,b)=>a+b,0)/k;
  let beta=null,corr=null;const N=INS["Nifty 50"];if(N&&x.k!=="Nifty 50"&&d){const ns=closes(N),m={};(ns.d||[]).forEach((dd,i)=>m[dd]=ns.c[i]);
    const pr=[];for(let i=c.length-n;i<c.length;i++){const a=m[d[i]],b=m[d[i-1]];if(a&&b&&c[i-1])pr.push([c[i]/c[i-1]-1,a/b-1])}
    if(pr.length>60){const ma=pr.reduce((s,z)=>s+z[0],0)/pr.length,mb=pr.reduce((s,z)=>s+z[1],0)/pr.length;let cv=0,vb=0,va=0;pr.forEach(([a,b])=>{cv+=(a-ma)*(b-mb);vb+=(b-mb)**2;va+=(a-ma)**2});beta=cv/vb;corr=cv/Math.sqrt(va*vb)}}
  return{n,ann,vol:sd*Math.sqrt(252),sharpe:sd?(mu-rf)/sd*Math.sqrt(252):null,sortino:dn?(mu-rf)/dn*Math.sqrt(252):null,mdd,calmar:mdd<0?ann/-mdd:null,var95,cvar,beta,corr}}
function momStats(c){if(c.length<60)return null;const last=c[c.length-1],w14=c.slice(-14),hi=Math.max(...w14),lo=Math.min(...w14),o={};
  o.stoch=hi>lo?(last-lo)/(hi-lo)*100:null;o.willr=o.stoch==null?null:o.stoch-100;
  const w20=c.slice(-20),m=w20.reduce((a,b)=>a+b,0)/20,md=w20.reduce((a,b)=>a+Math.abs(b-m),0)/20,sd=Math.sqrt(w20.reduce((a,b)=>a+(b-m)**2,0)/20);
  o.cci=md?(last-m)/(0.015*md):null;o.z=sd?(last-m)/sd:null;
  const w25=c.slice(-26),ih=w25.lastIndexOf(Math.max(...w25)),il=w25.lastIndexOf(Math.min(...w25));o.aup=ih/25*100;o.adn=il/25*100;
  const w55=c.slice(-56,-1),dh=Math.max(...w55),dl=Math.min(...w55);o.don=dh>dl?(last-dl)/(dh-dl):null;o.roc12=c.length>252?last/c[c.length-253]-1:null;return o}
function riskHtml(x){const R=riskStats(x);if(!R)return`<p class="note">Needs at least 6 months of prices.</p>`;
  const T=[tile("Return, 1 year",P(R.ann),C(R.ann)),tile("Volatility",(R.vol*100).toFixed(1)+"%",""),tile("Sharpe ratio",F(R.sharpe,2),R.sharpe==null?"":R.sharpe>=1?"good":R.sharpe<0?"bad":"warn","return per unit of risk, above cash"),
   tile("Sortino ratio",F(R.sortino,2),R.sortino==null?"":R.sortino>=1.5?"good":R.sortino<0?"bad":"warn","counts only downside swings"),tile("Max drawdown",P(R.mdd),R.mdd<-0.3?"bad":R.mdd<-0.15?"warn":"good","worst peak-to-bottom fall"),
   tile("Calmar ratio",F(R.calmar,2),R.calmar==null?"":R.calmar>=1?"good":R.calmar<0?"bad":"warn","yearly return ÷ max drawdown"),
   tile("1-day VaR (95%)",P(-R.var95),"","1 day in 20 is worse than this"),tile("CVaR (95%)",P(-R.cvar),"","average of those worst days"),
   tile("Beta vs Nifty",R.beta==null?"–":F(R.beta,2),"",R.corr==null?"":"correlation "+F(R.corr,2))];
  return`<div class="azg">${T.join("")}</div><p class="note" style="margin-top:6px">Last ${R.n} trading days of closes. Cash rate ${(((D.quant||{}).rf||0.07)*100).toFixed(1)}%.</p>`}
/* ---------- tiles ---------- */
const tile=(k,v,cl,sub)=>`<div class="azt ${cl||""}"><span>${E(k)}</span><b>${v}</b>${sub?`<small>${sub}</small>`:""}</div>`;
function techTiles(x,f){const g=(v,a,b)=>v==null?"":v>a?"good":v<b?"bad":"warn";
  const M=momStats(closes(x).c.filter(v=>v>0).concat(f.live&&f.live.ltp?[f.live.ltp]:[]))||{},st=x.kind==="Stock";
  const G=[["Trend",[tile("vs 50-day avg",P(f.vs50),C(f.vs50)),tile("vs 200-day avg",P(f.vs200),f.vs200!=null&&Math.abs(f.vs200)<0.0005?"":C(f.vs200)),tile("50-day vs 200-day",f.cross==null?"–":f.cross>0?"Above":"Below",C(f.cross),f.cross==null?"":f.cross>0?"golden cross side":"death cross side"),
     st&&tile("ADX (trend strength)",F(f.adx,0),f.adx==null?"":f.adx>=25?"good":"",f.di?f.di+" in control":""),st&&tile("Supertrend",f.st?f.st==="up"?"Up":"Down":"–",f.st?f.st==="up"?"good":"bad":""),
     M.aup!=null&&tile("Aroon up / down (25)",F(M.aup,0)+" / "+F(M.adn,0),M.aup>70&&M.adn<30?"good":M.adn>70&&M.aup<30?"bad":""),
     M.don!=null&&tile("55-day channel",Math.round(M.don*100)+"%",M.don>0.9?"good":M.don<0.1?"bad":"",M.don>1?"breakout":"0% = 55-day low, 100% = high")]],
   ["Momentum",[tile("RSI (14)",F(f.rsi,0),f.rsi==null?"":f.rsi>75||f.rsi<30?"warn":f.rsi>=50?"good":"bad",f.rsi>70?"overbought":f.rsi<30?"oversold":""),
     tile("MACD",f.macdUp==null?"–":f.macdUp?"Above signal":"Below signal",f.macdUp==null?"":f.macdUp?"good":"bad"),
     M.stoch!=null&&tile("Stochastic %K (14)",F(M.stoch,0),M.stoch>80?"warn":M.stoch<20?"warn":"",M.stoch>80?"near 2-week high":M.stoch<20?"near 2-week low":""),
     M.cci!=null&&tile("CCI (20)",F(M.cci,0),M.cci>100?"good":M.cci<-100?"bad":"",M.cci>100?"strong up":M.cci<-100?"strong down":""),
     M.z!=null&&tile("Z-score vs 20-day",F(M.z,2),Math.abs(M.z)>2?"warn":"",Math.abs(M.z)>2?"stretched":""),
     tile("Bollinger position",f.bbPos==null?"–":Math.round(f.bbPos*100)+"%",f.bbPos==null?"":f.bbPos>1||f.bbPos<0?"warn":"",f.bbW!=null?"band width "+P(f.bbW,1).replace("+",""):"")]],
   ["Returns",[tile("1 month",P(f.r1m),C(f.r1m)),tile("3 months",P(f.r3m),C(f.r3m)),tile("6 months",P(f.r6m),C(f.r6m)),tile("1 year",P(f.r1y!=null?f.r1y:M.roc12),C(f.r1y!=null?f.r1y:M.roc12)),
     tile("From 52-week high",P(f.hi52),f.hi52==null?"":f.hi52>-0.05?"good":f.hi52<-0.25?"bad":"warn"),tile("vs Nifty, 3 months",P(f.rs3),C(f.rs3))]],
   ["Volatility and volume",[tile("Volatility (yearly)",f.vol==null?"–":(f.vol*100).toFixed(0)+"%",""),st&&tile("ATR (daily range)",f.atr?"₹"+F(f.atr,1):"–",""),st&&tile("Volume vs normal",f.volx==null?"–":F(f.volx,2)+"×",f.volx>1.5?"good":"")]]];
  const T=G.map(([h,ts])=>{ts=ts.filter(t=>t&&!/<b>–<\/b>/.test(t));return ts.length?`<div class="azsg"><h4>${h}</h4><div class="azg">${ts.join("")}</div></div>`:""}).join("");
  const S=[...f.sigs.map(s=>`<span class="tag good" title="${E(s.name)}">✓ ${E(s.name)}${s.o.hit10!=null?` · beat Nifty ${Math.round(s.o.hit10*100)}% of ${F(s.o.n,0)} times`:""}</span>`),
    ...f.setups.map(s=>`<span class="tag">${E(s)}</span>`),...f.warn.map(s=>`<span class="tag bad">${E(s)}</span>`)];
  return`${T}${S.length?`<div class="row" style="gap:6px;margin-top:10px">${S.join("")}</div>`:`<p class="note" style="margin-top:8px">No setup or tested signal on the last close.</p>`}`}
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


/* ---------- probability and projection (Black-Scholes, lognormal) ---------- */
const Nc=x=>{const t=1/(1+0.2316419*Math.abs(x)),d=0.3989423*Math.exp(-x*x/2),p=d*t*(0.3193815+t*(-0.3565638+t*(1.781478+t*(-1.821256+t*1.330274))));return x>0?1-p:p};
function proj(x,f){const S=f.last;if(!S)return null;const key=x.k==="Nifty 50"?"NIFTY":x.k==="Nifty Bank"?"BANKNIFTY":x.k,bs=((D.quant||{}).bs||{})[key],r=(D.quant||{}).rf||0.07;
  let v=bs&&bs.iv,src="implied, from options";if(!v){const c=closes(x).c.filter(z=>z>0).slice(-127);if(c.length>60){const rr=c.slice(1).map((z,i)=>Math.log(z/c[i])),mu=rr.reduce((a,b)=>a+b,0)/rr.length;v=Math.sqrt(rr.reduce((a,b)=>a+(b-mu)**2,0)/rr.length*252);src="from the last 6 months of prices"}}
  if(!v)return null;const {sup,res}=levels(closes(x).c.filter(z=>z>0),S),sp=sup[0],rs=res[0];
  const H=[["3 months",0.25],["6 months",0.5],["1 year",1]].map(([lab,T])=>{const sd=v*Math.sqrt(T),m=S*Math.exp((r-v*v/2)*T);
    return{lab,T,up:Nc(((r-v*v/2)*T)/sd),lo:m*Math.exp(-sd),hi:m*Math.exp(sd),mid:m,
      hitR:rs?Math.min(1,2*(1-Nc(Math.log(rs.p/S)/sd))):null,hitS:sp?Math.min(1,2*(1-Nc(Math.log(S/sp.p)/sd))):null}});
  const mc=x.kind==="Stock"?((D.quant||{}).mc||{})[x.k]:null;return{v,src,sp,rs,H,mc:mc&&mc.p50!=null?mc:null}}
function summary(x,f){const p=proj(x,f);if(!p)return"";const cur=x.kind==="Index"?"":"₹",h3=p.H[0];
  const t=(k,v,sub,cl)=>`<div class="azt ${cl||""}"><span>${k}</span><b>${v}</b>${sub?`<small>${sub}</small>`:""}</div>`;
  return`<div class="azg" style="margin-top:12px">
   ${t("Next support",p.sp?cur+F(p.sp.p):"none below",p.sp?P(p.sp.p/f.last-1)+" away":"at its lows","")}
   ${t("Next resistance",p.rs?cur+F(p.rs.p):"none above",p.rs?P(p.rs.p/f.last-1)+" away":"at its highs","")}
   ${p.H.map(h=>t("Chance higher in "+h.lab,Math.round(h.up*100)+"%",`likely ${cur}${F(h.lo,0)} – ${cur}${F(h.hi,0)}`,h.up>=0.55?"good":h.up<0.45?"bad":"")).join("")}
   ${p.rs?t("Reach resistance in 3 months",Math.round(h3.hitR*100)+"%","","" ):""}${p.sp?t("Break support in 3 months",Math.round(h3.hitS*100)+"%","",h3.hitS>0.5?"bad":""):""}
   ${p.mc?t("Monte Carlo, 1 month",Math.round((p.mc.p_up||0)*100)+"% up",`${cur}${F(p.mc.p5,0)} – ${cur}${F(p.mc.p95,0)} (90%)`,""):""}
  </div><p class="note" style="margin-top:6px">Chances use Black-Scholes with ${(p.v*100).toFixed(1)}% yearly volatility (${p.src}). "Likely" is the middle two-thirds of outcomes. These are model odds, not forecasts.</p>`}
/* ---------- Analyze ---------- */
let CUR=null,LAST=0;
function head(x,f){const L=f.live,ch=f.prev&&f.last?f.last/f.prev-1:null,H=horizons(x,f);
  return`<div class="row" style="justify-content:space-between;align-items:flex-end;gap:12px"><div><span class="sub">${E(x.kind)}${x.mk&&x.mk.contract?" · "+E(x.mk.contract):""}${f.v&&f.v.ind?" · "+E(f.v.ind):""}</span>
   <h2 style="margin:2px 0 0;font-size:1.5rem">${E(x.k)} <span class="note" style="font-weight:400">${x.name!==x.k?E(x.name):""}</span></h2></div>
   <div style="text-align:right"><b style="font-size:1.6rem">${x.kind==="Index"?"":"₹"}${F(f.last)}</b> <span class="${C(ch)}">${P(ch,2)}</span><br><span class="note">${L?`LIVE ${E(String(L.t||"").slice(11,19))} IST`:"last close"}</span></div></div>
   <div class="row" style="gap:8px;margin-top:10px">${H.map(h=>`<span class="tag ${h.v[1]}">${h.lab}: ${h.v[0]}</span>`).join("")}</div>${why(H)}${summary(x,f)}`}
function why(H){const no=[];H.forEach(h=>h.cks.forEach(c=>{if(c.ok===false&&!no.includes(c.label))no.push(c.label)}));const yes=[];H.forEach(h=>h.cks.forEach(c=>{if(c.ok&&!yes.includes(c.label))yes.push(c.label)}));
  return no.length||yes.length?`<div class="azwhy">${yes.length?`<p><b class="good">Going for it:</b> ${yes.slice(0,4).map(z=>"✓ "+E(z)).join(" &nbsp; ")}</p>`:""}${no.length?`<p><b class="bad">Holding it back:</b> ${no.slice(0,4).map(z=>"✗ "+E(z)).join(" &nbsp; ")}</p>`:""}</div>`:""}
function render(){const x=CUR;if(!x)return;const f=feats(x);LAST=Date.now();
  $("az-head").innerHTML=head(x,f);$("az-chart").innerHTML=chart(x,f);bindChart();$("az-tech").innerHTML=techTiles(x,f)+levelsHtml(x,f);$("az-val").innerHTML=valTiles(x,f);$("az-risk").innerHTML=riskHtml(x);$("az-time").innerHTML=timing(horizons(x,f));
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
