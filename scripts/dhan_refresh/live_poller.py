"""Live prices without the claude.ai Dhan connector.

Runs on GitHub Actions during market hours. Logs in once with TOTP (no human),
asks Dhan for LTP/OHLC of every Nifty 500 stock and the indices every few
seconds, and force-pushes a small live.json to the 'live' branch.

The terminal page reads that file through the GitHub connector, and a scheduled
republish copies it into the page for viewers without any connector.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import refresh as R

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "live-out"
IDX_RE = re.compile(r"const LIVE_IDX=(\{[^}]*\})")


def universe() -> tuple[list[int], dict]:
    """NSE_EQ security ids (Nifty 500 board + Nifty 50) and index ids from the page."""
    eq = set()
    n5 = ROOT / "docs/n500.json"
    if n5.exists():
        eq |= {int(r["sid"]) for r in json.loads(n5.read_text())["rows"] if r.get("sid")}
    html = (ROOT / "docs/nse-terminal.html").read_text(encoding="utf-8")
    m = re.search(r"const LIVE_EQ=(\{[^}]*\})", html)
    if m:
        eq |= {int(v) for v in json.loads(m.group(1)).values()}
    idx = {}
    m = IDX_RE.search(html)
    if m:
        idx = json.loads(re.sub(r"(\d+):", r'"\1":', m.group(1)))
    return sorted(eq), idx


def parse(resp: dict) -> dict:
    """{'NSE_EQ': {sid: [ltp, o, h, l, c]}, 'IDX_I': {...}} from Dhan's ohlc reply."""
    data = resp.get("data", resp)
    out = {}
    for seg, rows in (data or {}).items():
        if not isinstance(rows, dict):
            continue
        for sid, q in rows.items():
            if not isinstance(q, dict):
                continue
            o = q.get("ohlc") or {}
            ltp = float(q.get("last_price") or 0)
            if ltp > 0:
                out.setdefault(seg, {})[str(sid)] = [ltp, float(o.get("open") or 0), float(o.get("high") or 0),
                                                     float(o.get("low") or 0), float(o.get("close") or 0)]
    return out


def push(payload: dict) -> None:
    (OUT / "live.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    run = lambda *a: subprocess.run(["git", "-C", str(OUT), *a], check=True, capture_output=True)
    run("add", "live.json")
    run("commit", "-q", "--amend", "--no-edit", "--allow-empty")
    run("push", "-q", "-f", "origin", "HEAD:refs/heads/live")


def setup_branch() -> None:
    if OUT.exists():
        subprocess.run(["rm", "-rf", "--", str(OUT)], check=True)
    OUT.mkdir()
    url = subprocess.run(["git", "-C", str(ROOT), "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
    hdr = subprocess.run(["git", "-C", str(ROOT), "config", "--get-all", "http.https://github.com/.extraheader"], capture_output=True, text=True).stdout.strip()
    run = lambda *a: subprocess.run(["git", "-C", str(OUT), *a], check=True, capture_output=True)
    run("init", "-q")
    run("remote", "add", "origin", url)
    if hdr:
        run("config", "http.https://github.com/.extraheader", hdr)
    run("config", "user.name", "dhan-live-bot")
    run("config", "user.email", "dhan-live-bot@users.noreply.github.com")
    run("checkout", "-q", "--orphan", "live")
    (OUT / "live.json").write_text("{}", encoding="utf-8")
    run("add", "live.json")
    run("commit", "-q", "-m", "Live prices (single commit, force-pushed)")


def main() -> int:
    until = dt.time(*map(int, (sys.argv[sys.argv.index("--until") + 1] if "--until" in sys.argv else "15:35").split(":")))
    every = float(sys.argv[sys.argv.index("--every") + 1]) if "--every" in sys.argv else 5.0
    cid, pin, sec = (os.environ[k] for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"))
    eq, idx = universe()
    print(f"universe: {len(eq)} stocks, {len(idx)} indices; pushing every {every}s until {until}")
    dhan = R.Dhan(cid, R.login(cid, pin, sec))
    setup_branch()
    body = {"NSE_EQ": eq[:990], "IDX_I": [int(k) for k in idx]}
    n = fails = 0
    first = None
    while True:
        now = dt.datetime.now(R.IST)
        if now.time() >= until:
            break
        t0 = time.time()
        try:
            q = parse(dhan._post("/marketfeed/ohlc", body))
            if not q:
                raise R.RefreshError("empty reply")
            push({"t": now.strftime("%Y-%m-%d %H:%M:%S"), "d": now.date().isoformat(), "q": q})
            n += 1
            fails = 0
            if first is None:
                first = q
                print(f"first push: {sum(len(v) for v in q.values())} prices")
            # holiday: nothing has traded by 09:30 (every open is zero)
            if now.time() >= dt.time(9, 30) and n > 5 and all(v[1] == 0 for v in q.get("NSE_EQ", {}).values()):
                print("no trading today; stopping")
                break
        except Exception as e:
            if any(c in str(e) for c in ("401", "807", "808", "809", "DH-901")):
                print(f"login no longer valid (another job logged in?): {str(e)[:100]}; stopping")
                break
            fails += 1
            print(f"  {now:%H:%M:%S} poll failed ({fails}): {str(e)[:120]}")
            if fails >= 30:
                print("too many failures; stopping")
                return 1
            time.sleep(10)
        time.sleep(max(0.0, every - (time.time() - t0)))
    print(f"done: {n} pushes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
