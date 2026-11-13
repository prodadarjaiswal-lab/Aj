"""Track US stocks during the US session and alert on Telegram, using Dhan.

Runs on GitHub Actions with the same TOTP login as the NSE feed. Prices come from
Dhan's Global Stocks live feed (WebSocket, segment INX_EQ); security ids come from
Dhan's US instrument list. Levels and moves are set in config/us_watch.json. Each
alert fires once a day; the sent list is kept on the 'us-watch' branch.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import struct
import subprocess
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

import bot as B
import refresh as R
import telegram as T
from telegram import esc

ROOT = Path(__file__).resolve().parents[2]
NY = ZoneInfo("America/New_York")
IST = ZoneInfo("Asia/Kolkata")
OUT = ROOT / "us-watch-out"
FEED = "wss://global-stocks-api-feed.dhan.co/"
SCRIPS = "https://api-global-stocks.dhan.co/api-data/us-stock-scrip-master.csv"
SIZES = {1: 27, 3: 27, 29: 18, 32: 15, 33: 19, 36: 19, 50: 13}
ERRORS = {805: "connection limit exceeded", 806: "US data not enabled on this Dhan account", 807: "token expired",
          808: "authentication failed", 809: "invalid token"}


class DhanError(RuntimeError):
    pass


def config() -> dict:
    c = json.loads((ROOT / "config/us_watch.json").read_text(encoding="utf-8"))
    return {k: v for k, v in c.items() if not k.startswith("_")}


def security_ids(symbols: list) -> dict:
    """Map US tickers to Dhan security ids using Dhan's US instrument list."""
    text = requests.get(SCRIPS, timeout=60).text
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise DhanError("Dhan's US instrument list came back empty")
    cols = list(rows[0].keys())
    sym_cols = [c for c in cols if "SYMBOL" in c.upper() and "NAME" not in c.upper()] or cols
    # Dhan's US list keeps the security id in SCRIP_CODE (DhanHQ-py fetch_global_security_list)
    id_cols = [c for c in cols if c.upper() in ("SCRIP_CODE", "SECURITY_ID", "SECURITYID", "SM_SECURITY_ID")]
    if not id_cols:
        raise DhanError(f"no security id column in Dhan's US list; columns: {cols[:12]}")
    want = {s.upper(): s for s in symbols}
    out = {}
    for r in rows:
        for c in sym_cols:
            v = str(r.get(c, "")).strip().upper()
            if v in want and want[v] not in out:
                out[want[v]] = str(r[id_cols[0]]).strip()
                print(f"  {want[v]}: {r.get('EXCHANGE', '')} {r.get('SYMBOL_NAME', '')} id {out[want[v]]}")
    missing = [s for s in symbols if s not in out]
    if missing:
        print(f"  not in Dhan's US list: {missing}; columns: {cols[:12]}")
    return out


def parse(buf: bytes) -> list:
    """Decode Dhan Global Stocks binary packets (little-endian), as in DhanHQ-py's GlobalStocksFeed."""
    out, off = [], 0
    while off + 11 <= len(buf):
        code = buf[off + 10]
        exp = SIZES.get(code, 11)
        n = buf[off + 9] or exp
        if n < exp or off + n > len(buf):
            break
        p = buf[off:off + n]
        sid = str(struct.unpack("<i", p[1:5])[0])
        if code == 1:
            ltp, vol, ltt, _ = struct.unpack("<fiii", p[11:27])
            out.append({"k": "trade", "sid": sid, "ltp": round(ltp, 4), "vol": vol, "t": ltt})
        elif code == 3:
            o, c, h, lo = struct.unpack("<ffff", p[11:27])
            out.append({"k": "ohlc", "sid": sid, "open": round(o, 4), "close": round(c, 4), "high": round(h, 4), "low": round(lo, 4)})
        elif code == 32:
            out.append({"k": "prev", "sid": sid, "prev": round(struct.unpack("<f", p[11:15])[0], 4)})
        elif code == 50:
            err = struct.unpack("<h", p[11:13])[0]
            out.append({"k": "error", "sid": sid, "code": err, "msg": ERRORS.get(err, "unknown error")})
        off += n
    return out


