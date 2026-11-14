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

import alerts as AL
import bot as B
import flow as FL
import dhan_guard as G
import refresh as R
import telegram as T

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


def push(payload: dict, state: dict | None = None, extra: dict | None = None) -> None:
    (OUT / "live.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    if state is not None:
        (OUT / "alerts.json").write_text(json.dumps(state), encoding="utf-8")
    for name, obj in (extra or {}).items():
        (OUT / name).write_text(json.dumps(obj, separators=(",", ":")), encoding="utf-8")
    run = lambda *a: subprocess.run(["git", "-C", str(OUT), *a], check=True, capture_output=True)
    files = [f for f in ("live.json", "alerts.json", "flow.json", "flow-state.json") if (OUT / f).exists()]
    run("add", *files)
    run("commit", "-q", "--amend", "--no-edit", "--allow-empty")
    run("push", "-q", "-f", "origin", "HEAD:refs/heads/live")


def prior_state(day: str) -> dict:
    """Alerts already sent today (kept on the live branch so a restarted job does not repeat them)."""
    try:
        subprocess.run(["git", "-C", str(ROOT), "fetch", "-q", "origin", "live"], check=True, capture_output=True, timeout=60)
        raw = subprocess.run(["git", "-C", str(ROOT), "show", "FETCH_HEAD:alerts.json"], check=True, capture_output=True, text=True).stdout
        st = json.loads(raw)
        if st.get("d") == day:
            return st
    except Exception:
        pass
    return {"d": day, "sent": []}


def prior_file(name: str, day: str) -> dict:
    try:
        subprocess.run(["git", "-C", str(ROOT), "fetch", "-q", "origin", "live"], check=True, capture_output=True, timeout=60)
        raw = subprocess.run(["git", "-C", str(ROOT), "show", f"FETCH_HEAD:{name}"], check=True, capture_output=True, text=True).stdout
        d = json.loads(raw)
        return d if d.get("d") == day else {}
    except Exception:
        return {}


def flow_ids(bot_state: dict, bysym: dict) -> list:
    """Nifty 50 (from the page) plus the stocks the owner watches, alerts on or asked about today."""
    html = (ROOT / "docs/nse-terminal.html").read_text(encoding="utf-8")
    m = re.search(r"const LIVE_EQ=(\{[^}]*\})", html)
    ids = [str(v) for v in json.loads(m.group(1)).values()] if m else []
    extra = [x["sym"] for x in bot_state.get("alerts", []) + bot_state.get("watch", []) if x.get("mkt") == "NSE"]
    extra += [x["sym"] for x in bot_state.get("journal", [])[-40:]]
    for sym in dict.fromkeys(extra):
        r = bysym.get(sym)
        if r and r.get("sid") and str(r["sid"]) not in ids:
            ids.append(str(r["sid"]))
    return ids[:90]


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
    day = dt.datetime.now(R.IST).date().isoformat()
    al = AL.Alerts(idx, prior_state(day)["sent"])
    print(f"telegram: {'on' if T.enabled() else 'off'}; {len(al.sent)} alerts already sent today")
    state = lambda: {"d": day, "sent": sorted(al.sent)}
    bot = B.Bot("NSE")
    fids = flow_ids(bot.state, al.bysym)
    fstate = prior_file("flow-state.json", day).get("s", {})
    flows = {sid: FL.Flow(fstate.get(sid)) for sid in fids}
    sym_of = {str(r["sid"]): r["s"] for r in al.bysid.values()} if hasattr(al, "bysid") else {}
    print(f"order flow: {len(fids)} stocks via /marketfeed/quote")
    try:                                                        # last Dhan US prices, for 'price NVDA' during NSE hours
        subprocess.run(["git", "-C", str(ROOT), "fetch", "-q", "origin", "us-watch"], capture_output=True, timeout=60)
        us_st = json.loads(subprocess.run(["git", "-C", str(ROOT), "show", "FETCH_HEAD:state.json"],
                                          capture_output=True, text=True).stdout or "{}")
        bot.us_quotes = {s: {**v, "live": False} for s, v in (us_st.get("quotes") or {}).items()}
        bot.us_symbols = set(bot.us_quotes)
    except Exception:
        pass
    flow_out = {}
    n = fails = relogins = 0
    first = last_q = None
    reached_end = False
    while True:
        now = dt.datetime.now(R.IST)
        if now.time() >= until:
            reached_end = True
            break
        t0 = time.time()
        try:
            q = parse(dhan._post("/marketfeed/ohlc", body))
            if not q:
                raise R.RefreshError("empty reply")
            last_q = q
            hhmm = now.strftime("%H:%M")
            for sid, v in q.get("NSE_EQ", {}).items():
                r = al.bysid.get(sid)
                if r:
                    bot.quotes[r["s"]] = (v[0], al.base("NSE_EQ", sid, v, hhmm))
            bot.status_line = f"Last price {now:%H:%M:%S} IST."
            ix = q.get("IDX_I", {})
            bot.live_index = {k: ix[s_][0] for k, s_ in (("NIFTY", "13"), ("BANKNIFTY", "25")) if s_ in ix and ix[s_][0] > 0}
            bot.feed_note = ""
            bot.poll()                                         # Telegram is answered by this job during market hours
            al.watch |= {str(al.bysym[x["sym"]]["sid"]) for x in bot.state["watch"] if x["mkt"] == "NSE" and x["sym"] in al.bysym}
            fired = bot.check(hhmm)
            if fired:
                T.send("\n".join(fired))
            traded = any(v[1] > 0 for v in q.get("NSE_EQ", {}).values())
            if traded and "brief" not in al.sent and now.time() < dt.time(12, 0):
                html = (ROOT / "docs/nse-terminal.html").read_text(encoding="utf-8")
                if T.send(AL.morning_brief(R.read_nset(html))):
                    al.sent.add("brief")
            if traded and now.time() >= dt.time(9, 15):
                msgs = al.check(q, hhmm)
                if msgs:
                    T.send("\n".join(msgs))
            extra = {}
            if traded and dt.time(9, 15) <= now.time() <= dt.time(15, 31) and fids:
                try:
                    time.sleep(1.1)                                    # Dhan: one quote request per second
                    rq = dhan._post("/marketfeed/quote", {"NSE_EQ": [int(x) for x in fids]})
                    for sid, qq in ((rq.get("data") or {}).get("NSE_EQ") or {}).items():
                        if str(sid) in flows:
                            flows[str(sid)].update(now.strftime("%H:%M:%S"), qq)
                except Exception as e:
                    if any(c in str(e) for c in ("401", "807", "808", "809", "DH-901")):
                        raise
                    print(f"  quote (order flow) failed: {str(e)[:80]}")
                if n % 12 == 0:
                    flow_out = {"d": day, "t": now.strftime("%H:%M:%S"), "basis": "snapshot-derived from Dhan quotes every 5 s",
                                "s": {sym_of.get(sid, sid): f.summary() for sid, f in flows.items() if f.tape}}
                    extra["flow.json"] = flow_out
                    bot.live_flow = flow_out
                if n % 60 == 0:
                    extra["flow-state.json"] = {"d": day, "s": {sid: f.state() for sid, f in flows.items()}}
            push({"t": now.strftime("%Y-%m-%d %H:%M:%S"), "d": now.date().isoformat(), "q": q}, state(), extra)
            n += 1
            fails = 0
            if n % 60 == 0 and G.newer_run("live-feed.yml"):      # the planned hand-over: stop so alerts are not doubled
                print("a newer live job is running; stopping")
                break
            if first is None:
                first = q
                print(f"first push: {sum(len(v) for v in q.values())} prices")
            # holiday: nothing has traded by 09:30 (every open is zero)
            if now.time() >= dt.time(9, 30) and n > 5 and all(v[1] == 0 for v in q.get("NSE_EQ", {}).values()):
                print("no trading today; stopping")
                break
        except Exception as e:
            if any(c in str(e) for c in ("401", "807", "808", "809", "DH-901")):
                if G.newer_run("live-feed.yml"):
                    print("a newer live job has taken over the login; stopping")
                    break
                # an accidental clash (a manual refresh, a back-test): wait for it, then log back in
                relogins += 1
                print(f"login lost ({str(e)[:80]}); re-login {relogins}")
                if relogins > 6:
                    T.send("⚠️ NSE live prices stopped: the Dhan login kept being taken by another job.")
                    return 1
                G.wait_for_batch_jobs()
                try:
                    dhan = R.Dhan(cid, R.login(cid, pin, sec))   # takes the shared session if another job refreshed it
                    if relogins > 1:
                        time.sleep(125)                          # Dhan issues one new token per 2 minutes
                    print("  logged in again")
                except Exception as e2:
                    print(f"  re-login failed: {str(e2)[:100]}")
                continue
            fails += 1
            print(f"  {now:%H:%M:%S} poll failed ({fails}): {str(e)[:120]}")
            if fails >= 30:
                print("too many failures; stopping")
                return 1
            time.sleep(10)
        time.sleep(max(0.0, every - (time.time() - t0)))
    if reached_end and until >= dt.time(15, 30) and last_q and "close" not in al.sent:
        if T.send(AL.close_summary(last_q, idx, al.prev)):
            al.sent.add("close")
            try:
                push({"t": dt.datetime.now(R.IST).strftime("%Y-%m-%d %H:%M:%S"), "d": day, "q": last_q}, state())
            except Exception as e:
                print(f"final push failed: {str(e)[:100]}")
    print(f"done: {n} pushes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
