"""Copy the latest live.json (branch 'live') into the terminal page as today's bar.

Used by the scheduled republish so the page shows recent prices even for
viewers with no connector at all.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import refresh as R
import n500

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()


def load_live() -> dict | None:
    subprocess.run(["git", "-C", str(ROOT), "fetch", "-q", "origin", "live"], check=False)
    r = subprocess.run(["git", "-C", str(ROOT), "show", "origin/live:live.json"], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip().startswith("{"):
        return None
    d = json.loads(r.stdout)
    return d if d.get("q") else None


def bar(o: dict, q: list, day: str) -> bool:
    ltp, op, hi, lo, _ = q
    if not o["c"] or ltp <= 0 or op <= 0:
        return False
    n = len(o["c"])
    if o["d"][-1] == day:
        o["c"][-1], o["o"][-1] = ltp, op
        o["h"][-1], o["l"][-1] = max(hi, ltp), min(lo or ltp, ltp)
        return True
    if abs(op / o["o"][-1] - 1) < 2e-4 and abs(hi / o["h"][-1] - 1) < 2e-4:
        return False          # Dhan is repeating the last stored session
    o["d"].append(day)
    for k, v in (("o", op), ("h", max(hi, ltp)), ("l", min(lo or ltp, ltp)), ("c", ltp)):
        o[k].append(v)
    if "v" in o:
        o["v"].append(0)
    for k in list(o):
        o[k] = o[k][-R.BARS:]
    return n > 0


def main() -> int:
    live = load_live()
    page = ROOT / "docs/nse-terminal.html"
    html = page.read_text(encoding="utf-8")
    if not live:
        print("no live data")
        return 0
    nset = R.read_nset(html)
    eq_map = {str(v): k for k, v in json.loads(re.search(r"const LIVE_EQ=(\{[^}]*\})", html).group(1)).items()}
    idx_map = json.loads(re.sub(r"(\d+):", r'"\1":', re.search(r"const LIVE_IDX=(\{[^}]*\})", html).group(1)))
    day, k = live["d"], 0
    for sid, q in live["q"].get("IDX_I", {}).items():
        nm = idx_map.get(sid)
        if nm in nset["idx"] and bar(nset["idx"][nm], q, day):
            k += 1
    nc = nset["idx"]["Nifty 50"]["c"]
    for sid, q in live["q"].get("NSE_EQ", {}).items():
        s = eq_map.get(sid)
        if s in nset["stocks"]:
            x = nset["stocks"][s]
            if bar(x["ohlc"], q, day):
                x["prev"] = x["ohlc"]["c"][-2]
                x["tech"].update({a: b for a, b in R.tech(x["ohlc"], nc).items() if b is not None})
                k += 1
    nset["asof"] = live["t"][:16]
    nset["bar_today"] = day
    nset["partial_today"] = False
    html = R.write_nset(html, nset)
    m = n500.N500_RE.search(html)
    if m and m.group(2).strip() not in ("null", ""):
        b = json.loads(m.group(2))
        qs = live["q"].get("NSE_EQ", {})
        for r in b.get("rows", []):
            q = qs.get(str(r.get("sid")))
            if q and q[0] > 0:
                r["last"] = q[0]
                if q[4] and b.get("asof") != day:
                    r["r1"] = q[0] / r.get("prev", q[4]) - 1 if r.get("prev") else r.get("r1")
        b["live_t"] = live["t"]
        html = n500.N500_RE.sub(lambda mm: mm.group(1) + json.dumps(b, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/") + mm.group(3), html, count=1)
    page.write_text(html, encoding="utf-8")
    print(f"applied live prices from {live['t']} IST to {k} series")
    return 0


if __name__ == "__main__":
    sys.exit(main())
