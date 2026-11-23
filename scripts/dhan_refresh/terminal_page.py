"""Build the Aj Trading Terminal artifact.

The terminal is a separate product from the Evidence Desk. It reuses the desk's Screen / Analyze / Proof tabs
(stock picker, value metrics, trade plan, live prices) and adds a Terminal tab first: indices, ETFs and MCX with
live ticks, the one-month 09:30 / 12:30 / 15:00 back-test, screener rules and next session's picks.

  python terminal_page.py --site DIR     writes DIR/index.html and DIR/d/*.json (publish index.html with the d/ files)
  python terminal_page.py --out PATH     the Terminal tab alone (no desk tabs), for a quick look
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
TEMPLATE = Path(__file__).parent / "terminal_template.html"


def _load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def working(root: Path = ROOT, bt: dict | None = None) -> dict:
    """Signals that pass the multi-year back-test for TODAY's kind of market, and the stocks showing them.

    Correction = Nifty below its 200-day average or 5%+ below its 60-day high: then the weak-market test
    ('tested_weak', out-of-sample stats for weak markets) decides; otherwise the rising-market test ('tested').
    Levels follow the back-test's ATR trade: stop 2 ATR, target 3 ATR, exit by day 21.
    """
    import math
    model = _load(root / "docs/tech-model.json") or {}
    today = _load(root / "docs/tech-today.json") or {}
    board = {r["s"]: r for r in (_load(root / "docs/n500.json") or {}).get("rows", [])}
    cfg = _load(root / "config/trading.json") or {}
    nc = (((_load(root / "docs/chart-data.json") or {}).get("s") or {}).get("NIFTY") or {}).get("c") or []
    last = nc[-1] if nc else None
    m200 = sum(nc[-200:]) / 200 if len(nc) >= 200 else None
    hi60 = max(nc[-60:]) if nc else None
    below200 = bool(last and m200 and last < m200)
    dd = (last / hi60 - 1) if last and hi60 else 0.0
    corr = below200 or dd <= -0.05
    side, flag = ("weak", "tested_weak") if corr else ("up", "tested")
    names = model.get("names") or {}
    bts = (bt or {}).get("signals") or {}
    sig = []
    for k, r in (model.get("signals") or {}).items():
        if not r.get(flag):
            continue
        o = (r.get("out") or {}).get(side) or {}
        m = (bts.get(k) or {}).get("09:30") or {}
        sig.append({"k": k, "name": names.get(k, k), "n": o.get("n"), "x10": o.get("x10"), "hit10": o.get("hit10"),
                    "m1": m.get("ex"), "m1n": m.get("n")})
    sig.sort(key=lambda x: -(x["x10"] or 0))
    keys = {x["k"] for x in sig}
    cap, ml = float(cfg.get("capital", 100000)), float(cfg.get("max_loss_per_trade", 1000))
    rows = []
    for sym, t in (today.get("stocks") or {}).items():
        hit = [k for k in (t.get("new") or []) if k in keys]
        b = board.get(sym) or {}
        if not hit or not t.get("atr") or b.get("status") in ("weak", "fade") or not b.get("sid"):
            continue
        c, a = t["c"], t["atr"]
        rows.append({"s": sym, "sid": b["sid"], "sig": [names.get(k, k) for k in hit], "c": c, "stop": round(c - 2 * a, 2),
                     "tgt": round(c + 3 * a, 2), "qty": max(0, min(math.floor(ml / (2 * a)), math.floor(cap / c))),
                     "status": {"lead": "leading", "improve": "improving", "neutral": "neutral"}.get(b.get("status"), b.get("status")),
                     "rank": b.get("rank") or 9999, "best": max((x["x10"] or 0) for x in sig if x["name"] in [names.get(k, k) for k in hit])})
    rows.sort(key=lambda r: (-r["best"], r["rank"]))
    label = ("Correction" if corr else "Rising market")
    why = (f"Nifty is {'below' if below200 else 'above'} its 200-day average and {abs(dd) * 100:.1f}% below its 60-day high, so the terminal uses "
           f"the {'weak-market' if corr else 'rising-market'} back-test (out-of-sample years only). Only signals that passed it are listed, "
           f"best first by average 10-day gain over the Nifty. The last column is the one-month intraday check (desk picks bought at 9:30).")
    return {"label": label, "correction": corr, "why": why, "signals": sig, "stocks": rows[:20], "asof": today.get("asof")}


def _data_js(root: Path) -> dict:
    d = root / "docs/terminal"
    bt = _load(d / "backtest.json")
    if bt:
        bt["trades"] = bt.get("trades", [])[-80:]
    js = lambda o: json.dumps(o, separators=(",", ":")).replace("</", "<\\/")
    return {"BT": js(None), "WK": js(working(root, bt)), "MK": js(_load(d / "markets.json")), "WL": js(_load(d / "watch.json")),
            "META": js({"built": dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M")})}


def build(root: Path = ROOT) -> str:
    """The Terminal tab as a page of its own."""
    t = TEMPLATE.read_text(encoding="utf-8")
    for k, v in _data_js(root).items():
        t = t.replace(f"/*{k}*/null", v, 1)
    return t


def _section(root: Path) -> tuple[str, str, str]:
    """(css, markup, script) of the Terminal tab, namespaced so it can live inside the desk page."""
    t = build(root)
    css = re.search(r"<style>(.*?)</style>", t, re.S).group(1)
    css = re.sub(r":root\{.*?\}\s*@media \(prefers-color-scheme: dark\)\{.*?\}\}\s*:root\[data-theme=\"dark\"\]\{.*?\}\s*", "", css, flags=re.S)
    css = re.sub(r"body\{.*?\}\s*", "", css, count=1, flags=re.S)
    css = (css.replace("var(--amber)", "var(--accent)").replace("var(--chip)", "var(--soft)")
              .replace("var(--f-head)", "var(--sans)").replace("var(--f-body)", "var(--sans)").replace("var(--f-mono)", "var(--mono)"))
    scoped = []
    for rule in re.findall(r"([^{}]+)\{([^{}]*)\}", re.sub(r"@media[^{]*\{((?:[^{}]*\{[^{}]*\})*)\s*\}", "", css)):
        sel = ",".join("#term " + s.strip() for s in rule[0].split(",") if s.strip())
        scoped.append(f"{sel}{{{rule[1]}}}")
    for media, body in re.findall(r"(@media[^{]*)\{((?:[^{}]*\{[^{}]*\})*)\s*\}", css):
        inner = "".join(",".join("#term " + s.strip() for s in r[0].split(",")) + "{" + r[1] + "}"
                        for r in re.findall(r"([^{}]+)\{([^{}]*)\}", body))
        scoped.append(f"{media}{{{inner}}}")
    body = t.split("</style>", 1)[1]
    markup = body.split("<script>", 1)[0]
    script = body.split("<script>", 1)[1].rsplit("</script>", 1)[0]
    markup = re.sub(r'<header class="head">.*?</header>', "", markup, count=1, flags=re.S)
    markup = markup.replace('<div class="wrap">', '<div class="twrap">', 1)
    markup = markup.replace('id="', 'id="tm-')
    script = re.sub(r'/\* theme toggle \*/.*?\}\)\(\);\n', "", script, count=1, flags=re.S)
    script = script.replace('$("', '$("tm-').replace("$(`", "$(`tm-").replace('id="', 'id="tm-').replace("$(\"tm-th-", "$(\"th-")
    script = script.replace('$("tm-"+', '$("tm-"+')
    script = script.replace('$("pop-"+k)', '$("tm-pop-"+k)').replace('$("ex-"+k)', '$("tm-ex-"+k)')
    return "\n".join(scoped) + "\n#term .twrap{display:flex;flex-direction:column;gap:22px}", markup, "(function(){\n" + script + "\n})();"


AZ_HTML = r"""
<section id="az" class="wrap" style="gap:14px" hidden>
  <div class="pnl"><div class="row" style="gap:8px"><input id="az-q" list="az-list" placeholder="Search a stock, index, ETF or MCX (Gold, Silver…)" autocomplete="off" aria-label="Search" style="flex:1;min-width:220px"><datalist id="az-list"></datalist><div class="row" id="az-quick" style="gap:6px"></div></div>
    <p class="note" id="az-empty">Pick something to analyze.</p></div>
  <div id="az-body" hidden style="display:flex;flex-direction:column;gap:14px">
    <div class="pnl" id="az-head"></div>
    <div class="pnl"><h2>Chart</h2><div id="az-chart"></div></div>
    <div class="pnl"><h2>Technical</h2><div id="az-tech"></div></div>
    <div class="pnl"><h2>Value</h2><div id="az-val"></div></div>
    <div class="pnl"><h2>Risk and return</h2><div id="az-risk"></div></div>
    <div class="pnl"><h2>When is it good to buy?</h2><div id="az-time"></div></div>
    <div class="row"><button class="chip" id="az-proof">Show proof</button><span class="note">How the signals were tested</span></div>
  </div>
