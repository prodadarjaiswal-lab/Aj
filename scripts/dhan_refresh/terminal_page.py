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
        t = t.replace(f"/*{k}*/null", f"/*{k}*/{v}/*{k}*/", 1)   # end markers: page_feed.py swaps in newer data
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
#term .sumbar{display:flex;flex-wrap:wrap;gap:6px 18px;font:12.5px var(--mono);color:var(--mute);border-block:1px solid var(--line);padding:6px 0}
#term .sumbar b{color:var(--ink);font-weight:600}#term .sumbar b.up{color:var(--up)}#term .sumbar b.down{color:var(--down)}
#term .sgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:12px}
#term .spnl{border:1px solid var(--line);border-radius:4px;padding:10px;min-width:0;background:var(--panel)}
#term .spnl.wide{grid-column:1/-1}
#term .spnl h3{margin:0 0 6px;font:600 12px var(--mono);letter-spacing:.1em;text-transform:uppercase;border-left:3px solid var(--warn);padding-left:8px;color:var(--ink)}
#term td.sm,#term .sm{font-size:12px;color:var(--mute);white-space:normal}
#term td,#term th{padding:4px 6px}
#term .twrap{gap:12px}
#term section.panel{padding:12px}
#thbtn{min-width:40px;padding-inline:10px}
#term .mute{background:none}
.azsg{margin-top:10px}.azsg:first-child{margin-top:0}.azsg h4{margin:0 0 6px;font-size:11.5px;color:var(--mute);text-transform:uppercase;letter-spacing:.08em;font-weight:600}
.azwhy{margin-top:10px;font-size:13.5px;line-height:1.45}.azwhy p{margin:2px 0}.azwhy b.good{color:var(--up)}.azwhy b.bad{color:var(--down)}
#az .chip.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
#az-svg{cursor:crosshair}
#term tr.go{cursor:pointer}
"""

# A clean terminal (ADARSH, 26 Nov 2026): back-test proof, "missing: survives the many-signals test" notes, scoreboards and
# track records are hidden here and live in the desk journal (journal/JOURNAL.md, built by journal.py) instead.
CLEAN_CSS = """
#tm-proof,#az-body .row:has(#az-proof),
#screener #deskSum .vr,#screener #deskSum .miss,#screener #deskSum details,
#screener p.note[id^="b-"],#dd-track,#dd-board,#dd-fresh,#dd-quant,#dd-jr,
#deskSum,#screener #dd-rising,#screener #dd-swing,#screener #dd-dips,#screener #dd-movers,#screener #dd-rsum,
#screener .pnl:has(#n-mkts){display:none!important}
#term #research{margin-top:4px}
#vm .verdict{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:baseline;margin:4px 0 8px}#vm .verdict b{font-size:1.6rem}
#vm .good{color:var(--up)}#vm .bad{color:var(--down)}#vm .warn{color:var(--warn)}#vm ul.why{margin:4px 0;padding-left:18px;display:flex;flex-direction:column;gap:3px;font-size:13.5px}
@media (max-width:520px){.tabs{flex-wrap:wrap;justify-content:flex-start}.tabs .tab{padding-inline:10px}}
#vm .mtiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
#vm .mt{border:1px solid var(--line);border-radius:6px;padding:8px 10px;display:flex;flex-direction:column;gap:2px;min-width:0}
#vm .mt span{color:var(--mute);font-size:12px}#vm .mt b{font:600 1.1rem var(--mono)}#vm .mt small{color:var(--mute);font-size:11.5px}
#vm h3{margin:12px 0 6px;font:600 12px var(--mono);letter-spacing:.1em;text-transform:uppercase;border-left:3px solid var(--warn);padding-left:8px}
#vm td.up,#vm b.up{color:var(--up)}#vm td.down,#vm b.down{color:var(--down)}
#term .eyeg{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr));gap:10px}
#term .eye{border:1px solid var(--line);border-radius:4px;padding:10px;background:var(--panel);min-width:0}
#term .eye h4{margin:0 0 6px;font:600 12px var(--mono);letter-spacing:.08em;text-transform:uppercase;display:flex;justify-content:space-between;gap:8px}
#term .eye h4 span{color:var(--mute);font-weight:400;text-transform:none;letter-spacing:0;white-space:nowrap}
#term .eyen{display:flex;flex-wrap:wrap;gap:5px}#term .eyen .chip{padding:3px 8px;font-size:12px}
#term .eye p.sm{margin:6px 0 0}
details.sec{margin:14px 0 4px}details.sec>summary{cursor:pointer;list-style:none}details.sec>summary h2{display:inline}details.sec>summary::after{content:" ▸ tap for every detail";font-size:12px;color:var(--mute,#8b949e)}details.sec[open]>summary::after{content:" ▾"}#newsx .ni{display:block;width:100%;text-align:left;font:inherit;background:var(--card,#141a1f);border:1px solid var(--line,#2a333b);border-radius:10px;padding:10px;margin:8px 0;color:inherit;cursor:pointer}#newsx .ni b{margin-right:8px}#newsx .eff{font-size:12px;margin-top:4px}
.pc .odds{display:flex;height:8px;border-radius:4px;overflow:hidden;background:var(--line);margin:6px 0 2px}.pc .odds i{display:block;background:var(--line)}.pc .odds i.gd{background:#22a06b}.pc .odds i.bd{background:#e5484d}
.pgtabs{display:flex;gap:6px;flex-wrap:wrap}#term .rt{width:100%}#term .rt td.on{outline:2px solid var(--accent);font-weight:600}#term .rt td.g{color:var(--up)}#term .rt td.b{color:var(--down)}
.pcg{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;margin:8px 0}.pc{display:block;width:100%;text-align:left;font:inherit;background:var(--card,#141a1f);border:1px solid var(--line,#2a333b);border-radius:10px;padding:10px;color:inherit;cursor:pointer}.pc .pct{display:flex;justify-content:space-between;align-items:baseline}.pc .spk{display:block;width:100%;height:34px;margin:6px 0}.pc .pl{display:flex;flex-wrap:wrap;gap:4px 10px;font-size:12px;margin-top:4px}.pcw h4{margin:0 0 4px}#tm-move h4{margin:10px 0 4px}
#term:not(.stk) .tm-stk,#term:not(.ide) .tm-ide,#term.stk .tm-idx,#term.ide .tm-idx{display:none!important}
#screener>*:not(#newsx){display:none!important}
#vm .vtg{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,150px),1fr));gap:8px}
#vm .vt{display:flex;flex-direction:column;gap:2px;text-align:left;padding:10px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:inherit;font:inherit;cursor:pointer}
#vm .vt.wait{opacity:.55}#vm .vwait summary{cursor:pointer;margin:8px 0;color:var(--mute)}
#term .nx{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));gap:10px}#term .nx>div{border:1px solid var(--line);border-radius:6px;padding:12px;background:var(--panel)}
#term .nx h4{margin:0 0 6px;font:600 11px var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--mute)}#term .nx b.big{font-size:18px;display:block;margin-bottom:4px}#term .nx p{margin:0;font-size:13px}
#term ol.phil{margin:6px 0 0;padding-left:20px;font-size:13px;display:flex;flex-direction:column;gap:3px}
#vm .vt:hover{border-color:var(--accent)}#vm .vt .big{font:600 20px var(--mono)}#vm .vt small{color:var(--mute);font-size:11px}
.dbars{display:flex;flex-direction:column;gap:4px;max-width:720px}.dsep{height:8px}
.dbar{display:grid;grid-template-columns:minmax(90px,140px) 1fr 56px;gap:8px;align-items:center;background:none;border:0;padding:2px 0;color:inherit;font:inherit;text-align:left;cursor:pointer}
.dbar .dl{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.dbar .dv{font:12px var(--mono);text-align:right}
.dbar .dt{position:relative;height:12px;background:linear-gradient(var(--line),var(--line)) 50% 0/1px 100% no-repeat}
.dbar .dt i{position:absolute;top:1px;bottom:1px;border-radius:2px}.dbar .gd{background:#22a06b}.dbar .bd{background:#e5484d}
#term .eye .chip.cu{border-color:#22a06b;color:#22a06b}#term .eye .chip.cd{border-color:#e5484d;color:#e5484d}
#term .tm-tables>summary{cursor:pointer;font-weight:600;padding:6px 0}
#term .eye p.bt{font-family:var(--mono);font-size:11px}#term .eye.pb{border-color:var(--acc,#3b82f6)}
#term .mtype{font:600 13px var(--mono);margin:0 0 8px;display:flex;gap:8px;flex-wrap:wrap;align-items:baseline}#term .mtype .sm{font-weight:400;color:var(--mute)}
#term ul.wk{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px}
#term ul.wk li{display:flex;gap:10px;align-items:baseline;font-size:13px}
#term ul.wk b{font-family:var(--mono);min-width:56px;text-align:right}#term ul.wk small{color:var(--mute)}
#term .pill.warn{background:color-mix(in srgb,var(--accent) 18%,transparent);color:var(--accent)}#term .pill.fail{background:color-mix(in srgb,var(--down) 18%,transparent);color:var(--down)}
#tm-mview ul.wk .pill{min-width:78px;text-align:center}#tm-mview tr.hi td{background:color-mix(in srgb,var(--up) 8%,transparent)}
#tm-mview details summary{cursor:pointer}#tm-mview .sumbar{margin:0 0 8px}
#tm-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:12px;align-items:start}#tm-row>.pnl{min-width:0;margin:0}
#tm-rec .rt2{display:flex;flex-direction:column;gap:10px}#tm-rec .rtile{border:1px solid var(--line);border-radius:6px;padding:10px;background:var(--panel)}
#tm-rec h4{margin:0 0 6px;font:600 12px var(--mono);letter-spacing:.08em;text-transform:uppercase;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}#tm-rec h4 .sm{text-transform:none;letter-spacing:0;font-weight:400}
#tm-rec .rk{display:grid;grid-template-columns:1fr auto;gap:2px 8px;width:100%;text-align:left;background:none;border:0;border-top:1px solid var(--line);padding:6px 0;color:inherit;font:inherit;cursor:pointer}
#tm-rec .rk:first-of-type{border-top:0}#tm-rec .rk:hover .rn{color:var(--accent)}#tm-rec .rn{font:600 13px var(--mono)}#tm-rec .dv{font:12px var(--mono);text-align:right}#tm-rec .rl{grid-column:1/-1;font-size:12px;color:var(--mute)}
#tm-iv b.up{color:var(--up)}#tm-iv b.down{color:var(--down)}#tm-iv b.warn{color:var(--warn)}
"""


def macro_summary(root: Path) -> dict:
    """Value-tab macro block from the NSE terminal data (docs/nse-terminal.html): rates, rupee, oil, inflation,
    global markets, FII/DII flows and sector valuations against their own history."""
    import refresh as R
    try:
        n = R.read_nset((root / "docs/nse-terminal.html").read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {"asof": str(n.get("asof", ""))[:16], "tiles": [], "glob": [], "sectors": [], "flows": None}
    lab = {"usdinr": ("USD/INR", "", 2), "in10y": ("India 10-year", "%", 2), "us10y": ("US 10-year", "%", 2),
           "brent": ("Brent crude", " $", 1), "cpi_yoy": ("India CPI inflation", "%", 2)}
    for k, (name, unit, dp) in lab.items():
        v = (n.get("macro") or {}).get(k) or []
        if len(v) >= 13:
            out["tiles"].append({"name": name, "v": round(v[-1][1], dp), "unit": unit, "m": v[-1][0], "y": round(v[-1][1] - v[-13][1], dp)})
    for name, x in ((n.get("glob") or {}).get("series") or {}).items():
        r = x.get("rows") or []
        if len(r) > 22:
            out["glob"].append({"name": name, "v": r[-1][1], "d": r[-1][0], "m1": r[-1][1] / r[-22][1] - 1})
    for x in n.get("sectors") or []:
        if not (x.get("pe_med") and x.get("snap_pe") and x.get("snap_close") and x.get("ltp")):
            continue
        pe = x["snap_pe"] * x["ltp"] / x["snap_close"]          # NSE's last published P/E scaled to today's price
        if True:
            out["sectors"].append({"name": x["name"], "pe": round(pe, 1), "med": round(x["pe_med"], 1), "prem": pe / x["pe_med"] - 1,
                                   "state": x.get("state"),
                                   "chg": (x["ltp"] / x["prev"] - 1) if x.get("ltp") and x.get("prev") else None})
    out["sectors"].sort(key=lambda z: z["prem"])
    fd = n.get("fiidii") or {}
    if fd:
        import datetime as _dt
        def key(d):
            try:
                return _dt.datetime.strptime(d, "%d-%b-%Y")
            except Exception:
                return _dt.datetime.min
        last = sorted(fd, key=key)[-1]
        out["flows"] = {"d": last, "fii": (fd[last].get("FII/FPI") or {}).get("net"), "dii": (fd[last].get("DII") or {}).get("net")}
    if n.get("gsec"):
        out["gsec"] = round(n["gsec"], 2)
    # market view for the Nifty 50: equity risk premium now (NSE's last P/E scaled to today's price) against its own
    # ~11-year monthly history; a higher premium means stocks are cheaper relative to bonds
    nf = next((x for x in n.get("sectors") or [] if x.get("name") == "Nifty 50"), None)
    if nf and nf.get("snap_pe") and nf.get("snap_close") and nf.get("ltp") and nf.get("erp_snap") is not None:
        pe_now = nf["snap_pe"] * nf["ltp"] / nf["snap_close"]
        erp_now = nf["erp_snap"] - (1 / nf["snap_pe"] - 1 / pe_now)
        hist = sorted(v[1] if isinstance(v, list) else v for v in (nf.get("erp_sorted") or []) if v is not None)
        pct = sum(1 for v in hist if v < erp_now) / len(hist) if hist else None
        flows = [((fd[d].get("FII/FPI") or {}).get("net") or 0) for d in fd] if fd else []
        bt = (((n.get("fund") or {}).get("bt_idx") or {}).get("results") or {}).get("E/P") or {}
        out["view"] = {"pe": round(pe_now, 1), "pe_med": nf.get("pe_med"), "erp": round(erp_now, 4), "erp_med": nf.get("erp_med"),
                       "pct": round(pct, 3) if pct is not None else None, "n_hist": len(hist), "rf": nf.get("rf"),
                       "g_sus": nf.get("g_sus"), "fii_sum": round(sum(flows), 0), "fii_days": len(flows),
                       "ts12": (bt.get("nifty_ts") or {}).get("12"), "ic12": (bt.get("12") or {}).get("ic"), "t12": (bt.get("12") or {}).get("t")}
    # index and ETF valuation (ADARSH 27 Nov), Damodaran style: earnings yield against the 10-year bond and the
    # implied equity risk premium (earnings yield + sustainable growth - bond) against the index's own monthly history
    iv = []
    for x in n.get("sectors") or []:
        if not (x.get("snap_pe") and x.get("snap_close") and x.get("ltp") and x.get("erp_snap") is not None):
            continue
        pe_now = x["snap_pe"] * x["ltp"] / x["snap_close"]
        erp_now = x["erp_snap"] - (1 / x["snap_pe"] - 1 / pe_now)
        hist = sorted(v[1] if isinstance(v, list) else v for v in (x.get("erp_sorted") or []) if v is not None)
        if len(hist) < 24:
            continue
        iv.append({"name": x["name"], "pe": round(pe_now, 1), "med": x.get("pe_med"), "ey": round(1 / pe_now, 4),
                   "rf": round(x.get("rf") or 0, 4), "g": round(x.get("g_sus") or 0, 4), "erp": round(erp_now, 4),
                   "erp_med": round(x.get("erp_med") or 0, 4), "pct": round(sum(1 for v in hist if v < erp_now) / len(hist), 3),
                   "n": len(hist), "pb": x.get("pb"), "dy": x.get("dy")})
    out["idxval"] = iv
    stk = ((n.get("fund") or {}).get("stk") or {})
    rows = []
    for sym, x in stk.items():
        if x.get("g_impl") is None or x.get("g_sus") is None:
            continue
        rows.append({"s": sym, "g_impl": round(x["g_impl"], 4), "g_sus": round(x["g_sus"], 4), "roe": x.get("roe"), "verdict": x.get("verdict")})
    rows.sort(key=lambda r: r["g_impl"] - r["g_sus"])
    out["growth"] = {"asof": (n.get("fund") or {}).get("asof"), "rows": rows}
    return out


VALUE_HTML = r"""
<div class="pnl" id="vm"><h2>Value and macro</h2><div id="vm-body"></div></div>
"""

VALUE_JS = r"""
(function(){const M=window.MACRO||{},el=document.getElementById("vm-body");if(!el)return;
const f=(x,d=2)=>x==null?"–":Number(x).toLocaleString("en-IN",{maximumFractionDigits:d,minimumFractionDigits:d});
const p=(x,d=1)=>x==null?"–":(x>0?"+":"")+(x*100).toFixed(d)+"%";
const RSV=(typeof RS!=="undefined"?RS:{});const L=Object.entries(RSV).map(([s,x])=>Object.assign({s},x));
let h="";const V=M.view;
/* 1. market view */
if(V){const pc=V.pct;const val=pc==null?["Not enough history","warn"]:pc<0.33?["Expensive","bad"]:pc>0.67?["Cheap","good"]:["Fair value","warn"];
  const fiiBuy=V.fii_sum>0;const up200=L.length?L.filter(x=>(x.vs200||0)>0).length/L.length:null;
  const act=val[0]==="Cheap"?(fiiBuy?"Add: cheap and foreign money is coming in.":"Accumulate slowly: cheap, but foreign investors are still selling."):
            val[0]==="Expensive"?(fiiBuy?"Hold, don't chase: the trend can run, but you are paying up.":"Trim and keep cash: expensive and foreign investors are selling."):
            (fiiBuy?"Selective buying: fair price, foreign money coming in.":"Wait for a better price or for foreign buying to turn.");
  h+=`<h3>Is the market overpriced? (Nifty 50)</h3><div class="verdict"><b class="${val[1]}">${val[0]}</b><span>${esc(act)}</span></div>
  <ul class="why"><li>P/E about <b>${f(V.pe,1)}</b> against a long-run median of ${f(V.pe_med,1)}.</li>
  <li>Equity risk premium ${p(V.erp,2)} (earnings yield plus sustainable growth minus the 10-year bond) is cheaper than <b>${pc==null?"–":Math.round(pc*100)+"%"}</b> of the last ${V.n_hist} months (median ${p(V.erp_med,2)}). Higher premium = cheaper.</li>
  <li>Foreign investors (FII) net ${V.fii_sum>0?"bought":"sold"} <b class="${V.fii_sum>0?"good":"bad"}">₹${f(Math.abs(V.fii_sum),0)} Cr</b> over the last ${V.fii_days} reported days.</li>
  ${up200!=null?`<li>${Math.round(up200*100)}% of Nifty 500 stocks are above their 200-day average${up200<0.4?" (weak breadth: selling is broad)":up200>0.65?" (broad strength)":""}.</li>`:""}</ul>
  <p class="note">How to read it: in India, rallies have tended to start when the market is cheap and foreign money turns to buying, rather than "high keeps going higher" as in the US. This view combines the two. It is a rule of thumb, not a tested signal: the old NSE terminal's back-test found the Nifty's cheapness predicted the next 12 months only weakly (correlation ${f(V.ts12,2)}).</p>`}
/* 2. Damodaran value screen (ADARSH 27 Nov): fundamentals only, no price momentum. Technical lives on Terminal/Stocks.
   cost of equity = risk-free + beta x India's implied ERP (CAPM); ROE = P/B / P/E; growth = ROE x retention (capped 12%);
   value = two-stage justified P/E (5 years at g, then stable growth with excess returns fading toward the cost of equity) */
/* ERP: Damodaran's published India premium (mature-market premium plus India country risk, about 7%), or the Nifty's implied premium if higher */
const RF=(V&&V.rf)||0.056,ERP=Math.max(0.07,(V&&V.erp)||0);
const CYC=/oil|gas|petro|metal|mining|steel|alumin|coal|power|shipping|transport services|sugar|cement|fertili/i;
const dam=x=>{if(!(x.pe>0)||!(x.pb>0))return null;const roe=x.roce>0?Math.min(x.pb/x.pe,x.roce/100):x.pb/x.pe,b=Math.min(1.6,Math.max(0.6,x.beta||1)),ke=RF+b*ERP;
  const pay=Math.min(1,Math.max(0,(x.dy||0)*x.pe/100)),gs=Math.min(0.05,ke-0.01),roeS=Math.max(ke,Math.min(roe,ke+0.05));
  const jpe=g=>{let v=0;for(let t=1;t<=5;t++)v+=Math.pow(1+g,t)*Math.max(0,1-g/roe)/Math.pow(1+ke,t);return v+Math.pow(1+g,5)*(1+gs)*(1-gs/roeS)/((ke-gs)*Math.pow(1+ke,5))};
  const g=Math.max(0,Math.min(0.12,roe*(1-pay))),vp=jpe(g)/x.pe;let lo=-0.1,hi=0.6;for(let i=0;i<40;i++){const m=(lo+hi)/2;(jpe(m)<x.pe?lo=m:hi=m)}
  return {roe,ke,g,vp,gi:(lo+hi)/2,spread:roe-ke}};
const dm=L.map(x=>Object.assign(x,{dm:dam(x)})).filter(x=>x.dm&&(x.turnover_cr||0)>=10&&!CYC.test((x.industry||"")+" "+(x.ind||"")));
const pass=x=>x.dm.spread>=0.03&&x.dm.vp>=1.25&&(x.de==null||x.de<=1.5);
const cheap=dm.filter(pass).sort((a,b)=>b.dm.vp-a.dm.vp).slice(0,15);
window.DAMV=cheap.map(x=>({s:x.s,line:`+${Math.round((x.dm.vp-1)*100)}% to value · ROE ${p(x.dm.roe,0)} vs cost ${p(x.dm.ke,0)}`}));
/* nearest misses for the Terminal's Value picks tile when nothing passes: earns its cost of capital, low debt, best value/price */
window.DAMN=dm.filter(x=>!pass(x)&&x.dm.vp>=1&&x.dm.spread>=0.03&&(x.de==null||x.de<=1.5)).sort((a,b)=>b.dm.vp-a.dm.vp).slice(0,4).map(x=>({s:x.s,vp:x.dm.vp,line:`${x.dm.vp>=1?"+":""}${Math.round((x.dm.vp-1)*100)}% to value · ROE ${p(x.dm.roe,0)} vs cost ${p(x.dm.ke,0)}`}));
const dear=dm.filter(x=>x.dm.vp<=0.5&&x.dm.gi>x.dm.g+0.1).sort((a,b)=>a.dm.vp-b.dm.vp).slice(0,6);
const tile=(x,ok)=>{const d=x.dm;return `<button class="vt${ok?"":" wait"}" data-s="${esc(x.s)}"><b>${esc(x.s)}</b><span class="big ${ok?"good":"bad"}">${ok?"+"+Math.round((d.vp-1)*100)+"%":Math.round((d.vp-1)*100)+"%"} to value</span><small>ROE ${p(d.roe,0)} vs cost of equity ${p(d.ke,0)}</small><small>${d.gi<-0.09?"price assumes it shrinks":"price needs "+p(d.gi,0)+" growth"}; it funds ${p(d.g,0)}</small></button>`};
h+=`<h3>Undervalued on Damodaran's tests</h3><p class="note">Every tile passes three fundamental tests, no price charts involved: <b>it earns more than its cost of capital</b> (return on equity, the lower of P/B ÷ P/E and ROCE, at least 3 points above its cost of equity = risk-free ${p(RF,1)} + beta × India equity risk premium ${p(ERP,1)}); <b>its value is 25%+ above the price</b> (two-stage model: 5 years growing at ROE × retained profit, capped at 12%, then ${p(Math.min(0.05,RF+ERP-0.01),0)} with excess returns fading to the cost of equity); and <b>debt/equity is 1.5 or less</b>. Cyclicals (oil, metals, power, cement and similar) are left out because their current profits may be a peak. Ranked by the gap to value. Tap a tile to analyze.</p><div class="vtg">${cheap.map(x=>tile(x,true)).join("")||'<p class="note">No stock passes all three today.</p>'}</div>
${dear.length?`<details class="vwait"><summary>Priced for a story (${dear.length}): the price needs 10+ points more growth than the company funds</summary><div class="vtg">${dear.map(x=>tile(x,false)).join("")}</div></details>`:""}
<p class="note">Value is a 1–3 year call, not a timing signal. Our back-test of cheapness on the Nifty 50 (2023–26) could not prove that cheap beats dear over 12 months, so size these as long-term holdings and diversify (Damodaran: 30–40 names).</p>`;
/* 3. what the price asks for (reverse DCF from the old NSE terminal) */
const G=(M.growth||{}).rows||[];if(G.length){const room=G.slice(0,8),stretch=G.slice(-6).reverse();
  const mx=Math.max(...G.map(r=>Math.abs(r.g_impl-r.g_sus)).filter(isFinite),0.01);
  const bar=r=>{const g=r.g_impl-r.g_sus,w=Math.min(50,Math.abs(g)/mx*50);return `<button class="dbar" data-s="${esc(r.s)}"><span class="dl">${esc(r.s)}</span><span class="dt"><i class="${g<=0?"gd":"bd"}" style="${g<=0?"right":"left"}:50%;width:${w}%"></i></span><span class="dv ${g<=0?"good":"bad"}">${p(g,0)}</span></button>`};
  h+=`<h3>What the price asks for (Nifty 50)</h3><p class="note">Green bar = the price needs less growth than the company can sustain (room for error). Red = the price asks for more. Tap a name to analyze it. Fundamentals as of ${esc((M.growth||{}).asof||"")}.</p>
  <div class="dbars">${room.map(bar).join("")}<div class="dsep"></div>${stretch.map(bar).join("")}</div>`}
/* 4. macro, sectors, global */
if((M.tiles||[]).length)h+=`<h3>India macro</h3><div class="mtiles">${M.tiles.map(t=>`<div class="mt"><span>${esc(t.name)}</span><b>${f(t.v)}${esc(t.unit)}</b><small>${esc(t.m)} · ${t.y>0?"+":""}${f(t.y)} on a year ago</small></div>`).join("")}${M.flows?`<div class="mt"><span>FII net, ${esc(M.flows.d)}</span><b class="${M.flows.fii>0?"up":"down"}">₹${f(M.flows.fii,0)} Cr</b><small>DII ₹${f(M.flows.dii,0)} Cr</small></div>`:""}</div>`;
if((M.sectors||[]).length){const sx=Math.max(...M.sectors.map(x=>Math.abs(x.prem||0)),0.01);h+=`<h3>Sector valuations: cheap or dear vs their own history</h3><div class="dbars">${M.sectors.slice().sort((a,b)=>(a.prem||0)-(b.prem||0)).map(x=>{const w=Math.min(50,Math.abs(x.prem||0)/sx*50);return `<div class="dbar"><span class="dl">${esc(x.name.replace(/^Nifty /,""))}</span><span class="dt"><i class="${x.prem<0?"gd":"bd"}" style="${x.prem<0?"right":"left"}:50%;width:${w}%"></i></span><span class="dv ${x.prem<0?"good":"bad"}">${p(x.prem,0)}</span></div>`}).join("")}</div><p class="note">P/E vs its own median. Green = cheaper than usual. NSE's last published index P/E scaled to today's close (${esc(M.asof||"")}).</p>`}
if((M.glob||[]).length)h+=`<h3>Global</h3><div class="mtiles">${M.glob.map(g=>`<div class="mt"><span>${esc(g.name)}</span><b>${f(g.v,g.v<50?2:0)}</b><small class="${g.m1>0?"up":"down"}">${p(g.m1)} in a month · ${esc(g.d)}</small></div>`).join("")}</div>`;
el.innerHTML=h||'<p class="note">Macro data appears after the next refresh.</p>';
el.addEventListener("click",e=>{const b=e.target.closest("[data-s]");if(b&&window.azGo){e.stopPropagation();azGo(b.dataset.s)}});
/* the Nifty 500 screener lives on the Terminal tab */
try{const q=PRESETS.find(p=>p[0]==="vq");if(q)q[3]=x=>{const d=x.dm||dam(x);return !!d&&d.spread>=0.03&&d.vp>=1.25&&(x.de==null||x.de<=1.5)}}catch(e){}
})();
"""


def lab_summary(root: Path, correction: bool) -> dict | None:
    """What the desk journal's indicator back-test says works in today's kind of market (journal/indicator-lab.json)."""
    lab = _load(root / "journal/indicator-lab.json")
    if not lab or not lab.get("indicators"):
        return None
    side = "weak" if correction else "up"
    rows = []
    for k, r in lab["indicators"].items():
        o, i_ = r.get(f"out_{side}") or {}, r.get(f"in_{side}") or {}
        if o.get("n", 0) < 100 or o.get("abn") is None or i_.get("abn") is None:
            continue
        both = (o["abn"] > 0) == (i_["abn"] > 0)
        v = {"keep": "passed every check", "avoid": "tested warning"}.get(r.get("verdict"), "same sign in both periods" if both else "flipped between periods")
        rows.append({"k": k, "name": r["name"], "abn": o["abn"], "n": o["n"], "both": both, "verdict": v})
    best = sorted([x for x in rows if x["abn"] > 0 and x["both"]], key=lambda x: -x["abn"])[:6]
    worst = sorted([x for x in rows if x["abn"] < 0 and x["both"]], key=lambda x: x["abn"])[:4]
    kept = len(lab.get("keep") or [])
    note = (f"From the desk journal: {lab['tested']} indicators back-tested on Dhan data {lab['from']} to {lab['asof']}, "
            f"last 3 years shown, 21-day return vs the average stock. {kept} of {lab['tested']} passed every check including the "
            f"many-ideas test{'' if kept else ', so these are leads, not proven signals'}.")
    return {"market": "falling" if correction else "rising", "best": best, "worst": worst, "note": note}

def mview_summary(root: Path) -> dict | None:
    """The market view (market_view.py): beliefs tested out of sample, VIX range, risk table, low-risk screen."""
    v = _load(root / "docs/market-view.json")
    if not v or not v.get("beliefs"):
        return None
    bl = [{"k": b["key"], "t": b["title"], "p": b.get("plain"), "v": b["verdict"], "h": b.get("h"),
           "m": b["oos"].get("raw_mean"), "hit": b["oos"].get("hit"), "mo": b["oos"].get("months"), "note": b.get("note"),
           "u": {"nifty_bounce": "Nifty vs a normal 5 days", "nifty_fade": "Nifty vs a normal 5 days",
                 "bank_leads": "Nifty in the 5 days after the signal"}.get(b["key"])}
          for b in v["beliefs"]]
    order = {"HOLDS": 0, "UNPROVEN": 1, "FAILS": 2}
    bl.sort(key=lambda b: (order.get(b["v"], 3), -abs(b["m"] or 0)))
    cs = next((b for b in v["beliefs"] if b["key"] == "calm_strong"), None)
    return {"asof": v.get("asof"), "oos_from": v.get("oos_from"), "type": v.get("regime"), "label": v.get("regime_text"),
            "r63": v.get("nifty_r63"), "vs200": v.get("nifty_vs200"), "vix": v.get("vix"), "beliefs": bl,
            "next": v.get("next_day"), "rot": (v.get("rotation") or {}).get("stats"),
            "screen": v.get("screen") or [], "screen_v": cs["verdict"] if cs else None,
            "screen_hit": cs["oos"].get("hit") if cs else None, "screen_m": cs["oos"].get("raw_mean") if cs else None,
            "ideas": [{"k": o["key"], "t": o["title"], "p": o["plain"], "hedge": o.get("hedge"), "sizing": o.get("sizing"),
                       "note": o.get("note"), "v": o.get("verdict"), "live": o.get("live") or [], "pts": o.get("pts"),
                       "is": {x: o["is"].get(x) for x in ("raw_mean", "hit", "months", "n", "t")},
                       "oos": {x: o["oos"].get(x) for x in ("raw_mean", "hit", "months", "n", "t")}} for o in v.get("ideas") or []],
            "timing": [{"k": o["key"], "rule": o["rule"], "idx": o["index"], "t": o["plain"], "src": o.get("src"), "v": o["verdict"],
                        "safer": o.get("safer"), "on": o.get("on_today"), "m": o["oos"].get("raw_mean"), "hit": o["oos"].get("hit"),
                        "s": o["oos"].get("strat"), "h": o["oos"].get("hold"), "in": o["oos"].get("in_mkt"),
                        "s_is": o["is"].get("strat"), "h_is": o["is"].get("hold")} for o in v.get("timing") or []],
            "paper": v.get("paper"), "desk": v.get("desk"), "weekly": v.get("weekly"),
            "risk": [{"k": r["k"], **r["oos"]} for r in v.get("risk") or []][:24], "sectors": (v.get("sectors_today") or [])[:6]}


def play_summary(root: Path) -> dict | None:
    """Today's playbook from the desk journal (journal/playbook.json): the market type, what the indicator back-test
    favours and warns against in it, and the stocks where those indicators fired on the last session."""
    pb = _load(root / "journal/playbook.json")
    if not pb or not pb.get("type"):
        return None
    lab = _load(root / "journal/indicator-lab.json") or {}
    slim = lambda x: {k: x.get(k) for k in ("k", "name", "grade", "abn", "net", "t", "n")}
    ind = lab.get("indicators") or {}
    mt = pb["type"]
    # every indicator's out-of-sample result in today's market type, so each screen card can show its own evidence
    ev = {k: [round((r.get("out_" + mt) or {}).get("abn") or 0, 5), (r.get("out_" + mt) or {}).get("n", 0)]
          for k, r in ind.items() if (r.get("out_" + mt) or {}).get("n", 0) >= 60}
    # the trader-skill setups' lab twins, out of sample in every market type (21-day return vs the average stock)
    tw = {"breakout_20d": "don20", "reclaim_ma20": "x_sma20", "oversold_bounce": "rsi14_x30", "rsi2_dip": "rsi2_5", "momentum70": "rsi14_x70"}
    setups = {s: {"name": (ind.get(k) or {}).get("name"), **{t: [round((((ind.get(k) or {}).get("out_" + t) or {}).get("abn") or 0), 5),
                                                             (((ind.get(k) or {}).get("out_" + t) or {}).get("n") or 0)] for t in ("rising", "flat", "turning", "falling")}}
              for s, k in tw.items() if k in ind}
    return {"asof": pb.get("asof"), "type": mt, "label": pb.get("label"), "since": pb.get("since"), "setups": setups,
            "use": [slim(x) for x in pb.get("use", [])[:10]], "avoid": [slim(x) for x in pb.get("avoid", [])[:6]],
            "fired": {k: v[:40] for k, v in (pb.get("fired") or {}).items()},
            "warned": {k: v[:40] for k, v in (pb.get("warned") or {}).items()}, "ev": ev,
            "tested": lab.get("tested"), "from": lab.get("from"), "cutoff": lab.get("cutoff")}


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
    html = html.replace("</style>", AZ_CSS + CLEAN_CSS + "\n</style>", 1)
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
    # Stocks tab (ADARSH 26 Nov): the Terminal tab is index-first (market view, trading ideas, markets board); every
    # stock list lives on Stocks, which is the same #term section with the stock half shown instead of the index half.
    html = html.replace('aria-selected="true">Terminal</button>',
                        'aria-selected="true">Terminal</button><button class="tab" role="tab" data-t="ide" aria-selected="false">Ideas</button><button class="tab" role="tab" data-t="stk" aria-selected="false">Stocks</button>', 1)
    html = html.replace('const r=t==="research";if(r)t="screener";',
                        'const r=t==="research";if(r)t="screener";const sk=t==="stk",ide=t==="ide";if(sk||ide)t="term";$("term").classList.toggle("stk",sk);$("term").classList.toggle("ide",ide);const hh=sk?"stk":ide?"ide":t;', 1)
    html = html.replace('if(location.hash!=="#"+t)history.replaceState(null,"","#"+t)}', 'if(location.hash!=="#"+hh)history.replaceState(null,"","#"+hh)}', 1)
    html = html.replace('const pick=h=>(!h||h==="term"||h==="terminal")?"term":', 'const pick=h=>(!h||h==="term"||h==="terminal")?"term":(h==="stk"||h==="stocks")?"stk":(h==="ide"||h==="ideas")?"ide":', 1)
    for a, b in (("Best evidence", "Top picks"), ("Tested setups today", "Setups today"),
                 ("Turning bullish (tested signals)", "Turning bullish"), ("Dips in proven stocks", "Dips in strong stocks")):
        html = html.replace(a, b)
    html = html.replace('<section id="screener" class="wrap" style="gap:10px" hidden>',
                        '<section id="screener" class="wrap" style="gap:10px" hidden>' + VALUE_HTML, 1)
    html = html.replace('data-t="screener" aria-selected="false">Screen</button>', 'data-t="screener" aria-selected="false">Value</button>', 1)
    j = html.rfind("</body>")
    j = j if j >= 0 else len(html)
    mac_js = json.dumps(macro_summary(root), separators=(",", ":")).replace("</", "<\\/")
    lab_js = json.dumps(lab_summary(root, bool(working(root).get("correction"))), separators=(",", ":")).replace("</", "<\\/")
    play_js = json.dumps(play_summary(root), separators=(",", ":")).replace("</", "<\\/")
    mv_js = json.dumps(mview_summary(root), separators=(",", ":")).replace("</", "<\\/")
    try:                                            # 120-day closes per stock for the Terminal's sparklines and swing stops, scaled to last = 1000
        _cd = _load(root / "docs/chart-data.json") or {}
        spk = {k: [round(x / v["c"][-1] * 1000) for x in v["c"][-120:]] for k, v in (_cd.get("s") or {}).items() if v.get("c") and v["c"][-1] and None not in v["c"][-120:]}
    except Exception:
        spk = {}
    spk_js = json.dumps(spk, separators=(",", ":"))
    news_js = json.dumps(_load(root / "docs/news.json") or {}, separators=(",", ":")).replace("</", "<\\/")
    html = html[:j] + f"<script>window.SPK={spk_js};window.NEWS={news_js};window.LAB=/*LAB*/{lab_js}/*LAB*/;window.MACRO=/*MACRO*/{mac_js}/*MACRO*/;window.PLAY=/*PLAY*/{play_js}/*PLAY*/;window.MVIEW=/*MVIEW*/{mv_js}/*MVIEW*/;</script>\n<script>\n" + VALUE_JS + "\n</script>\n<script>\n" + AZ_JS.read_text(encoding="utf-8").replace("</", "<\\/") + "\n</script>\n" + html[j:]
    # Terminal look: dark by default; the button in the tab bar switches light/dark and the choice is kept in this browser.
    html = html.replace('<div class="tabs" role="tablist">',
                        '<div class="tabs" role="tablist"><button class="tab" id="thbtn" title="Light or dark" aria-label="Switch light or dark">Light</button>', 1)
    theme = ("<script>(function(){const r=document.documentElement;let t='dark';try{t=localStorage.getItem('aj-th')||'dark'}catch(e){}"
             "r.setAttribute('data-theme',t);const b=document.getElementById('thbtn');const lb=()=>{if(b)b.textContent=t==='dark'?'Light':'Dark'};lb();if(b)b.onclick=()=>{t=t==='dark'?'light':'dark';"
             "r.setAttribute('data-theme',t);lb();try{localStorage.setItem('aj-th',t)}catch(e){}}})();</script>\n")
    k = html.rfind("</body>")
    k = k if k >= 0 else len(html)
    html = html[:k] + theme + html[k:]
    for must in ('data-t="stk"', 'data-t="ide"', 'const sk=t==="stk",ide=t==="ide"', 'h==="stocks"', 'data-t="term"', 'id="term"', '"term","screener"', 'h==="term"', 'data-t="pf"', 'id="allsel"', 'id="az"', '"pf","az"'):
        if must not in html:
            raise RuntimeError(f"desk page changed shape; could not insert the Terminal tab ({must})")
    import page_feed                                    # newer nightly data from aj-live, no republish needed
    html = page_feed.inject(html)
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
