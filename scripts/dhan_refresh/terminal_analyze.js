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
function live(x){const q=window.TLIVE;let a=q&&x.sid!=null&&(q[x.seg]||{})[String(x.sid)];if(a&&a[0]){const R0=((D.rs||{}).stocks||{})[x.k]||{},done=String(window.TLIVE_T||"").slice(0,10)===(D.rs||{}).pcd;return{ltp:a[0],pc:done?(R0.pc||null):(a[4]||null),t:window.TLIVE_T}}
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
document.addEventListener("tlive",()=>{if(CUR&&!$("az").hidden&&Date.now()-LAST>15000)render();sumLive();try{if($("tm-move"))movers()}catch(e){console.error("movers",e)}try{if($("tm-next"))nextView()}catch(e){console.error("next",e)}try{mvLive()}catch(e){console.error("mv",e)}
  document.querySelectorAll("[data-lc]").forEach(el=>{const d=dayChg(el.dataset.lc);if(d.c==null)return;el.textContent=(d.live?F(d.ltp)+" ":"")+P(d.c,1);el.className=d.c>0?"up":d.c<0?"down":""})});
{let s=null;try{s=localStorage.getItem("az-last")}catch(e){}open(s&&find(s)?s:"Nifty 50")}

/* ---------- Terminal summary: what worked, in one place ---------- */
const vchip=h=>h?h.map(z=>`<td class="${z.v[1]}">${z.v[0]==="Good to buy"?"Buy":z.v[0]==="Not enough data"?"–":z.v[0]}</td>`).join(""):"<td></td><td></td><td></td>";
const SL={brk20:"20-day breakout",flag:"Bull flag",reclaim20:"Back above 20-day",os14:"Oversold",os_bounce:"Oversold bounce",st_up:"Supertrend up",trend:"Trend template",vcp:"Tight base",adx:"ADX trend start",rsi2:"RSI(2) dip",accum:"Accumulation",gap:"Gap that holds",bbsq:"Squeeze breakout",dip3:"3 down days",ibs:"Weak close in uptrend",reclaim200:"Back above 200-day",pullback:"Pullback",don55:"55-day breakout",hi52v:"52-week high on volume",volbreak:"Volume breakout",nr7:"Tight inside day",rsnew:"RS line new high",qdrop10:"Dip in a proven stock",qdrop:"Dip in a proven stock",qdd:"Dip in a proven stock",macd0:"MACD turns up"};
const STK=Object.keys(RS).filter(k=>INS[k]);
function dayChg(s){const x=INS[s],L=x&&live(x);const r=RS[s]||{},t=TODAY[s]||{},pc=(L&&L.pc)||r.last||t.c;if(L&&pc)return{ltp:L.ltp,c:L.ltp/pc-1,live:true};return{ltp:r.last||t.c||null,c:null,live:false}}
function picks(){return STK.map(s=>({s,r:RS[s]})).filter(z=>(z.r.setups||[]).length&&(z.r.turnover_cr||0)>=10&&!(z.r.warn||[]).length)
  .sort((a,b)=>(b.r.score||0)-(a.r.score||0)||(b.r.rs3||0)-(a.r.rs3||0)).slice(0,15)}
const lvc=(s)=>`<td class="n" data-lv="${E(s)}"></td><td class="n" data-lc="${E(s)}"></td>`;
function sum(){const el=$("tm-sum");if(!el)return;const R=WK.stocks||[],PK=picks();
  const lt=Object.keys(VMT).map(s=>{const on=(VMT[s].on||[]).filter(k=>VTEST.includes(k));if(on.length<2||!INS[s])return null;const h=window.azHorizons(s);return h&&h[2].v[1]==="good"?{s,on,h,r:RS[s]||{}}:null})
    .filter(Boolean).sort((a,b)=>b.on.length-a.on.length||((a.r.pe_sec||9)-(b.r.pe_sec||9))).slice(0,12);
  const up200=STK.filter(k=>RS[k].vs200>0).length;
  el.innerHTML=`<div id="tm-mview" class="tm-ide"></div><div class="tm-stk" id="tm-stkw"><div class="head"><h2>Screener · Nifty 500</h2><span class="pill ${WK.correction?"fail":"pass"}">${E(WK.label||"–")}</span></div>
   <div class="sumbar" id="tm-breadth"><span><b>${PK.length}</b> setups today</span><span><b>${R.length}</b> buy now</span><span><b>${up200}</b> of ${STK.length} above 200-day</span><span id="tm-adv"></span></div>
   <div class="sgrid">
   <div class="spnl wide"><h3>Screener picks</h3><div class="scroll"><table><tr><th>Stock</th><th>Setup</th><th class="n">Live</th><th class="n">Day</th><th class="n">3M vs Nifty</th><th class="n">RSI</th><th>Value</th><th>3M</th><th>6M</th><th>1Y</th></tr>
    ${PK.length?PK.map(z=>`<tr class="go" data-mk="${E(z.s)}"><td><button class="lnk" data-mk="${E(z.s)}">${E(z.s)}</button></td><td class="sm">${[...new Set(z.r.setups.map(k=>SL[k]).filter(Boolean))].slice(0,2).map(E).join(", ")}</td>${lvc(z.s)}<td class="n ${z.r.rs3>0?"up":"down"}">${z.r.rs3==null?"–":P(z.r.rs3,0)}</td><td class="n">${z.r.rsi==null?"–":F(z.r.rsi,0)}</td><td class="sm">${E(z.r.value||"–")}</td>${vchip(window.azHorizons(z.s))}</tr>`).join(""):`<tr><td class="note">No setup on the last close.</td></tr>`}</table></div></div>
   <div class="spnl"><h3>Buy now</h3><div class="scroll"><table><tr><th>Stock</th><th class="n">Live</th><th class="n">Day</th><th class="n">Stop</th><th class="n">Target</th><th class="n">Qty</th></tr>
    ${R.length?R.map(r=>`<tr class="go" data-mk="${E(r.s)}"><td><button class="lnk" data-mk="${E(r.s)}">${E(r.s)}</button></td>${lvc(r.s)}<td class="n down">${F(r.stop)}</td><td class="n up">${F(r.tgt)}</td><td class="n">${r.qty}</td></tr>`).join(""):`<tr><td class="note">No stock has a working signal today.</td></tr>`}</table></div></div>

   <div class="spnl"><h3>Top gainers, live</h3><div class="scroll"><table id="tm-gain"></table></div></div>
   <div class="spnl"><h3>Top losers, live</h3><div class="scroll"><table id="tm-lose"></table></div></div>
   </div>
   <div id="tm-lowrisk"></div>
   <div id="tm-works"></div>
   <div class="head" style="margin-top:6px"><h2>Every screen at a glance</h2></div><p class="note">Each card says why its stocks are there. Stocks that already ran (25%+ in a month, RSI 80+ or flagged overextended) are left out, so the cards point at what can still move. In a rising market the back-test shows strength tends to continue, so fresh highs stay in. Names turn green or red with today's live move.</p>
   <div class="eyeg" id="tm-eye"></div>
   <p class="note">Tap any name to analyze it. Back-tests and proof live in the desk journal.</p></div>`;
  try{mview();mvLive()}catch(e){console.error("mview",e)}
  try{lowrisk()}catch(e){console.error("lowrisk",e)}
  setTimeout(()=>{try{nextView()}catch(e){console.error("next",e)}},0)
  /* index first: market view and ideas above the markets board; the board and the ticker strip belong to the Terminal half */
  try{const tw=document.querySelector("#term .twrap"),mv=$("tm-mview"),mk=$("tm-mk");const mp=mk&&mk.closest("section");
    if(mp)mp.classList.add("tm-idx");el.classList.add("tm-stk");const st=$("tm-strip");if(st)st.classList.add("tm-idx");
    if(tw&&mv&&mp)tw.insertBefore(mv,mp)}catch(e){console.error("layout",e)}
  /* Stocks tab: decision cards first; number tables folded away (ADARSH 26 Nov: fewer numbers, click to drill in) */
  try{const w=$("tm-stkw"),g=w&&w.querySelector(".sgrid");if(w&&g){const d=document.createElement("details");d.className="tm-tables";
    d.innerHTML='<summary>Tables: screener picks, buy now, live gainers and losers</summary>';d.appendChild(g);w.appendChild(d);
    const r=document.getElementById("research");if(r){const d2=document.createElement("details");d2.className="tm-tables";d2.innerHTML='<summary>Full Nifty 500 screener (filters and presets)</summary>';w.appendChild(d2);setTimeout(()=>d2.appendChild(r),0)}}}catch(e){console.error("fold",e)}
  try{works()}catch(e){console.error("works",e)}
  try{eye()}catch(e){console.error("eye",e)}
  try{movers();bestStocks();setTimeout(()=>{try{picksTerm();restructure()}catch(e){console.error("best",e)}try{news()}catch(e){console.error("news",e)}try{pages()}catch(e){console.error("pages",e)}},0)}catch(e){console.error("focus",e)}
  sumLive()}
/* the calmer-half stock list from market_view.py, on the Stocks tab; labelled by its own out-of-sample verdict */
/* Terminal tab: what is likely next, in four tiles, then how the desk trades (ADARSH 27 Nov: forward-looking, decisive) */
function nextView(){const host=document.querySelector("#term .twrap");if(!host)return;const old=$("tm-next");const V0=window.MVIEW||{},Y=window.PLAY||{},M=window.MACRO||{},K=V0.desk||{};
  /* live: Nifty's 3-month and 200-day figures and the VIX ranges move with today's prices */
  const IX=(MK.groups||{}).Indices||[],nr=IX.find(r=>r.k==="Nifty 50"),vr=IX.find(r=>/VIX/.test(r.name)),nq=nr&&mkChg(nr),vq=vr&&mkChg(vr);
  const nk=nq&&nr.last&&nq.last?nq.last/nr.last:1,vk=vq&&vr.last&&vq.last?vq.last/vr.last:1,isL=!!(window.TLIVE&&(nk!==1||vk!==1));
  const adj=x=>x==null?x:(1+x)*nk-1,V=Object.assign({},V0,{r63:adj(V0.r63!=null?V0.r63:V0.nifty_r63),vs200:adj(V0.vs200!=null?V0.vs200:V0.nifty_vs200)});
  if(V0.vix)V.vix=Object.assign({},V0.vix,{vix:V0.vix.vix*vk,day_pts:Math.round(V0.vix.day_pts*vk*nk),month_pts:Math.round(V0.vix.month_pts*vk*nk)});
  const pc=(x,d=1)=>x==null?"–":(x>0?"+":"")+(x*100).toFixed(d)+"%";const vx=V.vix,mv=(M.view||{}),q=mv.pct;
  const val=q==null?null:q<0.33?["Expensive","down","Don't chase; add only on dips."]:q>0.67?["Cheap","up","Accumulate quality on weakness."]:["Fair","","Be selective."];
  const fav=(Y.use||[]).slice(0,2).map(x=>x.name),bad=(Y.avoid||[]).slice(0,1).map(x=>x.name);
  const t=[];
  t.push(`<div><h4>Market type</h4><b class="big">${E(String(V.label||V.regime_text||Y.label||"–").split(":")[0])}</b><p>Nifty ${pc(V.r63!=null?V.r63:V.nifty_r63)} over 3 months, ${pc(V.vs200!=null?V.vs200:V.nifty_vs200)} vs its 200-day.</p></div>`);
  if(vx)t.push(`<div><h4>Expected range</h4><b class="big">±${vx.day_pts} pts tomorrow</b><p>±${vx.month_pts} pts over a month (India VIX ${F(vx.vix,1)}). ${Math.round((vx.p_move15||0)*100)}% chance of a 1.5%+ day.</p></div>`);
  if(val)t.push(`<div><h4>Valuation</h4><b class="big ${val[1]}">${val[0]}</b><p>${E(val[2])} Foreign investors ${mv.fii_sum>0?"buying":"selling"} lately.</p></div>`);
  {const R=setupRule(),tp=techPicks(12),dv=(window.DAMV||[]);t.push(`<div><h4>Favourable now</h4><b class="big up">${R.use.length?E(R.use.map(k=>SETUPS[k].split(" (")[0]).join(", ")):"Strongest trends"}</b><p>${tp.length} technical setups with a positive edge (Technical tab)${dv.length?`, ${dv.length} value stock${dv.length>1?"s":""} at a discount (Value tab)`:""}.</p></div>`)}
  if(fav.length||bad.length)t.push(`<div><h4>What tends to work in this market</h4><p>${fav.length?"Leaning: "+E(fav.join("; "))+".":""} ${bad.length?"Avoid: "+E(bad[0])+".":""}</p><p class="sm">Leads from the nightly back-test, not proven. Picks below.</p></div>`);
  const ph=(K.process&&K.process.length?K.process:["Start from a market belief or published research","Test it on data it was never fitted on","Size from the Rs 5,000 loss limit and volatility, never from conviction","Every trade has a stop, an exit date and a hedge","No edge today means no trade: sitting out is a position"]);
  const d=old||document.createElement("div");d.id="tm-next";d.className="tm-idx";const wasOpen=old&&old.querySelector("details")&&old.querySelector("details").open;
  d.innerHTML=`<div class="head"><h2>What's likely next</h2><span class="sm">${isL?`live ${E(String(window.TLIVE_T).slice(11,19))} IST · models from close of ${E(D_(V0.asof))}`:`close of ${E(D_(V0.asof))}`}</span></div><div class="nx">${t.join("")}</div>
   <details style="margin-top:10px"><summary><b>How we trade (the desk's philosophy)</b></summary><ol class="phil">${ph.map(x=>`<li>${E(x)}</li>`).join("")}</ol></details>
   `;
  if(old){if(wasOpen)d.querySelector("details").open=true;return}
  const mk=$("tm-mk"),sec=mk&&mk.closest("section");if(sec&&sec.nextSibling)host.insertBefore(d,sec.nextSibling);else host.appendChild(d)}
function lowrisk(){const el=$("tm-lowrisk"),V=window.MVIEW;if(!el||!V||!(V.screen||[]).length)return;const ok=V.screen_v==="HOLDS";
  const pc=(x,d=1)=>x==null?"–":(x>0?"+":"")+(x*100).toFixed(d)+"%",sh=x=>x==null?"–":Math.round(x*100)+"%";
  el.innerHTML=`<div class="spnl wide"><h3>Low risk, high return ${ok?'<span class="pill pass">Tested: holds</span>':'<span class="pill warn">Watch, not proven</span>'}</h3>
   <p class="sm">Calmer half of the Nifty 500, best 12-month return per unit of risk. Back-test: ${pc(V.screen_m,2)} a month vs Nifty after charges, right ${sh(V.screen_hit)} of months since ${E(D_(V.oos_from))}${ok?"":", not significant"}.</p>
   <div class="eyen">${V.screen.slice(0,12).map(r=>`<button class="chip" data-mk="${E(r.s)}">${E(r.s)}</button>`).join("")}</div></div>`}
/* ---------- Market view (market_view.py): verdict first, Roast Room 26 Nov: no forecast the data cannot back ---------- */
function mview(){const el=$("tm-mview"),V=window.MVIEW;if(!el||!V)return;
  const pc=(x,d=1)=>x==null?"–":(x>0?"+":"")+(x*100).toFixed(d)+"%",sh=x=>x==null?"–":Math.round(x*100)+"%";
  const tag={HOLDS:"pass",UNPROVEN:"warn",FAILS:"fail"},hz=h=>h===5?"5 days":h===126?"6 months":"1 month";
  const vx=V.vix,held=V.beliefs.filter(b=>b.v==="HOLDS").length,ok=V.screen_v==="HOLDS";
  const bl=V.beliefs.map(b=>`<li><span class="pill ${tag[b.v]||""}">${E(b.v==="HOLDS"?"Holds":b.v==="FAILS"?"Fails":"Unproven")}</span><span>${E(b.t)}<small> · ${pc(b.m,2)} ${b.u?E(b.u):"vs Nifty per "+hz(b.h)} · right ${sh(b.hit)} · ${b.mo} months tested${b.note?" · "+E(b.note):""}</small></span></li>`).join("");
  const idv=o=>{const L=o.live||[];if(o.k==="nifty_condor"&&L[0]){const c=L[0];return`Today: sell ${F(c.sp,0)} put and ${F(c.sc,0)} call, buy ${F(c.lp,0)} put and ${F(c.lc,0)} call. Credit about ${F(c.credit,0)} pts, worst case ${F(c.max_loss,0)} pts.`}
    if(!L.length)return o.k==="bank_pair_flat"?"Not active: the market is not flat today.":"Not active: no spread is stretched 2 standard deviations today.";
    return"Active now: "+L.map(x=>`${x.side>0?"buy":"sell"} <button class="lnk" data-mk="${E(x.k)}">${E(x.k)}</button>, ${x.side>0?"sell":"buy"} ${F(x.beta,2)}x Nifty${x.z!=null?` (gap ${F(x.z,1)} sd)`:""}`).join("; ")};
  const take=o=>o.v==="HOLDS"?"Trade it when it fires.":o.v==="FAILS"?`Skip: it lost ${pc(o.oos.raw_mean,2)} a trade over the last 3 years.`:(o.oos.raw_mean||0)>0?`Watch only: ${pc(o.oos.raw_mean,2)} a trade, not enough proof for money.`:"Skip: no edge.";
  const idc=(V.ideas||[]).map(o=>`<details class="spnl idea"><summary><b>${E(o.t)}</b><br><span class="pill ${tag[o.v]||""}">${E(o.v==="HOLDS"?"Trade":o.v==="FAILS"?"Skip":"Watch")}</span> ${E(take(o))}</summary>
    <p class="sm">${E(o.p)} ${E(o.hedge||"")}</p>${o.v==="HOLDS"?`<p><b>${idv(o)}</b></p>`:`<p class="sm">${o.v==="FAILS"?"Fired today, not traded (failed the test)":"Fired today, watch only (not proven)"}: ${idv(o).replace(/^(Active now|Today): /,"")}</p>`}
    <p class="sm">Back-test since ${E(D_(V.oos_from))}: ${pc(o.oos.raw_mean,2)} a trade${o.k==="nifty_condor"?" on the capped loss":""}, right ${sh(o.oos.hit)} of ${o.oos.n} trades (before: ${pc(o.is.raw_mean,2)}, right ${sh(o.is.hit)} of ${o.is.n}). ${E(o.sizing||"")} ${E(o.note||"")}</p></details>`).join("");
  const TM=V.timing||[],rules=[...new Set(TM.map(o=>o.rule))];
  const tcell=o=>!o?"<td>–</td>":`<td class="sm"><span class="pill ${o.v==="HOLDS"?"pass":o.safer?"warn":o.v==="FAILS"?"fail":""}">${o.v==="HOLDS"?"Holds":o.safer?"Safer":o.v==="FAILS"?"Fails":"Unproven"}</span> ${pc(o.s&&o.s.ret,0)} vs ${pc(o.h&&o.h.ret,0)}/yr · worst ${pc(o.s&&o.s.maxdd,0)} vs ${pc(o.h&&o.h.maxdd,0)}${o.on?" · <b>in now</b>":""}</td>`;
  const tmw=TM.filter(o=>o.v==="HOLDS").length,tmp=TM.filter(o=>o.v!=="FAILS"&&(o.m||0)>0).map(o=>o.idx+": "+o.rule.replace("_"," "));
  const tm=TM.length?`<details class="spnl wide"><summary><b>Classic index rules:</b> ${tmw?tmw+" beat holding the index":"none beats simply holding the index"}${tmp.length?"; only "+E(tmp.join(", "))+" lean positive":""}.</summary><h3>Classic index rules, tested since ${E(D_(V.oos_from))}</h3>
    <div class="scroll"><table><tr><th>Rule</th>${[...new Set(TM.map(o=>o.idx))].map(i=>`<th>${E(i)}</th>`).join("")}</tr>
    ${rules.map(r=>{const xs=TM.filter(o=>o.rule===r);return`<tr><td class="sm"><b>${E(xs[0].t)}</b><br><small>${E(xs[0].src||"")}</small></td>${[...new Set(TM.map(o=>o.idx))].map(i=>tcell(xs.find(o=>o.idx===i))).join("")}</tr>`}).join("")}</table></div>
    <p class="note">Rule vs simply holding the same index, last 3 years: return a year and worst fall. Holds = beat holding after the many-ideas correction; Safer = smaller worst fall with at least the same Sharpe, before and after the cut, without being proven to earn more. Out of the market = T-bill rate.</p></details>`:"";
  const WK=V.weekly,wr=WK?WK.rows||[]:[],wpos=wr.filter(o=>o.v!=="FAILS"&&(o.oos||0)>0);
  const wk=WK?`<details class="spnl wide"><summary><b>Weekly candles, ${E(D_(WK.from))} to ${E(D_(WK.asof))}:</b> ${WK.held.length?WK.held.length+" of "+wr.length+" ideas hold":"none of "+wr.length+" ideas holds"}${wpos.length?"; "+wpos.length+" lean positive, not proven":""}.</summary><h3>Every idea re-run on weekly candles (${F(WK.weeks,0)} weeks)</h3>
    <div class="scroll"><table><tr><th>Idea</th><th>Verdict</th><th>Before</th><th>Last 3 years</th><th>Right</th></tr>
    ${wr.map(o=>`<tr><td class="sm">${E(o.t)}${o.live?" · <b>fires now</b>":""}</td><td><span class="pill ${tag[o.v]||""}">${E(o.v==="HOLDS"?"Holds":o.v==="FAILS"?"Fails":"Unproven")}</span></td><td>${pc(o.is,2)}</td><td>${pc(o.oos,2)}</td><td>${sh(o.hit)} of ${o.m} mo</td></tr>`).join("")}</table></div>
    <p class="note">Same ideas, same many-ideas correction, on weekly bars (1 month = 4 weeks, 200 days = 40 weeks). Average per case, in the idea's own direction. Weekly market type: ${E(WK.regime||"n/a")}.</p></details>`:"";
  const pp=V.paper,ppl=pp?["nifty_condor","nifty_condor_tight"].filter(k=>pp[k]).map(k=>`${k==="nifty_condor"?"Wide":"Narrow"} condor: ${pp[k].closed} closed, ${pp[k].won} won, ${F(pp[k].pts,0)} pts${pp[k].open?`, open since ${E(D_(pp[k].open.d))}`:""}`).join(" · "):"";
  const DK=V.desk,cv={high:"pass",medium:"warn",low:""},rs=x=>"₹"+F(x,0);
  const memo=m=>`<div class="spnl idea"><h3>${E(m.etf||m.idx)} <span class="pill ${cv[m.conv]}">${m.conv==="low"?"Watch":m.conv+" conviction"}</span></h3>
    <p class="sm"><b>Thesis.</b> ${E(m.why)}${m.src?` <small>(${E(m.src)})</small>`:""}</p>
    <p class="sm"><b>Evidence.</b> Last 3 years, never used to fit it: ${pc(m.ev.raw_mean,2)} a month vs holding, right ${sh(m.ev.hit)} of ${m.ev.months} months${m.safer?", with a smaller worst fall":""}.</p>
    ${m.conv==="low"?`<p class="sm"><b>Watch:</b> evidence not strong enough to size yet.</p>`:`<p><b>Trade.</b> Buy about ${rs(m.notional)} of ${E(m.etf||m.idx)} near ${F(m.px,0)} (index). Stop ${F(m.stop,0)} (−${(m.stop_pct*100).toFixed(1)}%), risk ${rs(m.risk_rs)}.</p>
    <p class="sm"><b>Exit.</b> ${E(m.exit)} ${m.hedge&&m.hedge.text?"<b>Hedge.</b> "+E(m.hedge.text):""} ${m.note?E(m.note):""}</p>`}</div>`;
  const dk=DK?`<div class="head"><h2>Index trade memos</h2></div>
    ${(DK.next||[]).length?`<p class="sm"><b>Next trigger:</b> ${DK.next.map(E).join(" Or: ")}</p>`:""}
    ${DK.memos.length?`<div class="sgrid">${DK.memos.map(memo).join("")}</div>`:""}
    <p class="note">Sizing: worst case ${rs(DK.limit_rs)} a trade on ${rs(DK.capital)}. Built every evening from the data: thesis, test on unseen data, size from volatility, stop and exit before entry, correlated trades share one budget.</p>`:"";
  const rk=V.risk.length?`<details class="spnl wide"><summary><b>Risk and return, last 3 years</b> <span class="sm">Sharpe, worst fall, beta and correlation to the Nifty for every index and NSE factor index</span></summary>
    <div class="scroll"><table><tr><th>Index</th><th class="n">Return/yr</th><th class="n">Volatility</th><th class="n">Sharpe</th><th class="n">Worst fall</th><th class="n">Beta</th><th class="n">Corr</th></tr>
    ${V.risk.map(r=>`<tr><td>${E(r.k)}</td><td class="n ${r.ret>0?"up":"down"}">${pc(r.ret)}</td><td class="n">${sh(r.vol)}</td><td class="n"><b>${r.sharpe==null?"–":F(r.sharpe,2)}</b></td><td class="n down">${pc(r.maxdd,0)}</td><td class="n">${r.beta==null?"–":F(r.beta,2)}</td><td class="n">${r.corr==null?"–":F(r.corr,2)}</td></tr>`).join("")}</table></div>
    <p class="note">Sharpe uses a 6.5% risk-free rate. Next-session direction from market type was also tested: right ${sh(V.next&&V.next.accuracy)} of days vs ${sh(V.next&&V.next.always_up)} for always saying up, so no next-day call is shown. Sector rotation by market type: ${pc(V.rot&&V.rot.mean,2)} a month, right ${sh(V.rot&&V.rot.hit)}.</p></details>`:"";
  el.innerHTML=`<div class="head" style="margin-top:6px"><h2>Market view</h2></div>
   <div id="mv-live"></div>
   ${dk}
   ${idc?`<div class="head"><h2>Trading ideas</h2><span class="sm">hedged, index legs only, tested on data they were never fitted on</span></div><div class="sgrid">${idc}</div>`:""}
   ${ppl?`<p class="sm">Paper record since ${E(D_(pp.since))} (no hindsight): ${ppl}</p>`:""}
   <div class="sgrid">${tm}${wk}
   <details class="spnl wide"><summary><b>Popular beliefs, tested</b> <span class="sm">${held} of ${V.beliefs.length} proven</span></summary><h3>Popular beliefs, tested on data since ${E(D_(V.oos_from))} they were never fitted on</h3><ul class="wk">${bl}</ul></details>
   ${rk}</div>`}
/* ---------- What works in this market (desk journal's indicator back-test) ---------- */
function works(){const el=$("tm-works"),Y=window.PLAY,L=window.LAB;if(!el)return;
  if(Y&&Y.type){const nm={rising:"Rising",falling:"Falling",flat:"Flat / slow",turning:"Turning"}[Y.type]||Y.type;
    const row=x=>`<li><b class="${x.abn>0?"up":"down"}">${P(x.abn,1)}</b><span>${E(x.name)}<small> · ${E(x.grade)} · ${x.n} cases${(Y.fired[x.k]||Y.warned[x.k]||[]).length?` · fired today on ${(Y.fired[x.k]||Y.warned[x.k]).length}`:""}</small></span></li>`;
    el.innerHTML=`<div class="mtype"><b>${E(nm)} market</b> since ${E(D_(Y.since))} <span class="sm">${E(Y.label||"")}</span></div>
     <div class="sgrid"><div class="spnl"><h3>Back-test favours now</h3><ul class="wk">${Y.use.map(row).join("")||'<li class="note">Nothing has a clear edge in this market type. Fewer trades is the honest answer.</li>'}</ul></div>
     <div class="spnl"><h3>Back-test warns against now</h3><ul class="wk">${Y.avoid.map(row).join("")||'<li class="note">No reliable warnings in this market type.</li>'}</ul></div></div>
     <p class="note">From the desk journal's nightly back-test of ${E(String(Y.tested||""))} indicators, judged only on past ${E(nm.toLowerCase())} markets. Leaning = a lead, not proven. Details in the journal.</p>`;return}
  if(!L||!L.best)return;
  const row=x=>`<li><b class="${x.abn>0?"up":"down"}">${P(x.abn,1)}</b><span>${E(x.name)}<small> · ${x.n} cases · ${E(x.verdict)}</small></span></li>`;
  el.innerHTML=`<div class="sgrid"><div class="spnl"><h3>What has worked in ${E(L.market)} markets</h3><ul class="wk">${L.best.map(row).join("")||'<li class="note">None.</li>'}</ul></div>
   <div class="spnl"><h3>What has done worst in ${E(L.market)} markets</h3><ul class="wk">${L.worst.map(row).join("")||'<li class="note">None.</li>'}</ul></div></div>
   <p class="note">Extra 21-day return over the average stock, last 3 years. ${E(L.note)}</p>`}
function D_(d){if(!d)return"–";const m=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];const x=String(d).split("-");return x.length<3?d:`${+x[2]} ${m[+x[1]-1]} ${x[0]}`}
/* each screen and the lab indicators closest to it: the card shows their back-test in today's market type */
const TWIN={"dd-rising":["supertrend_up","macd_up","ema20_50","x_sma50","adx_x20"],"dd-swing":["vol2_up","accum","obv_x20","cmf_x10"],
  "dd-dips":["drop5d_10","dip3","rsi2_10_up","below50_15"],"dd-movers":["gap_up3","roc10_10","vol2_up"],
  flow:["vol2_up","cmf_x10","obv_x20"],osq:["rsi14_x30","mfi_20","bb_below"],lead:["rs_hi","rs3m_10","xs_mom6","xs_mom12"],
  downco:["xs_mom12_low","drop5d_10","below50_15"],downmkt:["xs_mom12_low","drop5d_10","below50_15"],setup:["don55","hi52_vol","bb_squeeze_up","flag"]};
