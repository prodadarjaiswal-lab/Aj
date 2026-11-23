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


def _data_js(root: Path) -> dict:
    d = root / "docs/terminal"
    bt = _load(d / "backtest.json")
    if bt:
        bt["trades"] = bt.get("trades", [])[-80:]
    js = lambda o: json.dumps(o, separators=(",", ":")).replace("</", "<\\/")
    return {"BT": js(bt), "MK": js(_load(d / "markets.json")), "WL": js(_load(d / "watch.json")),
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
    for must in ('data-t="term"', 'id="term"', '"term","screener"', 'h==="term"'):
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
