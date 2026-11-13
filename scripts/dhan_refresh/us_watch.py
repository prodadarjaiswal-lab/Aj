"""Track US stocks during the US session and alert on Telegram.

Runs on GitHub Actions. Prices come from Yahoo Finance's public chart endpoint
(about 1-minute fresh; Stooq as a fallback for the last price). Levels and moves
are set in config/us_watch.json. Each alert fires once per day; the sent list is
kept on the 'us-watch' branch so a second run does not repeat it.
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

import telegram as T
from telegram import esc

ROOT = Path(__file__).resolve().parents[2]
NY = ZoneInfo("America/New_York")
IST = ZoneInfo("Asia/Kolkata")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
OUT = ROOT / "us-watch-out"


def config() -> dict:
    c = json.loads((ROOT / "config/us_watch.json").read_text(encoding="utf-8"))
    return {k: v for k, v in c.items() if not k.startswith("_")}


def parse_yahoo(data: dict) -> dict:
    m = data["chart"]["result"][0]["meta"]
    return {"price": float(m["regularMarketPrice"]),
            "prev": float(m.get("chartPreviousClose") or m.get("previousClose") or 0),
            "high": float(m.get("regularMarketDayHigh") or 0),
            "low": float(m.get("regularMarketDayLow") or 0),
            "t": int(m.get("regularMarketTime") or 0)}


def quote(sym: str) -> dict:
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}", params={"interval": "1m", "range": "1d"},
                         headers=UA, timeout=15)
        r.raise_for_status()
        return parse_yahoo(r.json())
    except Exception as e:
        print(f"  yahoo {sym}: {str(e)[:100]}; trying stooq")
    r = requests.get("https://stooq.com/q/l/", params={"s": f"{sym.lower()}.us", "f": "sd2t2ohlcv", "h": "", "e": "csv"},
                     headers=UA, timeout=15)
    head, row = r.text.strip().splitlines()[:2]
    d = dict(zip(head.lower().split(","), row.split(",")))
    return {"price": float(d["close"]), "prev": 0.0, "high": float(d["high"]), "low": float(d["low"]), "t": 0}


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


def main() -> int:
    args = sys.argv[1:]
    cfg = config()
    if args[:1] == ["now"]:                       # one-off price message
        msg = ["<b>US price check</b> · " + dt.datetime.now(IST).strftime("%d %b %H:%M IST")]
        for sym, c in cfg.items():
            msg.append(line(sym, c, quote(sym)))
        print("\n".join(msg))
        return 0 if T.send("\n".join(msg)) else 1
    max_min = float(args[args.index("--max-minutes") + 1]) if "--max-minutes" in args else 345
    every = float(args[args.index("--every") + 1]) if "--every" in args else 60
    t_end = time.time() + max_min * 60
    day = dt.datetime.now(NY).date().isoformat()
    st = load_state(day)
    w = Watch(cfg, st["sent"])
    print(f"tracking {', '.join(cfg)}; telegram {'on' if T.enabled() else 'off'}; {len(w.sent)} alerts already sent")
    last = {}
    while time.time() < t_end:
        now = dt.datetime.now(NY)
        if now.weekday() >= 5 or now.time() >= dt.time(16, 5):
            break
        if now.time() < dt.time(9, 30):
            time.sleep(min(every, 60))
            continue
        when = f"{now:%H:%M} New York, {now.astimezone(IST):%H:%M} IST"
        msgs, changed = [], False
        for sym in cfg:
            try:
                q = quote(sym)
            except Exception as e:
                print(f"  {sym}: {str(e)[:100]}")
                continue
            if q["t"] and dt.datetime.fromtimestamp(q["t"], NY).date() != now.date():
                print("  no trading today (holiday); stopping")
                return 0
            last[sym] = q
            n0 = len(w.sent)
            msgs += w.check(sym, q, when)
            changed |= len(w.sent) != n0
        if last and "open" not in w.sent and now.time() >= dt.time(9, 35):
            w.sent.add("open")
            msgs.insert(0, "<b>US market open</b>\n" + "\n".join(line(s, cfg[s], q) for s, q in last.items()))
            changed = True
        if msgs:
            T.send("\n".join(msgs))
        if changed:
            save_state({"d": day, "sent": sorted(w.sent)})
        time.sleep(every)
    now = dt.datetime.now(NY)
    if now.time() >= dt.time(16, 0) and last and "close" not in w.sent:
        if T.send("<b>US close</b> · " + now.astimezone(IST).strftime("%H:%M IST") + "\n" +
                  "\n".join(line(s, cfg[s], quote(s)) for s in cfg)):
            w.sent.add("close")
            save_state({"d": day, "sent": sorted(w.sent)})
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