function twinEv(id){const Y=window.PLAY;if(!Y||!Y.ev)return null;const xs=(TWIN[id]||[]).map(k=>Y.ev[k]).filter(Boolean);if(!xs.length)return null;
  const n=xs.reduce((a,x)=>a+x[1],0);return{abn:xs.reduce((a,x)=>a+x[0]*x[1],0)/n,n}}
/* ---------- Bird's-eye view of every screener section ---------- */
const ranAlready=s=>{const r=(typeof RS!=="undefined"&&RS[s])||{};return (r.r1m||0)>0.25||(r.rsi||0)>=80||(r.warn||[]).includes("extended")};
function eye(){const el=$("tm-eye");if(!el)return;const cards=[],Y=window.PLAY,mt=Y&&Y.type?({rising:"rising",falling:"falling",flat:"flat",turning:"turning"}[Y.type]||Y.type):"";
  const badge=ev=>ev?`<p class="sm bt ${ev.abn>0.002?"up":ev.abn<-0.002?"down":""}">Back-test in ${E(mt)} markets: ${P(ev.abn,1)} vs the average stock (${ev.n} cases)</p>`:"";
  const card=(t,n,names,d,ev,cls)=>cards.push({ev,h:`<div class="eye${cls?" "+cls:""}"><h4>${E(t)} <span>${E(String(n))}</span></h4><div class="eyen">${names.length?names.map(s=>`<button class="chip" data-mk="${E(s)}">${E(s)}</button>`).join(""):'<span class="sm">none today</span>'}</div>${d?`<p class="sm">${E(d)}</p>`:""}${badge(ev)}</div>`});
  const liquid=s=>(typeof RS==="undefined"||!RS[s]||(RS[s].turnover_cr||0)>=10)&&!ranAlready(s);
  /* 1. the playbook's own picks: stocks where an indicator the back-test favours in this market type fired on the last session */
  if(Y&&Y.type){const sc={};Y.use.forEach(x=>(Y.fired[x.k]||[]).forEach(s=>{if(!liquid(s))return;(sc[s]=sc[s]||{s,v:0,k:[]}).v+=x.abn;sc[s].k.push(x.name)}));
    const top=Object.values(sc).sort((a,b)=>b.v-a.v);
    const w=new Set();Y.avoid.forEach(x=>(Y.warned[x.k]||[]).forEach(s=>w.add(s)));
    cards.push({ev:{abn:9},h:`<div class="eye pb"><h4>Back-test picks for a ${E(mt)} market <span>${top.length} stocks</span></h4><div class="eyen">${top.length?top.slice(0,8).map(z=>`<button class="chip" data-mk="${E(z.s)}" title="${E(z.k.join("; "))}">${E(z.s)}</button>`).join(""):'<span class="sm">none fired on the last session</span>'}</div><p class="sm">Fired on the last session: ${E([...new Set(top.slice(0,8).flatMap(z=>z.k))].slice(0,3).join("; ")||"–")}. Turnover Rs 10 Cr+ a day.${w.size?` ${w.size} stocks tripped a warning, so check before buying them.`:""}</p></div>`})}
  [["dd-rising","Basis: a desk signal that passed its own back-test turned bullish on the last close."],["dd-dips","Basis: a stock that beat the Nifty by 20%+ over 2 years has pulled back; buy-the-dip setups."],["dd-movers","Basis: the biggest moves of the last session and the likely reason (news, results, sector)."],["dd-swing","Basis: order flow and auction levels (VWAP, value area) from the last session."]].forEach(([id,d])=>{const x=document.getElementById(id);if(!x)return;
    const names=[...new Set([...x.querySelectorAll("[data-s]")].map(b=>b.dataset.s))].filter(s=>!ranAlready(s)).slice(0,6),cnt=(x.querySelector("[id^=n-]")||{}).textContent||names.length;
    card(((x.querySelector(".ddt")||{}).textContent||id).trim(),cnt,names,d,twinEv(id))});
  if(typeof PRESETS!=="undefined"&&typeof RS!=="undefined")PRESETS.filter(p=>["best","setup","flow","osq","lead","downco","downmkt"].includes(p[0])).forEach(p=>{let rows=Object.entries(RS).map(([s,x])=>Object.assign({s},x)).filter(x=>{try{return p[3](x)&&(x.turnover_cr||0)>=10&&!ranAlready(x.s)}catch(e){return false}});
    try{rows.sort(p[4])}catch(e){}card(p[1],rows.length+" stocks",rows.slice(0,6).map(x=>x.s),p[2],twinEv(p[0]),p[0]==="best"?"best":"")});
  /* order: playbook picks, then Top picks, then screens by their back-test in today's market type (no evidence last) */
  const key=c=>c.ev?c.ev.abn:-1;
  const head=cards.filter(c=>c.ev&&c.ev.abn===9),best=cards.filter(c=>c.h.includes("eye best")),rest=cards.filter(c=>!head.includes(c)&&!best.includes(c)).sort((a,b)=>key(b)-key(a));
  el.innerHTML=[...head,...best,...rest].map(c=>c.h).join("")}

