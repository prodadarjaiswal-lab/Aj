"""Keep the published terminal page current without a Claude republish.

The page is a snapshot: its data is baked in as JSON blobs between markers like /*DATA*/{...}/*DATA*/.
Nightly, GitHub Actions builds the same page and `push` copies every blob (and every per-stock d/*.json
file) into the public repo prodadarjaiswal-lab/aj-live, branch "page", cut into pieces small enough for
the GitHub connector. When someone opens the page, the updater added by `inject` reads aj-live's
manifest through the GitHub connector; if it is newer than the page's own build it saves the new blobs
in the browser and reloads once, and the boot script hands them to the page before the page's own
scripts run. Per-stock files are then read from aj-live too. If anything fails, the page simply shows
what was baked in.

  python page_feed.py push SITE OUT     write OUT/manifest.json + OUT/p/*.txt from a built SITE dir
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
REPO, BRANCH = ("prodadarjaiswal-lab", "aj-live"), "page"
PIECE = 600_000                       # characters per piece; the connector handles files well under 1 MB
HEAD, TAIL = "AJP1:", ":AJP1END"      # sentinels so a piece can be cut cleanly out of any connector reply
BLOB = re.compile(r"/\*([A-Z][A-Z0-9_]{1,15})\*/(.*?)/\*\1\*/", re.S)


def blobs(html: str) -> dict:
    """{TAG: json text} for every marked blob that holds valid JSON."""
    out = {}
    for m in BLOB.finditer(html):
        try:
            json.loads(m.group(2))
        except ValueError:
            continue
        out.setdefault(m.group(1), m.group(2))
    return out


def built_of(html: str) -> str | None:
    m = re.search(r'window\.AJ_BUILT="([^"]+)"', html)
    return m.group(1) if m else None


BOOT = """<script>/* page_feed boot: newer data saved by the updater replaces the baked-in blobs */
window.AJ_BUILT=%s;(function(){try{const c=JSON.parse(localStorage.getItem("aj-feed")||"null");
if(c&&c.built>window.AJ_BUILT){const b={};for(const k in c.blobs)b[k]=JSON.parse(c.blobs[k]);window.__AJ=b;window.AJ_FEED=c.built;window.AJ_CHUNKS=c.chunks||null}
else if(c)localStorage.removeItem("aj-feed")}catch(e){window.__AJ=null}})();
%s</script>
"""

UPDATER = """/* updater: checks aj-live for data newer than this page and reloads once to show it */
(function(){const O=%s,R=%s,B=%s,H=%s,T=%s;let MCP=null;
const txt=r=>{for(const b of (r&&r.content)||[]){const s=(b&&b.resource&&typeof b.resource.text==="string")?b.resource.text:(b&&typeof b.text==="string"?b.text:null);
  if(s!=null){const i=s.indexOf(H),j=s.lastIndexOf(T);if(i>=0&&j>i)return s.slice(i+H.length,j);if(s.trim().startsWith("{"))return s}}return null};
const get=async p=>{const t=txt(await MCP.callTool("GitHub","get_file_contents",{owner:O,repo:R,path:p,ref:B},{cache:false}));if(t==null)throw new Error("empty "+p);return t};
const join=async ps=>(await Promise.all(ps.map(get))).join("");
const chip=(s,ok)=>{try{let e=document.getElementById("aj-feed-chip");if(!e){e=document.createElement("div");e.id="aj-feed-chip";
  e.style.cssText="position:fixed;left:8px;bottom:8px;z-index:9999;font:12px system-ui,sans-serif;padding:4px 8px;border-radius:6px;background:rgba(0,0,0,.75);color:#fff;pointer-events:none";document.body.appendChild(e)}
  e.textContent=s;setTimeout(()=>e.remove(),ok?6000:12000)}catch(e){}};
const mcp=async()=>{if(!MCP){try{MCP=window.claude&&window.claude.use?await window.claude.use("mcp"):null}catch(e){MCP=null}}return MCP};
const local=window.fetch.bind(window);
window.ajFetchChunk=async n=>{const c=window.AJ_CHUNKS;if(c&&c[n]&&await mcp()){try{const j=JSON.parse(await join(c[n]));return{ok:true,status:200,json:async()=>j}}catch(e){}}return local("d/"+n+".json")};
(async()=>{if(!await mcp())return;if(window.AJ_FEED)chip("Data updated automatically · built "+window.AJ_FEED+" IST",true);let man;try{man=JSON.parse(await get("manifest.json"))}catch(e){return}
  const have=window.AJ_FEED||window.AJ_BUILT;if(!man||!man.built||man.built<=have)return;
  try{if(sessionStorage.getItem("aj-feed-tried")===man.built)return;sessionStorage.setItem("aj-feed-tried",man.built)}catch(e){}
  chip("Loading "+(man.asof||man.built)+" data…",true);
  try{const blobs={};for(const k in man.blobs){blobs[k]=await join(man.blobs[k]);JSON.parse(blobs[k])}
    localStorage.setItem("aj-feed",JSON.stringify({built:man.built,blobs,chunks:man.chunks||null}));location.reload()}
  catch(e){chip("Newer data ("+(man.asof||man.built)+") could not be loaded here: "+String(e&&e.message||e).slice(0,60),false)}})();
})();
"""


def inject(html: str, built: str | None = None) -> str:
    """Let the baked-in blobs be replaced by newer ones and add the boot + updater scripts."""
    built = built or dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M")
    if "page_feed boot" in html:
        return html

    def sub(m):
        try:
            json.loads(m.group(2))
        except ValueError:
            return m.group(0)
        return f'(window.__AJ&&window.__AJ["{m.group(1)}"])||{m.group(0)}'
    html = BLOB.sub(sub, html)
    html = html.replace('fetch("d/"+n+".json")', "window.ajFetchChunk(n)")
    j = lambda o: json.dumps(o)
    up = UPDATER % (j(REPO[0]), j(REPO[1]), j(BRANCH), j(HEAD), j(TAIL))
    i = html.find("<script")
    return html[:i] + BOOT % (j(built), up) + html[i:]


def _pieces(text: str, stem: str, out: Path) -> list[str]:
    names = []
    for n, a in enumerate(range(0, max(len(text), 1), PIECE)):
        name = f"p/{stem}.{n}.txt"
        (out / name).write_text(HEAD + text[a:a + PIECE] + TAIL, encoding="utf-8")
        names.append(name)
    return names


def push(site: Path, out: Path) -> dict:
    """Manifest + pieces for the aj-live 'page' branch, from a site built by terminal_page.py --site."""
    html = (site / "index.html").read_text(encoding="utf-8")
    built = built_of(html)
    if not built:
        raise SystemExit("page has no AJ_BUILT: build it with page_feed.inject")
    (out / "p").mkdir(parents=True, exist_ok=True)
    for f in (out / "p").glob("*.txt"):
        f.unlink()
    man = {"built": built, "asof": None, "blobs": {}, "chunks": {}}
    for tag, text in blobs(html).items():
        man["blobs"][tag] = _pieces(text, "b-" + tag, out)
        if tag == "DATA":
            try:
                man["asof"] = (json.loads(text).get("today") or {}).get("asof")
            except Exception:
                pass
    for f in sorted((site / "d").glob("*.json")):
        man["chunks"][f.stem] = _pieces(f.read_text(encoding="utf-8"), "c-" + f.stem, out)
    (out / "manifest.json").write_text(json.dumps(man, separators=(",", ":")), encoding="utf-8")
    return {"built": built, "asof": man["asof"], "blobs": len(man["blobs"]), "chunks": len(man["chunks"]),
            "files": sum(len(v) for v in man["blobs"].values()) + sum(len(v) for v in man["chunks"].values())}


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "push":
        print(json.dumps(push(Path(sys.argv[2]), Path(sys.argv[3]))))
    else:
        print(__doc__)
        sys.exit(2)