class DhanUS:
    """Live US quotes from Dhan's Global Stocks feed."""

    def __init__(self, client_id: str, token: str, ids: dict):
        self.client_id, self.token, self.ids = client_id, token, ids
        self.by_sid = {v: k for k, v in ids.items()}
        self.q = {s: {"price": 0.0, "prev": 0.0, "high": 0.0, "low": 0.0, "t": 0} for s in ids}
        self.ws = None

    def connect(self) -> None:
        from websockets.sync.client import connect
        self.ws = connect(f"{FEED}?clientId={self.client_id}&token={self.token}&authType=2&version=2",
                          open_timeout=20, max_size=2 ** 20)
        for code in (15, 17):                      # 15 = trades, 17 = OHLC
            self.ws.send(json.dumps({"requestCode": code, "instrumentCount": len(self.ids),
                                     "instrumentList": [{"exchangeSegment": "INX_EQ", "securityId": v} for v in self.ids.values()]}))

    def pump(self, seconds: float) -> None:
        """Read packets for up to `seconds`, updating the latest quote per symbol."""
        end = time.time() + seconds
        while time.time() < end:
            try:
                msg = self.ws.recv(timeout=max(0.1, end - time.time()))
            except TimeoutError:
                return
            if isinstance(msg, str):
                continue
            for p in parse(msg):
                sym = self.by_sid.get(p["sid"])
                if p["k"] == "error":
                    raise DhanError(f"Dhan feed error {p['code']}: {p['msg']}")
                if not sym:
                    continue
                q = self.q[sym]
                if p["k"] == "trade" and p["ltp"] > 0:
                    q["price"], q["t"] = p["ltp"], p["t"]
                elif p["k"] == "ohlc":
                    q["high"], q["low"] = p["high"] or q["high"], p["low"] or q["low"]
                    if not q["price"] and p["close"] > 0:
                        q["price"] = p["close"]
                elif p["k"] == "prev" and p["prev"] > 0:
                    q["prev"] = p["prev"]

    def close(self) -> None:
        try:
            self.ws.send(json.dumps({"requestCode": 12}))
            self.ws.close()
        except Exception:
            pass