/* ---------- 27 Nov (ADARSH): Terminal = one movers section + what's next + best value + best swing; Stocks = best of each screen, visual ---------- */
function cl60(s){const k=(window.SPK||{})[s],r=RS[s]||{};if(k&&r.last)return k.map(v=>v*r.last/1000);const x=INS[s];return x?closes(x).c:[]}
function spark(s,n=60,w=120,h=34){const c0=cl60(s);if(!c0.length)return"";const c=c0.filter(v=>v!=null&&isFinite(v)).slice(-n);if(c.length<5)return"";
  const lo=Math.min(...c),hi=Math.max(...c),r=hi-lo||1,pts=c.map((v,i)=>`${(i/(c.length-1)*w).toFixed(1)},${(h-2-(v-lo)/r*(h-4)).toFixed(1)}`).join(" ");
  return `<svg class="spk" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="${c[c.length-1]>=c[0]?"var(--up,#3fb68b)":"var(--down,#e5534b)"}" stroke-width="1.6"/></svg>`}
/* swing plan in the trader-entry/exit style: stop under the 20-day low (max 8% away), target 2R, size from the Rs 5,000 max loss */
function plan(s){const c=cl60(s).filter(v=>v!=null&&isFinite(v));if(c.length<25)return null;const last=dayChg(s).ltp||c[c.length-1];
  const lo20=Math.min(...c.slice(-20)),stop=Math.max(lo20*0.995,last*0.92);if(!(stop<last))return null;const R=last-stop,ml=((window.CFG||{}).max_loss_per_trade)||5000;
  return{last,stop,tgt:last+2*R,qty:Math.floor(ml/R),risk:R/last}}