</section>
"""

AZ_CSS = """
#az-body[hidden]{display:none!important}
.azg{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
.azt{border:1px solid var(--line);border-radius:8px;padding:8px 10px;display:flex;flex-direction:column;gap:2px;min-width:0}
.azt span{color:var(--mute);font-size:12px}.azt b{font-size:1.05rem;color:var(--ink)}.azt small{color:var(--mute);font-size:11.5px}
.azt.good{border-color:var(--up)}.azt.good b{color:var(--up)}.azt.bad{border-color:var(--down)}.azt.bad b{color:var(--down)}.azt.warn b{color:var(--warn)}
.azh{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.azhc{border:1px solid var(--line);border-radius:10px;padding:12px;display:flex;flex-direction:column;gap:4px}
.azhc b{font-size:1.35rem}.azhc small{color:var(--mute)}.azhc ul{margin:6px 0 0;padding:0;list-style:none;font-size:13px;display:flex;flex-direction:column;gap:3px}
.azm{color:var(--mute)}
#az .pnl>h2,#az .pnl h3{font-family:var(--mono);text-transform:uppercase;letter-spacing:.1em;font-size:13px;border-left:3px solid var(--warn);padding-left:8px}
.azt{border-left-width:3px}.azt b{font-family:var(--mono);font-variant-numeric:tabular-nums}.azhc b{font-family:var(--mono)}
.azlv{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,380px),1fr));gap:14px}
#term .mute{background:none}
.azsg{margin-top:10px}.azsg:first-child{margin-top:0}.azsg h4{margin:0 0 6px;font-size:11.5px;color:var(--mute);text-transform:uppercase;letter-spacing:.08em;font-weight:600}
.azwhy{margin-top:10px;font-size:13.5px;line-height:1.45}.azwhy p{margin:2px 0}.azwhy b.good{color:var(--up)}.azwhy b.bad{color:var(--down)}
#az .chip.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
#az-svg{cursor:crosshair}
#term tr.go{cursor:pointer}
"""

AZ_JS = Path(__file__).parent / "terminal_analyze.js"


PORTFOLIO = r"""
<section id="pf" class="wrap" style="gap:14px" hidden>
  <div class="pnl">
    <h2>Your portfolio</h2>
    <p class="note">Pick a stock, type its weight in %, and add it. The verdict uses the desk's tested signals, the value model, the Nifty 500 trend and your caps (one stock up to 10%, one sector up to 25%). Saved in this browser only.</p>
    <div class="row"><select id="pfSym" aria-label="Stock"></select><input id="pfW" type="number" min="0" max="100" step="0.5" placeholder="Weight %" aria-label="Weight in percent" style="max-width:120px"><button class="chip" id="pfAdd">Add</button><button class="chip" id="pfClear">Clear all</button></div>
    <div class="tw"><table id="pfTab"></table></div>
    <div id="pfVerdict"></div>
  </div>