def dhan_login() -> tuple:
    cid, pin, sec = (os.environ[k] for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"))
    return cid, R.login(cid, pin, sec)


class Watch:
    def __init__(self, cfg: dict, sent: list | None = None):
        self.cfg = cfg
        self.sent = set(sent or [])
        self.prev: dict = {}

    def _once(self, key, text, out):
        if key not in self.sent:
            self.sent.add(key)
            out.append(text)

    def check(self, sym: str, q: dict, when: str) -> list:
        c, out = self.cfg[sym], []
        p = q["price"]
        prev = q["prev"] or self.prev.get(sym, 0)
        if q["prev"]:
            self.prev[sym] = q["prev"]
        chg = (p / prev - 1) * 100 if prev else 0.0
        name = esc(c.get("name", sym))
        why = c.get("why", {})
        for lv in sorted(c.get("below", []), reverse=True):
            if p <= lv:
                note = f" {esc(why[str(lv)])}." if str(lv) in why else ""
                self._once(f"{sym}:below:{lv}", f"🔻 <b>{name}</b> at ${p:,.2f}, at or below ${lv:,.0f} ({when}).{note}", out)
        for lv in sorted(c.get("above", [])):
            if p >= lv:
                note = f" {esc(why[str(lv)])}." if str(lv) in why else ""
                self._once(f"{sym}:above:{lv}", f"🔺 <b>{name}</b> at ${p:,.2f}, at or above ${lv:,.0f} ({when}).{note}", out)
        mv = c.get("move_pct", 3)
        if prev and abs(chg) >= mv:
            step = int(abs(chg) // mv) * mv           # alert again at 3%, 6%, 9% ...
            self._once(f"{sym}:move:{'+' if chg > 0 else '-'}{step}",
                       f"{'📈' if chg > 0 else '📉'} <b>{name}</b> {chg:+.1f}% at ${p:,.2f} ({when}).", out)
        return out


def line(sym: str, c: dict, q: dict) -> str:
    chg = f" ({(q['price'] / q['prev'] - 1) * 100:+.2f}%)" if q["prev"] else ""
    rng = f", day ${q['low']:,.2f}-${q['high']:,.2f}" if q["low"] and q["high"] else ""
    return f"<b>{esc(c.get('name', sym))}</b> ({sym}) ${q['price']:,.2f}{chg}{rng}"


def load_state(day: str) -> dict:
    try:
        subprocess.run(["git", "-C", str(ROOT), "fetch", "-q", "origin", "us-watch"], check=True, capture_output=True, timeout=60)
        st = json.loads(subprocess.run(["git", "-C", str(ROOT), "show", "FETCH_HEAD:state.json"],
                                       check=True, capture_output=True, text=True).stdout)
        if st.get("d") == day:
            return st
    except Exception:
        pass
    return {"d": day, "sent": []}


def save_state(st: dict) -> None:
    try:
        run = lambda *a: subprocess.run(["git", "-C", str(OUT), *a], check=True, capture_output=True)
        if not (OUT / ".git").exists():
            OUT.mkdir(exist_ok=True)
            url = subprocess.run(["git", "-C", str(ROOT), "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
            hdr = subprocess.run(["git", "-C", str(ROOT), "config", "--get-all", "http.https://github.com/.extraheader"],
                                 capture_output=True, text=True).stdout.strip()
            run("init", "-q")
            run("remote", "add", "origin", url)
            if hdr:
                run("config", "http.https://github.com/.extraheader", hdr)
            run("config", "user.name", "dhan-live-bot")
            run("config", "user.email", "dhan-live-bot@users.noreply.github.com")
            run("checkout", "-q", "--orphan", "us-watch")
        (OUT / "state.json").write_text(json.dumps(st), encoding="utf-8")
        run("add", "state.json")
        run("commit", "-q", "--allow-empty", "-m", "US watch state")
        run("push", "-q", "-f", "origin", "HEAD:refs/heads/us-watch")
    except Exception as e:
        print(f"  state not saved: {str(e)[:100]}")


DHAN_JOBS = ("dhan-refresh.yml", "tech-model.yml", "setup-backtest.yml")


def refresh_running() -> bool:
    """True while another Dhan job (nightly refresh or a back-test) runs; a new login would cancel its token."""
    for wf in DHAN_JOBS:
        try:
            r = subprocess.run(["gh", "run", "list", "--workflow", wf, "--status", "in_progress", "--json", "databaseId"],
                               capture_output=True, text=True, timeout=30, cwd=ROOT)
            if r.returncode == 0 and r.stdout.strip() not in ("", "[]"):
                return True
        except Exception:
            pass
    return False


_TOKEN = {}


def open_feed(cfg: dict, relogin: bool = False) -> DhanUS:
    import dhan_guard as G
    G.wait_for_batch_jobs(20)
    ids = security_ids(list(cfg))
    if not ids:
        raise DhanError("none of the symbols were found in Dhan's US instrument list")
    print(f"Dhan US ids: {ids}")
    if relogin or not _TOKEN:
        _TOKEN["cid"], _TOKEN["tok"] = dhan_login()
    feed = DhanUS(_TOKEN["cid"], _TOKEN["tok"], ids)
    feed.connect()
    return feed


def main() -> int:
    args = sys.argv[1:]
    cfg = config()
    if args[:1] == ["now"]:                       # one-off price message
        feed = open_feed(cfg)
        feed.pump(20)
        feed.close()
        msg = ["<b>US price check (Dhan)</b> · " + dt.datetime.now(IST).strftime("%d %b %H:%M IST")]
        for sym, c in cfg.items():
            q = feed.q.get(sym)
            msg.append(line(sym, c, q) if q and q["price"] else f"{esc(c.get('name', sym))}: no price from Dhan yet (market closed?)")
        print("\n".join(msg))
        return 0 if T.send("\n".join(msg)) else 1
    max_min = float(args[args.index("--max-minutes") + 1]) if "--max-minutes" in args else 345
    every = float(args[args.index("--every") + 1]) if "--every" in args else 30
    t_end = time.time() + max_min * 60
    day = dt.datetime.now(NY).date().isoformat()
    st = load_state(day)
    w = Watch(cfg, st["sent"])
    print(f"tracking {', '.join(cfg)} via Dhan; telegram {'on' if T.enabled() else 'off'}; {len(w.sent)} alerts already sent")
    while dt.datetime.now(NY).time() < dt.time(9, 25) and time.time() < t_end:
        time.sleep(30)                             # log in just before the open
    feed, fails, relogin = None, 0, False
    bot = B.Bot("US")

    def sync_symbols() -> bool:
        """Add US symbols the user asked for by chat; True when the feed must resubscribe."""
        added = False
        for x in bot.state["alerts"] + bot.state["watch"]:
            if x["mkt"] == "US" and x["sym"] not in cfg:
                cfg[x["sym"]] = {"name": x["sym"], "move_pct": 3}
                added = True
        bot.us_symbols = set(cfg)
        return added

    sync_symbols()
    while time.time() < t_end:
        now = dt.datetime.now(NY)
        if now.weekday() >= 5 or now.time() >= dt.time(16, 2):
            break
        try:
            if feed is None:
                feed = open_feed(cfg, relogin)
                relogin = False
            feed.pump(every)
            fails = 0
            for sym, q in feed.q.items():
                bot.quotes[sym] = (q["price"], q["prev"])
            bot.status_line = f"Last check {now.astimezone(IST):%H:%M:%S} IST."
            bot.poll()
            if sync_symbols():
                feed.close()
                feed = None                            # resubscribe with the new symbols, same login
                continue
        except DhanError as e:
            print(f"  {e}")
            if feed:
                feed.close()
            feed = None
            relogin = any(c in str(e) for c in ("807", "808", "809"))
            if "806" in str(e):
                T.send(f"US alerts stopped: {esc(e)}. Enable US stocks data in your Dhan account.")
                return 1
            time.sleep(300 if any(c in str(e) for c in ("807", "808", "809")) else 60)   # another job logged in; open_feed waits for it
            continue
        except Exception as e:
            fails += 1
            print(f"  feed problem ({fails}): {str(e)[:120]}")
            if feed:
                feed.close()
            feed = None
            if fails >= 20:
                T.send("US alerts stopped: the Dhan US feed kept failing. It restarts with the next scheduled run.")
                return 1
            time.sleep(30)
            continue
        if now.time() < dt.time(9, 30):
            continue
        when = f"{now:%H:%M} New York, {now.astimezone(IST):%H:%M} IST"
        n0, msgs = len(w.sent), []
        for sym in cfg:
            q = feed.q.get(sym)
            if q and q["price"]:
                msgs += w.check(sym, q, when)
        msgs += bot.check(when)
        if "open" not in w.sent and now.time() >= dt.time(9, 35) and any(q["price"] for q in feed.q.values()):
            w.sent.add("open")
            msgs.insert(0, "<b>US market open (Dhan)</b>\n" + "\n".join(line(s, cfg[s], q) for s, q in feed.q.items() if q["price"]))
        if msgs:
            T.send("\n".join(msgs))
        if len(w.sent) != n0:
            save_state({"d": day, "sent": sorted(w.sent)})
    now = dt.datetime.now(NY)
    if feed and now.time() >= dt.time(16, 0) and "close" not in w.sent:
        feed.pump(5)
        if T.send("<b>US close (Dhan)</b> · " + now.astimezone(IST).strftime("%H:%M IST") + "\n" +
                  "\n".join(line(s, cfg[s], q) for s, q in feed.q.items() if q["price"])):
            w.sent.add("close")
            save_state({"d": day, "sent": sorted(w.sent)})
    if feed:
        feed.close()
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