function swingScore(s){const r=RS[s];if(!r||(r.turnover_cr||0)<10||ranAlready(s)||(r.warn||[]).length)return null;const Y=window.PLAY||{};
  let sc=0;const why=[];(Y.use||[]).forEach(x=>{if(((Y.fired||{})[x.k]||[]).includes(s)){sc+=x.abn*100;why.push(x.name)}});
  if(Object.entries(Y.warned||{}).some(([k,v])=>(Y.avoid||[]).some(a=>a.k===k)&&v.includes(s)))return null;
  if((r.setups||[]).length){sc+=1+0.3*(r.score||0);why.push(...r.setups.map(k=>SL[k]).filter(Boolean).slice(0,1))}
  if((r.vs200||0)>0){sc+=0.5}else sc-=1;if((r.rs3||0)>0){sc+=0.5;why.push("beating the Nifty over 3 months")}
  if(r.rsi!=null&&(r.rsi<45||r.rsi>72))sc-=0.7;if(!why.length)return null;return{s,sc,why:[...new Set(why)].slice(0,3)}}
function bestSwing(n=5,pool){return (pool||STK).map(swingScore).filter(Boolean).sort((a,b)=>b.sc-a.sc).slice(0,n)}
function pcard(z,kind){const p=plan(z.s),d=dayChg(z.s),r=RS[z.s]||{};
  return `<button class="pc" data-mk="${E(z.s)}"><div class="pct"><b>${E(z.s)}</b><span data-lc="${E(z.s)}" class="${d.c>0?"up":d.c<0?"down":""}">${d.c==null?"":(d.live?F(d.ltp)+" ":"")+P(d.c,1)}</span></div>${spark(z.s)}
   <p class="sm">${E(kind==="v"?z.line:z.why.join(" · "))}</p>${kind==="v"?"":p?`<div class="pl"><span>Buy ~${F(p.last)}</span><span class="down">Stop ${F(p.stop)}</span><span class="up">Target ${F(p.tgt)}</span><span>Qty ${p.qty}</span></div>`:""}</button>`}