</section>
"""

PF_JS = r"""
(function(){const KEY="aj-pf";let P=[];try{P=JSON.parse(localStorage.getItem(KEY)||"[]")}catch(e){P=[]}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(P))}catch(e){}};
const IXL=(D.ix||[]).slice().sort((a,b)=>a[0]<b[0]?-1:1);
const sel=document.getElementById("pfSym");sel.innerHTML='<option value="">Choose a stock…</option>'+IXL.map(x=>`<option value="${esc(x[0])}">${esc(x[0])} · ${esc(x[1])}</option>`).join("");
const by={};((D.board||{}).rows||[]).forEach(r=>by[r.s]=r);
function info(sym){let tc="–",vc="–",cl="";try{const c=ctx(sym),t=call(c);tc=t.call||"–";cl=t.cl||""}catch(e){}
  const f=((D.nval||{})[sym]||{}).fund||{};vc=f.verdict||((D.vm||{}).today||{})[sym]&&"see Analyze"||"–";
  const r=by[sym]||{};return{tc,cl,vc,ind:r.ind||"Other",r21:r.r21,status:r.status}}
function render(){const tot=P.reduce((a,x)=>a+x.w,0);const rows=P.map(x=>({...x,...info(x.s)}));
  document.getElementById("pfTab").innerHTML=rows.length?`<tr><th>Stock</th><th class="n">Weight</th><th>Technical</th><th>Value</th><th>Sector</th><th class="n">1 month</th><th></th></tr>`+
   rows.map((x,i)=>`<tr><td><button class="link" data-a="${esc(x.s)}">${esc(x.s)}</button></td><td class="n">${x.w.toFixed(1)}%</td><td class="${x.cl}">${esc(x.tc)}</td><td>${esc(String(x.vc))}</td><td>${esc(x.ind)}</td><td class="n ${cls(x.r21)}">${x.r21==null?"–":pc(x.r21,1)}</td><td><button class="link" data-rm="${i}">Remove</button></td></tr>`).join("")
   +`<tr><td><b>Total</b></td><td class="n"><b>${tot.toFixed(1)}%</b></td><td colspan="5"></td></tr>`:'<tr><td class="note">No stocks yet. Choose one above and add it.</td></tr>';
  document.querySelectorAll("#pfTab [data-rm]").forEach(b=>b.onclick=()=>{P.splice(+b.dataset.rm,1);save();render()});
  document.querySelectorAll("#pfTab [data-a]").forEach(b=>b.onclick=()=>{tab("analyze");show(b.dataset.a);window.scrollTo(0,0)});
  const V=document.getElementById("pfVerdict");if(!rows.length){V.innerHTML="";return}
  const sec={};rows.forEach(x=>sec[x.ind]=(sec[x.ind]||0)+x.w);const issues=[],good=[];
  if(Math.abs(tot-100)>0.5)issues.push(`Weights add up to ${tot.toFixed(1)}%, not 100% (${tot<100?(100-tot).toFixed(1)+"% in cash":"over-invested"}).`);
  rows.filter(x=>x.w>10).forEach(x=>issues.push(`${x.s} is ${x.w.toFixed(1)}%, above the 10% single-stock cap.`));
  Object.entries(sec).filter(([k,w])=>w>25).forEach(([k,w])=>issues.push(`${k} is ${w.toFixed(1)}% of the portfolio, above the 25% sector cap.`));
  const bad=rows.filter(x=>x.cl==="bad"),badW=bad.reduce((a,x)=>a+x.w,0);if(bad.length)issues.push(`${badW.toFixed(1)}% sits in stocks the desk rates Avoid or Downtrend: ${bad.map(x=>x.s).join(", ")}.`);
  const exp=rows.filter(x=>/unattractive|expensive|above/i.test(String(x.vc))),expW=exp.reduce((a,x)=>a+x.w,0);if(exp.length)issues.push(`${expW.toFixed(1)}% is in stocks the value model calls expensive: ${exp.map(x=>x.s).join(", ")}.`);
  const gd=rows.filter(x=>x.cl==="good");if(gd.length)good.push(`${gd.reduce((a,x)=>a+x.w,0).toFixed(1)}% has a tested buy signal: ${gd.map(x=>x.s).join(", ")}.`);
  if(rows.length<10)issues.push(`Only ${rows.length} stock${rows.length>1?"s":""}; your target is about 30 for spread.`);
  const r1=rows.filter(x=>x.r21!=null),m=r1.length?r1.reduce((a,x)=>a+x.w*x.r21,0)/r1.reduce((a,x)=>a+x.w,0):null;
  const head=issues.length===0?["Balanced","good"]:issues.length<=2?["Needs a few changes","warn"]:["Needs work","bad"];
  V.innerHTML=`<div class="row" style="margin-top:10px;justify-content:space-between"><b class="${head[1]}" style="font-size:1.4rem">${head[0]}</b>${m!=null?`<span class="note">Weighted 1-month move ${pc(m,1)}</span>`:""}</div><ul>${issues.map(t=>`<li>${esc(t)}</li>`).join("")}${good.map(t=>`<li class="good">${esc(t)}</li>`).join("")}</ul><p class="note">Research software, not advice.</p>`}
