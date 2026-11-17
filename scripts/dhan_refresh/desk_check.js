// Checks the built desk in Playwright, serving its files through page.route (no web server needed).
// Usage: node desk_check.js <folder with desk.html and d/> <comma-separated symbols>
// Exits 1 on a console error, a stock that fails to draw, or sideways scroll on any view, at 400px or 1100px.
const {chromium}=require('playwright');const fs=require('fs'),path=require('path');
(async()=>{const b=await chromium.launch();const root=process.argv[2];const syms=process.argv[3].split(',');let fail=0;
for(const [w,name] of [[400,'m'],[1100,'d']]){const p=await b.newPage({viewport:{width:w,height:900}});
await p.route('http://desk.local/**',r=>{const f=path.join(root,new URL(r.request().url()).pathname);fs.existsSync(f)?r.fulfill({body:fs.readFileSync(f),contentType:f.endsWith('.json')?'application/json':'text/html; charset=utf-8'}):r.fulfill({status:404,body:''})});
const errs=[];p.on('pageerror',e=>errs.push(e.message));p.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
const ov=()=>p.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
await p.goto('http://desk.local/desk.html#analyze');await p.waitForTimeout(700);const bad=[];let live=0,gex=0;
for(const s of syms){await p.fill('#q',s);await p.press('#q','Enter');await p.waitForTimeout(450);
 const r=await p.evaluate(()=>({chart:!!document.querySelector('#pchart svg'),ov:document.documentElement.scrollWidth-innerWidth,live:/live/.test(document.querySelector('#sesswhen')?.textContent||''),snap:[...document.querySelectorAll('#flowcards .basis')].some(x=>/snapshot/.test(x.textContent)),gex:!!document.querySelector('#opts svg')}));
 if(!r.chart||r.ov)bad.push(s+JSON.stringify(r));if(r.live&&r.snap)live++;if(r.gex)gex++}
await p.goto('http://desk.local/desk.html#research');await p.waitForTimeout(400);const pre=[];
for(const k of await p.evaluate(()=>[...document.querySelectorAll('#presets [data-pre]')].map(b=>b.dataset.pre))){await p.click(`[data-pre="${k}"]`);await p.waitForTimeout(80);pre.push(k+'='+(await p.evaluate(()=>document.querySelector('#n-research').textContent)).replace(' stocks',''))}
const view={};
for(const t of ['screener','plan','proof']){await p.goto('http://desk.local/desk.html#'+t);await p.waitForTimeout(500);
 const o=await ov();if(o)bad.push('#'+t+' overflow '+o);
 view[t]=await p.evaluate(t=>t==='plan'?document.querySelectorAll('#planT tr[data-s]').length+' rows':t==='proof'?['pf-sig','pf-risk','pf-fx','pf-live'].map(i=>i.slice(3)+':'+(/Not computed yet/.test(document.getElementById(i).textContent)?'none':'ok')).join(','):'ok',t)}
if(view.plan&&!view.plan.startsWith('0')){await p.goto('http://desk.local/desk.html#plan');await p.waitForTimeout(300);await p.click('#planT th button[data-k="5"]');await p.click('#planT tr[data-s]');await p.waitForTimeout(400);
 if(!(await p.evaluate(()=>!document.getElementById('analyze').hidden)))bad.push('plan row did not open Analyze')}
const o=await ov();if(bad.length||errs.length||o)fail=1;
console.log(name,'checked',syms.length,'problems',bad.length,bad.slice(0,5).join(' '),'| live+snapshot',live,'| gamma',gex,'| presets',pre.join(' '),'| views',JSON.stringify(view),'| overflow',o,'| errors',errs.slice(0,3));}
await b.close();process.exitCode=fail})();