/* live day change for a board row: live price vs the feed's previous close (a[4]), else the last close baked into the page */
/* the nightly market view with Nifty and VIX figures moved to today's live prices */
function LVIEW(){const V0=window.MVIEW||{},IX=(MK.groups||{}).Indices||[],nr=IX.find(r=>r.k==="Nifty 50"),vr=IX.find(r=>/VIX/.test(r.name)),nq=nr&&mkChg(nr),vq=vr&&mkChg(vr);
  const nk=window.TLIVE&&nq&&nr.last&&nq.last?nq.last/nr.last:1,vk=window.TLIVE&&vq&&vr.last&&vq.last?vq.last/vr.last:1,adj=x=>x==null?x:(1+x)*nk-1;
  const V=Object.assign({},V0,{r63:adj(V0.r63!=null?V0.r63:V0.nifty_r63),vs200:adj(V0.vs200!=null?V0.vs200:V0.nifty_vs200),live:nk!==1||vk!==1});
  if(V0.vix)V.vix=Object.assign({},V0.vix,{vix:V0.vix.vix*vk,day_pts:Math.round(V0.vix.day_pts*vk*nk),month_pts:Math.round(V0.vix.month_pts*vk*nk)});return V}
function mvLive(){const el=$("mv-live");if(!el)return;const V=LVIEW(),vx=V.vix,pc=(x,d=1)=>x==null?"–":(x>0?"+":"")+(x*100).toFixed(d)+"%",sh=x=>x==null?"–":Math.round(x*100)+"%";
  el.innerHTML=`<div class="mtype"><b>${E(V.label||"–")}</b> <span class="sm">Nifty ${pc(V.r63)} over 3 months, ${pc(V.vs200)} vs 200-day · ${V.live?`live ${E(String(window.TLIVE_T).slice(11,19))} IST`:`close of ${E(D_(V.asof))}`}</span></div>
   ${vx?`<div class="sumbar"><span>Tomorrow's range (India VIX ${F(vx.vix,1)}): <b>±${vx.day_pts} pts</b></span><span>Next month: <b>±${vx.month_pts} pts</b></span><span>Chance of a 1.5%+ day: <b>${sh(vx.p_move15)}</b></span><span class="sm">range held ${sh(vx.hit1)} of ${vx.days} days (68% expected)</span></div>`:""}`}
window.ajDayChg=(...a)=>dayChg(...a);window.ajMkChg=(...a)=>mkChg(...a);
function mkChg(r){const x=INS[r.k],L=x&&live(x);if(L&&L.ltp){const pc=L.pc||r.last;if(pc)return{last:L.ltp,c:L.ltp/pc-1}}return{last:r.last,c:r.chg}}
function movers(){const tw=document.querySelector("#term .twrap");if(!tw)return;const old=$("tm-move");const all=[];
  Object.entries(MK.groups||{}).forEach(([g,rows])=>rows.forEach(r=>{if(/VIX|Liquid/i.test(r.name))return;const c=mkChg(r).c;if(c!=null)all.push({k:r.k,n:r.name,g,c,m:r.r21})}));
  all.sort((a,b)=>b.c-a.c);const up=all.filter(x=>x.c>0).slice(0,5),dn=all.filter(x=>x.c<0).slice(-5).reverse(),mx=Math.max(...all.map(x=>Math.abs(x.c)),0.005);
  const bar=x=>`<button class="dbar" data-mk="${E(x.k)}"><span class="dl">${E(x.n)}</span><span class="dt"><i class="${x.c>0?"gd":"bd"}" style="${x.c>0?"left":"right"}:50%;width:${Math.min(50,Math.abs(x.c)/mx*50)}%"></i></span><span class="dv ${x.c>0?"up":"down"}">${P(x.c,2)}</span></button>`;
  const vx=(MK.groups.Indices||[]).find(r=>/VIX/.test(r.name)),n50=(MK.groups.Indices||[]).find(r=>r.k==="Nifty 50");
  const nq=n50&&mkChg(n50),vq=vx&&mkChg(vx);
  const d=old||document.createElement("div");d.id="tm-move";d.className="pnl tm-idx";
  d.innerHTML=`<div class="head"><h2>Markets today</h2><span class="sm">${nq&&nq.last?`Nifty ${F(nq.last)} <b class="${nq.c>0?"up":"down"}">${P(nq.c,2)}</b>`:""}${vq&&vq.last?` · VIX ${F(vq.last,1)}`:""}</span></div>
   <h4 class="sm">Rose the most</h4><div class="dbars">${up.map(bar).join("")||'<p class="sm">none</p>'}</div><h4 class="sm">Fell the most</h4><div class="dbars">${dn.map(bar).join("")||'<p class="sm">none</p>'}</div>
   <p class="sm">Indices, ETFs and MCX together; tap any to analyze.</p>`;
  if(old)return;tw.insertBefore(d,tw.firstChild);
  /* the full board and the ticker strip fold away */
  const mk=$("tm-mk"),sec=mk&&mk.closest("section");if(sec){const f=document.createElement("details");f.className="tm-idx tm-tables";f.innerHTML="<summary>All indices, ETFs and MCX</summary>";sec.parentNode.insertBefore(f,sec);f.appendChild(sec)}
  const st=$("tm-strip");if(st)st.style.display="none"}

/* ---------- Technicals from the trader skills (ADARSH 27 Nov): trader-scanner rules on daily closes, a trader-exit style plan,
   trader-timemachine replays (10,000 paths from the stock's own last 120 daily moves, plus every past time the rule fired),
   trader-risk sizing (Rs 5,000 max loss, never more than the capital), Indian delivery charges ~0.25% round trip ---------- */
const SETUPS={breakout_20d:"20-day closing-high breakout",bull_flag:"Bull flag",reclaim_ma20:"Reclaimed the 20-day average",oversold_bounce:"Oversold bounce (RSI<30, closed up)"};
function rsiW(c,i,n=14){if(i<n)return null;let g=0,l=0;for(let k=i-n+1;k<=i;k++){const d=c[k]-c[k-1];if(d>0)g+=d;else l-=d}return l===0?100:100-100/(1+g/l)}
function scanAt(c,i){const o=[];if(i<25)return o;const last=c[i];
  if(last>Math.max(...c.slice(i-20,i)))o.push("breakout_20d");
  const b=c.slice(i-4,i+1),hi=Math.max(...b),lo=Math.min(...b);if(c[i-5]/c[i-15]-1>0.10&&(hi-lo)/lo<0.05)o.push("bull_flag");
  const m=k=>c.slice(k-19,k+1).reduce((a,v)=>a+v,0)/20;if(c[i-1]<m(i-1)&&last>m(i))o.push("reclaim_ma20");
  const r1=rsiW(c,i-1);if(r1!=null&&r1<30&&last>c[i-1])o.push("oversold_bounce");return o}
function planFor(c,i,k){const e=c[i];let atr=0;for(let j=i-13;j<=i;j++)atr+=Math.abs(c[j]-c[j-1]);atr/=14;
  let st=k==="bull_flag"?Math.min(...c.slice(i-4,i+1))-0.25*atr:k==="reclaim_ma20"?c.slice(i-19,i+1).reduce((a,v)=>a+v,0)/20-0.5*atr:k==="oversold_bounce"?Math.min(...c.slice(i-5,i+1))-0.25*atr:e-1.5*atr;
  st=Math.min(st,e-0.5*atr);if(st<=0||st<e*0.85)st=e*0.92;const R=e-st;return{e,st,tg:e+2*R,R}}
let SEED=19;const rnd=()=>{SEED=(SEED*1664525+1013904223)>>>0;return SEED/4294967296};
function machine(c,pl,days=15,N=10000){const r=[];for(let k=c.length-120;k<c.length;k++)if(k>0&&c[k-1])r.push(c[k]/c[k-1]);const ch=0.0025*pl.e/pl.R;
  let tf=0,sf=0,sumR=0;SEED=19;for(let n=0;n<N;n++){let p=pl.e,out=null;for(let d=0;d<days;d++){p*=r[Math.floor(rnd()*r.length)];if(p<=pl.st){out=-1;break}if(p>=pl.tg){out=2;break}}
    if(out===2)tf++;else if(out===-1)sf++;sumR+=(out==null?(p-pl.e)/pl.R:out)-ch}
  return{tf:tf/N,sf:sf/N,nn:1-(tf+sf)/N,avgR:sumR/N}}
function history(c,k,days=15){let w=0,l=0,o=0;for(let i=25;i<c.length-1;i++){if(!scanAt(c,i).includes(k))continue;const pl=planFor(c,i,k);let out=0;
  for(let j=i+1;j<=Math.min(c.length-1,i+days);j++){if(c[j]<=pl.st){out=-1;break}if(c[j]>=pl.tg){out=1;break}}out>0?w++:out<0?l++:o++;i+=2}return{w,l,o}}
function techPicks(n=6){const cap=((window.CFG||{}).capital)||500000,ml=((window.CFG||{}).max_loss_per_trade)||5000,res=[];
  STK.forEach(s=>{const r=RS[s]||{};if((r.turnover_cr||0)<10||(r.warn||[]).length||ranAlready(s))return;const c=cl60(s).filter(v=>v>0);if(c.length<60)return;
    const i=c.length-1;scanAt(c,i).forEach(k=>{if(k!=="oversold_bounce"&&(r.vs200||0)<0)return;const pl=planFor(c,i,k),last=dayChg(s).ltp||c[i];res.push({s,k,pl,c,last,volx:r.volx})})});
  res.forEach(z=>{z.m=machine(z.c,z.pl);z.h=history(z.c,z.k);const sc=z.pl.e/z.last||1;z.qty=Math.max(0,Math.min(Math.floor(ml/z.pl.R),Math.floor(cap/z.pl.e)))});
  return res.filter(z=>z.m.avgR>0&&z.h.l<=z.h.w+1).sort((a,b)=>b.m.avgR-a.m.avgR).slice(0,n)}
function tcard(z){const d=dayChg(z.s),m=z.m,w=x=>Math.round(x*100);
  return `<button class="pc" data-mk="${E(z.s)}"><div class="pct"><b>${E(z.s)}</b><span data-lc="${E(z.s)}" class="${d.c>0?"up":d.c<0?"down":""}">${d.c==null?"":(d.live?F(d.ltp)+" ":"")+P(d.c,1)}</span></div>
   <p class="sm"><b>${E(SETUPS[z.k])}</b>${z.volx?` · volume ${F(z.volx,1)}× normal`:""}</p>${spark(z.s)}
   <div class="pl"><span>Entry ${F(z.pl.e)}</span><span class="down">Stop ${F(z.pl.st)}</span><span class="up">Target ${F(z.pl.tg)}</span><span>Qty ${z.qty}</span></div>
   <div class="odds" title="10,000 replays over 15 sessions"><i class="gd" style="width:${w(m.tf)}%"></i><i class="bd" style="width:${w(m.sf)}%"></i><i style="width:${w(m.nn)}%"></i></div>
   <p class="sm">Time Machine: target first <b class="up">${w(m.tf)}%</b>, stop first <b class="down">${w(m.sf)}%</b>, neither ${w(m.nn)}% · average <b>${m.avgR>0?"+":""}${m.avgR.toFixed(2)}R</b> after charges · past fires in 6 months: ${z.h.w} hit target, ${z.h.l} stopped${z.h.o?`, ${z.h.o} neither`:""}</p></button>`}
function picksTerm(){const nx=$("tm-next");if(!nx||$("tm-best"))return;const sw=techPicks(6),V=(window.DAMV||[]).slice(0,4);
  const d=document.createElement("div");d.id="tm-best";d.className="tm-idx";
  d.innerHTML=`<div class="head"><h2>Selling at a discount (value)</h2><span class="sm">Damodaran tests · 1–3 years</span></div><div class="pcg">${V.length?V.map(z=>pcard(z,"v")).join(""):'<p class="note">No stock passes the value tests today: the market is not cheap.</p>'}</div>
   <div class="head"><h2>Best breakouts and setups (technical)</h2><span class="sm">up to 15 sessions</span></div><div class="pcg">${sw.length?sw.map(tcard).join(""):'<p class="note">No setup has a positive Time Machine edge today. Sitting out is a position.</p>'}</div>
   <p class="sm">Rules from the trader skills on daily closes: 20-day closing-high breakout, bull flag (10%+ run then a tight 5-day range), reclaim of the 20-day average, oversold bounce. Breakouts, flags and reclaims only above the 200-day. Stop under the setup (flag low, 20-day average, or 1.5× daily range), target 2× the risk, quantity from the Rs 5,000 max loss. Time Machine replays the next 15 sessions 10,000 times from the stock's own last 120 daily moves, minus ~0.25% delivery charges; only setups with a positive average and a past record no worse than one extra stop-out are shown, best first. Replays reuse recent drift, so a stock that has been rising looks better than it may be; the "past fires" line is the real record.</p>`;
  nx.parentNode.insertBefore(d,nx.nextSibling)}
function bestStocks(){const w=$("tm-stkw");if(!w||$("tm-bestk"))return;const used=new Set(),rows=[];
  const add=(t,pool)=>{const z=bestSwing(8,pool).find(z=>!used.has(z.s));if(z){used.add(z.s);rows.push([t,z])}};
  const Y=window.PLAY||{};add("Back-test picks",[...new Set((Y.use||[]).flatMap(x=>(Y.fired||{})[x.k]||[]))]);
  if(typeof PRESETS!=="undefined")PRESETS.filter(p=>["best","setup","lead","osq","flow"].includes(p[0])).forEach(p=>add(p[1],STK.filter(s=>{try{return p[3](Object.assign({s},RS[s]))}catch(e){return false}})));
  const d=document.createElement("div");d.id="tm-bestk";
  d.innerHTML=`<div class="head"><h2>Best stock from each screen</h2><span class="sm">forward-looking, already-run names left out</span></div><div class="pcg">${rows.map(([t,z])=>`<div class="pcw"><h4 class="sm">${E(t)}</h4>${pcard(z)}</div>`).join("")||'<p class="note">Nothing qualifies today.</p>'}</div>`;
  w.insertBefore(d,w.querySelector(".head").nextSibling)}

/* 27 Nov (ADARSH): tabs = Terminal, News, Analyze, Portfolio. Terminal holds everything; each section opens to its full detail. */
function restructure(){const tw=document.querySelector("#term .twrap"),best=$("tm-best");if(!tw||!best||$("sec-ide"))return;
  document.querySelectorAll('.tab[data-t="ide"],.tab[data-t="stk"]').forEach(b=>b.style.display="none");
  const vb=document.querySelector('.tab[data-t="screener"]');if(vb)vb.textContent="News";
  const mk=(id,title,inner)=>{const d=document.createElement("details");d.className="sec";d.id=id;d.innerHTML=`<summary><h2>${title}</h2></summary>`;if(inner){inner.classList.remove("tm-stk","tm-ide");d.appendChild(inner)}return d};
  const K=(window.MVIEW||{}).desk||{};
  const ide=mk("sec-ide","Index trade ideas and their tests",$("tm-mview"));
  const tech=mk("sec-tech","Technicals: every screen",$("tm-stkw")),val=mk("sec-val","Value: Damodaran detail and macro",$("vm"));
  const nx=$("tm-next");if(nx)nx.parentNode.insertBefore(ide,nx.nextSibling);
  const h=best.querySelectorAll(".head"),g=best.querySelectorAll(".pcg");
  if(g[0])g[0].parentNode.insertBefore(val,g[0].nextSibling);if(g[1])g[1].parentNode.insertBefore(tech,g[1].nextSibling);
  if(h[1])best.insertBefore(h[1],h[0]);if(g[1])best.insertBefore(g[1],h[0]);if(tech)best.insertBefore(tech,h[0]);const nt=best.querySelector(":scope>p.sm");if(nt&&g[1])best.insertBefore(nt,g[1].nextSibling);   /* technicals first, value second */
  if(/^#(stk|stocks|ide|ideas)$/.test(location.hash)){try{history.replaceState(null,"","#term")}catch(e){}$("term").classList.remove("stk","ide")}}
function news(){const sc=document.getElementById("screener"),N=window.NEWS||{};if(!sc||$("newsx"))return;const C=N.cats||{},it=N.items||[];
  const box=document.createElement("div");box.id="newsx";box.className="pnl";sc.prepend(box);
  const eff=c=>{const x=C[c];if(!x||x.d1==null)return`<span class="sm">Not enough past cases of this kind yet.</span>`;
    const lean=x.d1>0?"up":"down";return x.moves?`<b class="${lean}">Moves the price: ${P(x.d1,1)} vs the Nifty next day</b> on average, ${P(x.d5,1)} over 5 days (${x.days} news days, up ${Math.round(x.d1_up*100)}% of the time).`
      :`<span>No reliable direction: next day ${P(x.d1,1)} vs the Nifty on average, typical move ±${(x.d1_abs*100).toFixed(1)}% (${x.days} news days).</span>`};
  const tech=s=>{const r=RS[s]||{},d=dayChg(s),z=swingScore(s);const tr=r.vs200==null?"":r.vs200>0?"uptrend (above 200-day)":"downtrend (below 200-day)";
    return [d.c!=null?`today <b class="${d.c>0?"up":"down"}">${P(d.c,1)}</b>`:"",tr,r.rsi!=null?"RSI "+F(r.rsi,0):"",z?"<b class=\"up\">swing setup</b>":""].filter(Boolean).join(" · ")};
  const kinds=Object.entries(C).filter(([k,x])=>x.d1!=null).sort((a,b)=>b[1].d1-a[1].d1),mx=Math.max(...kinds.map(([k,x])=>Math.abs(x.d1)),0.005);
  const rows=(all)=>it.filter(z=>all||z[3]!=="Routine filing").slice(0,40).map(([s,t,ti,c])=>`<button class="ni" data-mk="${E(s)}"><div><b>${E(s)}</b><span class="sm">${E(t)} · ${E(c)}</span></div><div>${E(ti)}</div><div class="eff">${eff(c)}</div><div class="eff sm">${tech(s)}</div></button>`).join("");
  box.innerHTML=`<div class="head"><h2>News</h2><span class="sm">NSE announcements, Nifty 500 · ${E(N.asof||"")}</span></div>
   <p class="note">Each item shows how the same kind of announcement moved stocks over the last year (Dhan closes, return minus the Nifty's, after-market news counted next day), then the stock's own technicals. "Moves the price" only when the effect is consistent across 30+ separate news days.</p>
   ${kinds.length?`<h4 class="sm">Average next-day move by kind of news</h4><div class="dbars">${kinds.map(([k,x])=>`<div class="dbar" style="opacity:${x.moves?1:0.55}"><span class="dl">${E(k)}</span><span class="dt"><i class="${x.d1>0?"gd":"bd"}" style="${x.d1>0?"left":"right"}:50%;width:${Math.min(50,Math.abs(x.d1)/mx*50)}%"></i></span><span class="dv ${x.d1>0?"up":"down"}">${P(x.d1,1)}</span></div>`).join("")}</div><p class="sm">Faded bars are not reliable yet. Price history ${E(N.from||"")} to ${E(N.to||"")}; ${N.archived||0} announcements archived so far, back-filling a year over the next few nights.</p>`:""}
   <div id="news-list">${rows(false)||'<p class="note">No announcements yet: they arrive with the nightly refresh.</p>'}</div>
   <label class="sm"><input type="checkbox" id="news-all"> show routine filings too</label>`;
  const a=$("news-all");if(a)a.onchange=()=>{$("news-list").innerHTML=rows(a.checked)};
  box.addEventListener("click",e=>{const b=e.target.closest("[data-mk]");if(b&&window.azGo){e.stopPropagation();azGo(b.dataset.mk)}})}

/* which setup to use in which market (ADARSH 27 Nov): the lab twin's out-of-sample 21-day return vs the average stock, per market type */
SETUPS.rsi2_dip="RSI(2) under 5 (deep dip)";SETUPS.momentum70="RSI(14) crosses above 70 (momentum)";
function setupRule(){const Y=window.PLAY||{},S=Y.setups||{},mt=Y.type||"rising",use=[],skip=[];
  Object.keys(S).forEach(k=>{const v=S[k][mt]||[0,0];(v[0]>=0.002&&v[1]>=60?use:skip).push(k)});use.sort((a,b)=>S[b][mt][0]-S[a][mt][0]);return{mt,use,skip,S}}
const _scanAt=scanAt;scanAt=function(c,i){const o=_scanAt(c,i);if(i<25)return o;const r2=(()=>{let g=0,l=0;for(let k=i-1;k<=i;k++){const d=c[k]-c[k-1];if(d>0)g+=d;else l-=d}return l===0?100:100-100/(1+g/l)})();
  if(r2<5)o.push("rsi2_dip");const a=rsiW(c,i),b=rsiW(c,i-1);if(a!=null&&b!=null&&b<70&&a>=70)o.push("momentum70");return o};
let TP=null;const _techPicks=techPicks;techPicks=function(n){if(!TP){const R=setupRule();const all=_techPicks(60);
  TP=all.filter(z=>R.use.includes(z.k)||(!R.S[z.k]&&z.h.w>z.h.l)).concat(all.filter(z=>!R.use.includes(z.k)&&R.S[z.k]&&z.m.avgR>0.5&&z.h.w>z.h.l))}return TP.slice(0,n)};
function pages(){const tw=document.querySelector("#term .twrap");if(!tw||$("pg-term"))return;
  const pg={};["term","tech","val","news"].forEach(k=>{const d=document.createElement("div");d.id="pg-"+k;d.className="twrap";d.style.display=k==="term"?"":"none";pg[k]=d});
  const R=setupRule(),S=R.S,TY=["rising","flat","turning","falling"],pc=x=>(x>0?"+":"")+(x*100).toFixed(1)+"%";
  const rows=Object.keys(S).map(k=>`<tr><td>${E(SETUPS[k]||k)}</td>${TY.map(t=>{const v=S[k][t];return `<td class="n ${v[0]>=0.002?"g":v[0]<=-0.002?"b":""}${t===R.mt?" on":""}">${v[1]>=60?pc(v[0]):"–"}</td>`}).join("")}<td>${R.use.includes(k)?'<b class="up">Use now</b>':'<span class="sm">Skip now</span>'}</td></tr>`).join("");
  const tp=techPicks(12);
  pg.tech.innerHTML=`<div class="panel"><div class="head"><h2>Which setup to use now</h2><span class="sm">market: <b>${E(R.mt)}</b></span></div>
   <div class="scroll"><table class="rt"><tr><th>Setup</th>${TY.map(t=>`<th class="n">${t}</th>`).join("")}<th></th></tr>${rows}</table></div>
   <p class="sm">Return over the next 21 sessions vs the average Nifty 500 stock, last 3 years only (out of sample), from the nightly back-test of ${E(String((window.PLAY||{}).tested||78))} indicators on Dhan data. A setup is used when it beat the average stock by 0.2%+ in today's kind of market over 60+ cases. Bull flags have no lab test yet, so they need their own past record to be positive.</p></div>
   <div class="head"><h2>Best setups now</h2><span class="sm">Time Machine odds · up to 15 sessions</span></div><div class="pcg">${tp.length?tp.map(tcard).join(""):'<p class="note">Setups that suit this market have not fired on the last close; the strongest trends are in the screens below.</p>'}</div>
   <p class="sm">Scanner rules from the trader skills on daily closes. Entry at the last close, stop under the setup, target 2× the risk, quantity from the Rs 5,000 max loss. Time Machine: 10,000 replays of 15 sessions from the stock's own last 120 daily moves, minus ~0.25% delivery charges; "past fires" is the real record on that stock over 6 months.</p>`;
  const st=$("sec-tech");if(st){st.open=false;pg.tech.appendChild(st)}
  const vm=$("vm");if(vm){const vs=$("sec-val");pg.val.appendChild(vm);if(vs)vs.remove()}
  const nw=$("newsx");if(nw)pg.news.appendChild(nw);
  const best=$("tm-best");if(best)best.remove();
  const fav=document.createElement("div");fav.id="tm-fav";const dv=(window.DAMV||[]).slice(0,2);
  fav.innerHTML=`<div class="head"><h2>Favourable now</h2><span class="sm">tap a card to analyze</span></div><div class="pcg">${tp.slice(0,3).map(tcard).join("")}${dv.map(z=>pcard(z,"v")).join("")}</div>`;
  [...tw.children].forEach(x=>pg.term.appendChild(x));const nx=$("tm-next");if(nx)nx.parentNode.insertBefore(fav,nx.nextSibling);
  ["term","tech","val","news"].forEach(k=>tw.appendChild(pg[k]));
  /* four tabs: Terminal, Technical, Value, News; Analyze opens from any name */
  const bar=document.querySelector(".tabs");document.querySelectorAll(".tabs .tab[data-t]").forEach(b=>b.style.display="none");
  const names={term:"Terminal",tech:"Technical",val:"Value",news:"News"},btn={};
  Object.entries(names).forEach(([k,n])=>{const b=document.createElement("button");b.className="tab";b.textContent=n;b.setAttribute("aria-selected",k==="term"?"true":"false");btn[k]=b;bar.appendChild(b);
    b.onclick=()=>{try{tab("term")}catch(e){}Object.entries(pg).forEach(([j,d])=>d.style.display=j===k?"":"none");Object.entries(btn).forEach(([j,x])=>x.setAttribute("aria-selected",j===k?"true":"false"));
      document.querySelectorAll(".tabs .tab[data-t]").forEach(x=>x.setAttribute("aria-selected","false"));try{history.replaceState(null,"","#"+k)}catch(e){}window.scrollTo(0,0)}});
  const h=location.hash.slice(1),go={tech:"tech",technical:"tech",stk:"tech",stocks:"tech",val:"val",value:"val",screener:"val",news:"news",term:"term",ide:"term"}[h];if(go&&btn[go])btn[go].click()}
function sumLive(){document.querySelectorAll("#tm-eye .chip[data-mk]").forEach(b=>{const d=dayChg(b.dataset.mk);b.classList.toggle("cu",d.c>0);b.classList.toggle("cd",d.c<0);if(d.c!=null)b.title=(d.c>0?"+":"")+(d.c*100).toFixed(2)+"% today"});document.querySelectorAll("#tm-sum [data-lv]").forEach(td=>{const d=dayChg(td.dataset.lv);td.textContent=d.ltp==null?"–":F(d.ltp)});
  document.querySelectorAll("#tm-sum [data-lc]").forEach(td=>{const d=dayChg(td.dataset.lc);td.textContent=d.c==null?"–":P(d.c,2);td.className="n "+(d.c>0?"up":d.c<0?"down":"")});
  const L=STK.map(s=>({s,...dayChg(s)})).filter(z=>z.c!=null);const g=$("tm-gain"),l=$("tm-lose"),ad=$("tm-adv");
  if(ad)ad.innerHTML=L.length?`<b class="up">${L.filter(z=>z.c>0).length}</b> up · <b class="down">${L.filter(z=>z.c<0).length}</b> down, live`:"";
  const rows=a=>a.length?`<tr><th>Stock</th><th class="n">Live</th><th class="n">Day</th><th>Setup</th></tr>`+a.map(z=>`<tr class="go" data-mk="${E(z.s)}"><td><button class="lnk" data-mk="${E(z.s)}">${E(z.s)}</button></td><td class="n">${F(z.ltp)}</td><td class="n ${z.c>0?"up":"down"}">${P(z.c,2)}</td><td class="sm">${E(((RS[z.s]||{}).setups||[]).slice(0,1).map(k=>SL[k]||k).join("")||"")}</td></tr>`).join(""):`<tr><td class="note">Waiting for live prices (market hours).</td></tr>`;
  L.sort((a,b)=>b.c-a.c);if(g)g.innerHTML=rows(L.slice(0,6));if(l)l.innerHTML=rows(L.slice(-6).reverse().filter(z=>z.c<0))}
try{sum()}catch(e){console.error("sum",e)}
/* the Nifty 500 screener (all presets and filters) sits on the Terminal tab, above the at-a-glance cards */
try{const r=document.getElementById("research"),t=document.getElementById("tm-eye");if(r&&t)t.parentNode.insertBefore(r,t.previousElementSibling)}catch(e){console.error("move screener",e)}
})();