document.getElementById("pfAdd").onclick=()=>{const s=sel.value,w=parseFloat(document.getElementById("pfW").value);if(!s||!(w>0))return;
  const i=P.findIndex(x=>x.s===s);if(i>=0)P[i].w=w;else P.push({s,w});save();render();document.getElementById("pfW").value=""};
document.getElementById("pfClear").onclick=()=>{P=[];save();render()};
render();window.pfRender=render})();
"""

ALLSEL_JS = r"""
(function(){const s=document.getElementById("allsel");if(!s)return;let filled=false;
  const fill=()=>{if(filled)return;filled=true;s.innerHTML='<option value="">All NSE stocks ('+(D.ix||[]).length+')…</option>'+(D.ix||[]).slice().sort((a,b)=>a[0]<b[0]?-1:1).map(x=>`<option value="${esc(x[0])}">${esc(x[0])} · ${esc(x[1])}</option>`).join("")};
  s.addEventListener("focus",fill);s.addEventListener("pointerdown",fill);s.onchange=()=>{if(s.value)show(s.value)}})();
"""


def _patch_tabs(html: str) -> str:
    """Tabs: Terminal, Screen, Analyze (with Proof below it), Portfolio. Analyze prices follow the live feed."""
    html = html.replace('<button class="tab" role="tab" data-t="proof" aria-selected="false">Proof</button>',
                        '<button class="tab" role="tab" data-t="pf" aria-selected="false">Portfolio</button>', 1)
    html = html.replace('["term","screener","analyze","plan","proof"].forEach(x=>$(x).hidden=t!==x)',
                        '["term","screener","analyze","plan","proof","pf","az"].forEach(x=>$(x).hidden=!(x==="az"?t==="analyze":x!=="analyze"&&x!=="plan"&&t===x));if(t==="pf"&&window.pfRender)pfRender()', 1)
    html = html.replace('if(t==="proof"&&SHOWN)', 'if((t==="proof"||t==="analyze")&&SHOWN)', 1)
    html = html.replace('["research","proof"].includes(h)?h:"screener"', '["research"].includes(h)?h:h==="proof"?"analyze":h==="pf"||h==="portfolio"?"pf":"screener"', 1)
    html = html.replace('<div class="row" id="quick"></div></div>',
                        '<select id="allsel" aria-label="All NSE stocks" style="max-width:340px"></select><div class="row" id="quick"></div></div>', 1)
    # Analyze headline price: live Dhan price when the feed has it; re-render the open stock at most every 20 s
    html = html.replace("const last=(lf&&lf.last)||t.c||r.last||",
                        "const last=(typeof LIVE!==\"undefined\"&&LIVE.eq[sym]&&LIVE.eq[sym].ltp)||(lf&&lf.last)||t.c||r.last||", 1)
    html = html.replace('<section id="proof"', AZ_HTML + PORTFOLIO + '<section id="proof"', 1)
    html = html.replace("</style>", AZ_CSS + "\n</style>", 1)
    i = html.rfind("</script>")
    return html[:i] + "\n" + PF_JS + "\n" + ALLSEL_JS + "\n" + html[i:]


def build_site(site: Path, root: Path = ROOT) -> dict:
    import desk_page
    site.mkdir(parents=True, exist_ok=True)
    out = site / "index.html"
    info = desk_page.build(out)
    html = out.read_text(encoding="utf-8")
    css, markup, script = _section(root)
    html = html.replace("<title>Evidence Desk</title>", "<title>Aj Trading Terminal</title>", 1)
    html = html.replace("<h1>Evidence Desk</h1>", "<h1>Aj Trading Terminal</h1>", 1)
    html = html.replace('<button class="tab" role="tab" data-t="screener" aria-selected="true">',
                        '<button class="tab" role="tab" data-t="term" aria-selected="true">Terminal</button>'
                        '<button class="tab" role="tab" data-t="screener" aria-selected="false">', 1)
    html = html.replace('<section id="screener" class="wrap" style="gap:10px">',
                        f'<section id="term" class="wrap" style="gap:10px">{markup}</section>\n'
                        '<section id="screener" class="wrap" style="gap:10px" hidden>', 1)
    html = html.replace('["screener","analyze","plan","proof"].forEach(x=>$(x).hidden=t!==x)',
                        '["term","screener","analyze","plan","proof"].forEach(x=>$(x).hidden=t!==x)', 1)
    html = html.replace('const pick=h=>["analyze"', 'const pick=h=>(!h||h==="term"||h==="terminal")?"term":["analyze"', 1)
    html = html.replace("</style>", css + "\n</style>", 1)
    i = html.rfind("</script>")
    html = html[:i + len("</script>")] + "\n<script>\n" + script + "\n</script>" + html[i + len("</script>"):]
    html = _patch_tabs(html)
    j = html.rfind("</body>")
    j = j if j >= 0 else len(html)
    html = html[:j] + "<script>\n" + AZ_JS.read_text(encoding="utf-8").replace("</", "<\\/") + "\n</script>\n" + html[j:]
    for must in ('data-t="term"', 'id="term"', '"term","screener"', 'h==="term"', 'data-t="pf"', 'id="allsel"', 'id="az"', '"pf","az"'):
        if must not in html:
            raise RuntimeError(f"desk page changed shape; could not insert the Terminal tab ({must})")
    out.write_text(html, encoding="utf-8")
    files = {f"d/{f.name}": str(f) for f in sorted((site / "d").glob("*.json"))}
    return {**info, "page": str(out), "files": len(files)}


if __name__ == "__main__":
    if "--site" in sys.argv:
        print(json.dumps(build_site(Path(sys.argv[sys.argv.index("--site") + 1]))))
    else:
        out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else ROOT / "docs/terminal.html"
        out.write_text(build(), encoding="utf-8")
        print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
