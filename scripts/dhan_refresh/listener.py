"""The always-on Telegram listener.

Runs as back-to-back GitHub Actions jobs (bot-listener.yml). Long-polls Telegram
and answers every command at any hour:
  * NSE prices: live from the 'live' branch (written by the Dhan live feed) when it is
    fresh; otherwise the last Dhan close, with the reason ("market closed" / "feed not running").
  * US prices: from the 'us-watch' branch (written by the Dhan US tracker).
  * Everything else from the nightly files (re-read every 30 minutes with git pull).
Prices only ever come from Dhan; when Dhan data is missing the reply says so.
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

import bot as B
import telegram as T

ROOT = Path(__file__).resolve().parents[2]
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def _show(branch: str, path: str):
    try:
        subprocess.run(["git", "-C", str(ROOT), "fetch", "-q", "origin", branch], check=True, capture_output=True, timeout=40)
        return json.loads(subprocess.run(["git", "-C", str(ROOT), "show", f"FETCH_HEAD:{path}"],
                                         check=True, capture_output=True, text=True).stdout)
    except Exception:
        return None


def market_note(now: dt.datetime) -> str:
    if now.weekday() >= 5:
        return "Market closed for the weekend"
    if now.time() < dt.time(9, 15):
        return "Market opens at 09:15 IST"
    if now.time() > dt.time(15, 30):
        return "Market closed for the day"
    return "Live feed not running right now; showing the last Dhan close"


def live_quotes(b: B.Bot, now: dt.datetime) -> None:
    """Load NSE (live branch) and US (us-watch branch) Dhan prices into the bot."""
    b.quotes, b.feed_note = {}, market_note(now)
    lv = _show("live", "live.json")
    if lv and lv.get("t"):
        try:
            age = (now.replace(tzinfo=None) - dt.datetime.strptime(lv["t"], "%Y-%m-%d %H:%M:%S")).total_seconds()
        except ValueError:
            age = 1e9
        if age <= 120:
            bysid = {str(r["sid"]): r["s"] for r in b.d.rows if r.get("sid")}
            for sid, v in (lv.get("q") or {}).get("NSE_EQ", {}).items():
                if sid in bysid and v[0] > 0:
                    b.quotes[bysid[sid]] = (v[0], v[4] if now.time() < dt.time(15, 29) else (b.d.bysym[bysid[sid]].get("last") or 0))
            b.feed_note = ""
    us = _show("us-watch", "state.json") or {}
    b.us_quotes = {}
    for s, q in (us.get("quotes") or {}).items():
        try:
            fresh = (dt.datetime.now(dt.timezone.utc) - dt.datetime.strptime(q["t"], "%Y-%m-%d %H:%M IST").replace(tzinfo=IST)).total_seconds() <= 180
        except Exception:
            fresh = False
        b.us_quotes[s] = {**q, "live": fresh}
    b.us_symbols = set(b.us_quotes) | set(json.loads((ROOT / "config/us_watch.json").read_text()).keys()) - {"_note"}


def main() -> int:
    minutes = float(sys.argv[sys.argv.index("--minutes") + 1]) if "--minutes" in sys.argv else 340
    end = time.time() + minutes * 60
    if not T.enabled():
        print("telegram not set up")
        return 1
    b = B.Bot("ANY")
    last_data = time.time()
    print(f"listening; offset {b.state.get('offset')}")
    while time.time() < end:
        if time.time() - last_data > 1800:                # nightly files change: re-read every 30 minutes
            subprocess.run(["git", "-C", str(ROOT), "pull", "-q", "--ff-only", "origin", "main"], capture_output=True, timeout=60)
            b.d = B.Data()
            last_data = time.time()
        try:
            ups = T.call("getUpdates", offset=b.state["offset"], timeout=50, allowed_updates=["message"])
        except Exception as e:
            print(f"  poll failed: {str(e)[:100]}")
            time.sleep(10)
            continue
        mine = [u for u in ups if str(((u.get("message") or {}).get("chat") or {}).get("id")) == str(T.chat_id())]
        if ups:
            b.state["offset"] = ups[-1]["update_id"] + 1
            b.dirty = True
        if mine:
            st_ = B.load_state()                          # alerts may have been removed by a price job
            if st_:
                b.state = {**st_, "offset": b.state["offset"]}
            live_quotes(b, dt.datetime.now(IST))
        for u in mine:
            text = (u.get("message") or {}).get("text")
            if not text:
                continue
            try:
                reply = b.handle(text)
            except Exception as e:
                reply = f"Something went wrong with that command: {B.esc(str(e)[:100])}"
            T.send(reply)
        if b.dirty:
            B.save_state(b.state)
            b.dirty = False
    print("done; the next run takes over")
    return 0


if __name__ == "__main__":
    sys.exit(main())
