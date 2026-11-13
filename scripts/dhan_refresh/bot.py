"""Two-way Telegram bot: reads the owner's messages and answers from the terminal's data.

The price jobs (live_poller for NSE, us_watch for US) call Bot.poll() every few
seconds. Commands are fixed words, no AI. User alerts, the watch list and the
Telegram read position are kept in bot.json on the 'bot' branch, so they survive
restarts and are shared by both jobs.
"""
from __future__ import annotations

import glob
import json
import re
import subprocess
from pathlib import Path

import telegram as T
from telegram import esc

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "bot-out"
EDGE = ("volbreak", "pullback")
SETUP = {"volbreak": "volume breakout", "pullback": "pullback in an uptrend", "breakout": "breakout",
         "coiled": "coiled range", "turn": "turn up"}
STATUS = {"lead": "a leader", "improve": "improving", "neutral": "neutral", "fade": "fading", "weak": "weak"}

HELP = """<b>Commands</b>
<code>price TCS</code>  latest price (NSE in market hours, US in the US session)
<code>TCS</code>  trade verdict (technical)
<code>value TCS</code>  investing verdict (valuation, Nifty 50 stocks)
<code>top</code>  today's top 5 tested setups
<code>hedge TCS</code>  ways to hedge a position
<code>alert TCS above 3450</code>  one-time price alert (also: below)
<code>watch RELIANCE</code>  alert on 3% moves
<code>my alerts</code>  list alerts and watched stocks
<code>remove 2</code>  delete alert number 2
<code>status</code>  what is running
Research, not advice."""

MENU = [("top", "Today's top 5 tested setups"), ("myalerts", "List my alerts and watched stocks"),
        ("status", "What is running"), ("help", "All commands with examples")]


def _load(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


class Data:
    """Read-only view of what the nightly jobs produced."""

    def __init__(self, board: dict | None = None, nset: dict | None = None, opts: dict | None = None):
        if board is None:
            board = _load(ROOT / "docs/n500.json", {"rows": []})
        if nset is None:
            try:
                import refresh as R
                nset = R.read_nset((ROOT / "docs/nse-terminal.html").read_text(encoding="utf-8"))
            except Exception:
                nset = {}
        if opts is None:
            files = sorted(glob.glob(str(ROOT / "data/options/*.json")))
            opts = _load(files[-1], {}) if files else {}
        self.asof = board.get("asof", "?")
        self.rows = board.get("rows", [])
        self.bysym = {r["s"]: r for r in self.rows}
        self.stocks = nset.get("stocks", {})
        self.opts = opts.get("rows", {})
        self.opts_date = opts.get("date", "")

    def find(self, word: str):
        w = word.upper().strip()
        if w in self.bysym:
            return self.bysym[w]
        hits = [r for r in self.rows if w in r["name"].upper().split() or r["name"].upper().startswith(w)]
        return hits[0] if len(hits) == 1 else None


def rupee(x) -> str:
    return f"₹{x:,.1f}" if x < 1000 else f"₹{x:,.0f}"


def top(d: Data) -> str:
    good = [r for r in d.rows if r.get("setup") in EDGE and r.get("status") in ("lead", "improve") and r.get("trig")]
    good.sort(key=lambda r: -(r.get("score") or 0))
    if not good:
        return f"No tested setups on leading stocks (data to {esc(d.asof)}). Sitting out is a position."
    lines = [f"<b>Top tested setups</b> · data to {esc(d.asof)}"]
    for i, r in enumerate(good[:5], 1):
        where = "above" if r["last"] > r["trig"] else "below"
        lines.append(f"{i}. <b>{esc(r['s'])}</b> {rupee(r['last'])}, {SETUP[r['setup']]}; {where} its trigger {rupee(r['trig'])}, "
                     f"off below {rupee(r['fail'])} (score {r.get('score')})")
    lines.append("Send a symbol for its verdict. Edge in the 6-year test: about +0.5% to +0.7% over 21 days in rising markets.")
    return "\n".join(lines)


def options_line(d: Data, sym: str, last: float) -> str:
    o = d.opts.get(sym)
    if not o:
        return ""
    bits = [f"Options ({esc(o.get('expiry', ''))}): market expects ±{o['exp_move'] * 100:.1f}% by expiry"]
    if o.get("pcr_oi"):
        bits.append(f"put/call open interest {o['pcr_oi']:.2f}")
    if o.get("call_wall") and o.get("put_wall"):
        bits.append(f"heaviest calls at {o['call_wall']:,.0f}, puts at {o['put_wall']:,.0f}")
    return ", ".join(bits) + "."


def technical(d: Data, r: dict, ltp: float | None = None) -> str:
    last = ltp or r["last"]
    st, setup = r.get("status"), r.get("setup")
    lines = [f"<b>{esc(r['s'])}</b> {rupee(last)} · trade view"]
    if st in ("lead", "improve") and setup in EDGE and last > r["fail"]:
        if last > r["trig"] * 1.05:
            call = f"<b>Wait.</b> It has a tested setup but is {((last / r['trig']) - 1) * 100:.0f}% past the trigger. Buy on a pullback towards {rupee(r['trig'])}."
        elif last > r["trig"]:
            call = f"<b>Buy candidate.</b> {SETUP[setup].capitalize()} is live above {rupee(r['trig'])}. Stop below {rupee(r['fail'])}."
        else:
            call = f"<b>Buy only above {rupee(r['trig'])}.</b> {SETUP[setup].capitalize()} is set up but not triggered. Stop below {rupee(r['fail'])}."
    elif st in ("lead", "improve"):
        extra = f" It shows a {SETUP[setup]}, a pattern with no tested edge." if setup else ""
        call = f"<b>No entry now.</b> The stock is {STATUS[st]} but has no tested setup today.{extra}"
    elif st == "neutral":
        call = "<b>No trade.</b> Neither leading nor weak; nothing to act on."
    else:
        call = f"<b>Avoid for a trade.</b> The stock is {STATUS.get(st, st)} against the Nifty 500."
    lines.append(call)
    facts = [f"rank {r.get('rank')} of {len(d.rows)} (score {r.get('score')})"]
    if r.get("vs50") is not None:
        facts.append(f"{r['vs50'] * 100:+.0f}% vs 50-day avg, {r['vs200'] * 100:+.0f}% vs 200-day")
    if r.get("rsi") is not None:
        facts.append(f"RSI {r['rsi']:.0f}")
    if r.get("rs3") is not None:
        facts.append(f"3-month return vs Nifty 500 {r['rs3'] * 100:+.0f}%")
    if r.get("hi52") is not None:
        facts.append(f"{-r['hi52'] * 100:.0f}% below its 52-week high")
    lines.append("Why: " + "; ".join(facts) + ".")
    ol = options_line(d, r["s"], last)
    if ol:
        lines.append(ol)
    lines.append(f"Data to {esc(d.asof)} close. For the investing view send: value {esc(r['s'])}")
    return "\n".join(lines)


def value(d: Data, sym: str, ltp: float | None = None) -> str:
    s = d.stocks.get(sym)
    if not s or not s.get("val"):
        return f"The investing view covers the Nifty 50 stocks for now; {esc(sym)} is not one of them. Send {esc(sym)} for the trade view."
    v = s["val"]
    last = ltp or (s.get("ohlc", {}).get("c") or [0])[-1]
    lines = [f"<b>{esc(sym)}</b> {rupee(last)} · investing view"]
    gap = v.get("gap")
    if gap is None:
        call = "<b>No verdict.</b> Not enough history to compare price with growth."
    elif gap <= -0.03:
        call = "<b>Reasonable to accumulate.</b> The price needs less growth than the company has delivered."
    elif gap < 0.05:
        call = "<b>Fairly priced.</b> The price needs about the growth the company has delivered."
    else:
        call = "<b>Expensive.</b> The price needs faster growth than the company has delivered."
    lines.append(call)
    facts = []
    if v.get("g_impl") is not None and v.get("g3") is not None:
        facts.append(f"price needs {v['g_impl'] * 100:.0f}% a year growth for 10 years; 3-year delivered growth is {v['g3'] * 100:.0f}%")
    if v.get("pe") and v.get("pe_med"):
        facts.append(f"P/E {v['pe']:.0f} against its own median {v['pe_med']:.0f}")
    if v.get("fair_at_g3"):
        facts.append(f"value if growth continues at the delivered rate: {rupee(v['fair_at_g3'])}")
    if facts:
        lines.append("Why: " + "; ".join(facts) + ".")
    if s.get("signal"):
        lines.append(f"Terminal label: {esc(s['signal'])}.")
    lines.append(f"Full five-method model: Fair Value Workbench. For the trade view send: {esc(sym)}")
    return "\n".join(lines)


def hedge(d: Data, r: dict, ltp: float | None = None) -> str:
    sym, last = r["s"], ltp or r["last"]
    beta = (d.stocks.get(sym, {}).get("val") or {}).get("beta")
    o = d.opts.get(sym)
    lines = [f"<b>Hedging {esc(sym)}</b> at {rupee(last)}, per ₹1,00,000 held"]
    if r.get("fail") and r["fail"] < last:
        lines.append(f"1. <b>Stop-loss (free):</b> exit below {rupee(r['fail'])}, a loss of about {(1 - r['fail'] / last) * 100:.0f}%.")
    else:
        lines.append("1. <b>Stop-loss (free):</b> decide the exit price before you buy; 1.5 to 2 times the daily range below entry is common.")
    if o:
        cost = o["straddle"] / 2 / o["spot"] * 100
        lines.append(f"2. <b>Protective put:</b> {esc(sym)} has options. An at-the-money put to {esc(o['expiry'])} costs roughly {cost:.1f}% "
                     f"of the position and caps the loss at about that. Implied volatility {o['iv_put']:.0f}%.")
    else:
        lines.append(f"2. <b>Protective put:</b> no option data for {esc(sym)} in the nightly snapshot, so a stock put may not be available.")
    b = beta or 1.0
    nf = d.opts.get("NIFTY")
    nline = f"3. <b>Market hedge:</b> short about ₹{b * 100000:,.0f} of Nifty (beta {b:.2f}{'' if beta else ', assumed'}) with futures or a Nifty put. " \
            "This removes market risk, not the stock's own risk."
    if nf:
        nline += f" A Nifty at-the-money put to {esc(nf['expiry'])} costs roughly {nf['straddle'] / 2 / nf['spot'] * 100:.1f}%."
    lines.append(nline)
    lines.append("4. <b>Another asset class:</b> keep part of the money in gold or a liquid fund. Gold has tended to hold up when Indian "
                 "equities fall, but it is a cushion, not a matched hedge.")
    lines.append("Lot sizes make option and futures hedges practical only for larger positions. Research, not advice.")
    return "\n".join(lines)


class Bot:
    """Polls Telegram, answers commands, and checks user alerts against live prices."""

    def __init__(self, market: str, data: Data | None = None, state: dict | None = None):
        self.market = market                      # "NSE" or "US"
        self.d = data or Data()
        self.state = state if state is not None else load_state()
        self.state.setdefault("offset", 0)
        self.state.setdefault("alerts", [])
        self.state.setdefault("watch", [])
        self.dirty = False
        self.quotes = {}                          # NSE: {sym: (ltp, prev)}; US: {sym: (ltp, prev)}
        self.us_symbols = set()
        self.status_line = ""

    # -- Telegram ---------------------------------------------------------
    def poll(self) -> int:
        """Fetch new messages and reply. Returns the number handled. Never raises."""
        if not T.enabled():
            return 0
        try:
            ups = T.call("getUpdates", offset=self.state["offset"], timeout=0, allowed_updates=["message"])
        except Exception as e:
            print(f"bot: poll failed: {str(e)[:100]}")
            return 0
        n = 0
        for u in ups:
            self.state["offset"] = u["update_id"] + 1
            self.dirty = True
            m = u.get("message") or {}
            if str((m.get("chat") or {}).get("id")) != str(T.chat_id()) or not m.get("text"):
                continue
            try:
                reply = self.handle(m["text"])
            except Exception as e:
                reply = f"Something went wrong with that command: {esc(str(e)[:100])}"
            if reply:
                T.send(reply)
                n += 1
        if self.dirty:
            save_state(self.state)
            self.dirty = False
        return n

    # -- commands ---------------------------------------------------------
    def is_us(self, sym: str) -> bool:
        return sym in self.us_symbols or any(a["sym"] == sym and a["mkt"] == "US" for a in self.state["alerts"])

    def price(self, word: str) -> str:
        sym = word.upper()
        if sym in self.quotes and self.quotes[sym][0]:
            ltp, prev = self.quotes[sym]
            chg = f" ({(ltp / prev - 1) * 100:+.2f}%)" if prev else ""
            cur = "$" if self.market == "US" else "₹"
            return f"<b>{esc(sym)}</b> {cur}{ltp:,.2f}{chg} (Dhan, live)"
        r = self.d.find(word)
        if r:
            return f"<b>{esc(r['s'])}</b> {rupee(r['last'])} at the {esc(self.d.asof)} close. Live NSE prices are answered 09:15 to 15:30 IST."
        if self.market == "US":
            return f"{esc(sym)} is not tracked yet. Send: watch {esc(sym)} us"
        return f"I don't know {esc(sym)}. NSE: Nifty 500 symbols. US stocks are answered during the US session; add one with: watch {esc(sym)} us"

    def handle(self, text: str) -> str:
        t = re.sub(r"\s+", " ", text.strip())
        low = t.lower().lstrip("/")
        w = low.split(" ")
        if low in ("help", "start", "hi", "hello", "commands"):
            return HELP
        if low in ("top", "picks", "top 5", "top5", "buys"):
            return top(self.d)
        if low in ("my alerts", "myalerts", "alerts", "list"):
            return self.list_alerts()
        if low == "status":
            return self.status()
        if w[0] == "price" and len(w) >= 2:
            return self.price(w[1])
        if w[0] in ("value", "invest") and len(w) >= 2:
            r = self.d.find(w[1])
            return value(self.d, r["s"] if r else w[1].upper(), self.ltp(r["s"]) if r else None)
        if w[0] in ("technical", "trade", "verdict") and len(w) >= 2:
            return self.tech(w[1])
        if w[0] == "hedge" and len(w) >= 2:
            r = self.d.find(w[1])
            return hedge(self.d, r, self.ltp(r["s"])) if r else f"I don't know {esc(w[1].upper())}. Hedge works for Nifty 500 stocks."
        if w[0] == "alert":
            m = re.match(r"alert (\S+) (above|below|over|under|>|<) ?\$?₹?([\d.,]+)( us)?$", low)
            if not m:
                return "Use: <code>alert TCS above 3450</code> or <code>alert NVDA below 150</code>"
            return self.add_alert(m.group(1).upper(), "above" if m.group(2) in ("above", "over", ">") else "below",
                                  float(m.group(3).replace(",", "")), bool(m.group(4)))
        if w[0] == "watch" and len(w) >= 2:
            return self.add_watch(w[1].upper(), len(w) > 2 and w[2] == "us")
        if w[0] in ("remove", "delete") and len(w) == 2 and w[1].isdigit():
            return self.remove(int(w[1]))
        if len(w) == 1 and re.fullmatch(r"[a-z0-9&\-]{2,15}", w[0]):
            if self.d.find(w[0]):
                return self.tech(w[0])
            if w[0].upper() in self.quotes:
                return self.price(w[0])
        return "I didn't understand that. Send <code>help</code> for the commands."

    def ltp(self, sym: str):
        q = self.quotes.get(sym)
        return q[0] if q and q[0] else None

    def tech(self, word: str) -> str:
        r = self.d.find(word)
        if not r:
            return f"I don't know {esc(word.upper())}. The trade view covers Nifty 500 stocks."
        return technical(self.d, r, self.ltp(r["s"]))

    def market_of(self, sym: str, us_flag: bool) -> str | None:
        if us_flag or self.is_us(sym):
            return "US"
        return "NSE" if sym in self.d.bysym else None

    def add_alert(self, sym: str, side: str, level: float, us_flag: bool) -> str:
        mkt = self.market_of(sym, us_flag)
        if not mkt:
            return f"I don't know {esc(sym)}. For a US stock add 'us': <code>alert {esc(sym)} {side} {level:g} us</code>"
        if len(self.state["alerts"]) >= 40:
            return "You have 40 alerts already. Remove one first (send: my alerts)."
        self.state["alerts"].append({"sym": sym, "mkt": mkt, "side": side, "level": level})
        self.dirty = True
        cur = "$" if mkt == "US" else "₹"
        when = "" if mkt == self.market else f" It is checked during the {mkt} session."
        return f"Done. One message when {esc(sym)} goes {side} {cur}{level:,.2f}.{when}"

    def add_watch(self, sym: str, us_flag: bool) -> str:
        mkt = self.market_of(sym, us_flag)
        if not mkt:
            return f"I don't know {esc(sym)}. For a US stock: <code>watch {esc(sym)} us</code>"
        if not any(x["sym"] == sym for x in self.state["watch"]):
            self.state["watch"].append({"sym": sym, "mkt": mkt})
            self.dirty = True
        return f"Watching {esc(sym)} ({mkt}). You get a message on a 3% move in a day."

    def list_alerts(self) -> str:
        a, wt = self.state["alerts"], self.state["watch"]
        if not a and not wt:
            return "No alerts yet. Try: <code>alert TCS above 3450</code>"
        lines = ["<b>Your alerts</b>"]
        for i, x in enumerate(a, 1):
            lines.append(f"{i}. {esc(x['sym'])} {x['side']} {'$' if x['mkt'] == 'US' else '₹'}{x['level']:,.2f}")
        if wt:
            lines.append("Watching: " + ", ".join(esc(x["sym"]) for x in wt))
        lines.append("Delete one with: <code>remove 1</code>")
        return "\n".join(lines)

    def remove(self, i: int) -> str:
        a = self.state["alerts"]
        if not 1 <= i <= len(a):
            return "No alert with that number. Send: my alerts"
        x = a.pop(i - 1)
        self.dirty = True
        return f"Removed: {esc(x['sym'])} {x['side']} {x['level']:,.2f}"

    def status(self) -> str:
        return (f"{self.market} price job: running. {self.status_line}\n"
                f"Board data to {esc(self.d.asof)} close; options snapshot {esc(self.d.opts_date or 'none')}.\n"
                f"{len(self.state['alerts'])} alerts, {len(self.state['watch'])} watched.\n"
                "I answer while a price job runs: NSE 09:07 to 15:35 IST, US session from about 19:55 IST.")

    # -- user alerts ------------------------------------------------------
    def check(self, when: str) -> list:
        """Fire user alerts for this market against self.quotes. Each fires once, then is deleted."""
        out, keep = [], []
        for x in self.state["alerts"]:
            q = self.quotes.get(x["sym"])
            hit = x["mkt"] == self.market and q and q[0] and (q[0] >= x["level"] if x["side"] == "above" else q[0] <= x["level"])
            if hit:
                cur = "$" if x["mkt"] == "US" else "₹"
                out.append(f"🔔 <b>{esc(x['sym'])}</b> is {x['side']} {cur}{x['level']:,.2f}: now {cur}{q[0]:,.2f} ({when}).")
                self.dirty = True
            else:
                keep.append(x)
        self.state["alerts"] = keep
        if self.dirty:
            save_state(self.state)
            self.dirty = False
        return out


# -- state on the 'bot' branch ---------------------------------------------
def load_state() -> dict:
    try:
        subprocess.run(["git", "-C", str(ROOT), "fetch", "-q", "origin", "bot"], check=True, capture_output=True, timeout=60)
        return json.loads(subprocess.run(["git", "-C", str(ROOT), "show", "FETCH_HEAD:bot.json"],
                                         check=True, capture_output=True, text=True).stdout)
    except Exception:
        return {}


def save_state(st: dict) -> None:
    try:
        run = lambda *a: subprocess.run(["git", "-C", str(OUT), *a], check=True, capture_output=True, timeout=60)
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
            run("checkout", "-q", "--orphan", "bot")
        (OUT / "bot.json").write_text(json.dumps(st), encoding="utf-8")
        run("add", "bot.json")
        run("commit", "-q", "--allow-empty", "-m", "Bot state")
        run("push", "-q", "-f", "origin", "HEAD:refs/heads/bot")
    except Exception as e:
        print(f"bot: state not saved: {str(e)[:100]}")


def set_menu() -> None:
    """Register the command menu and description shown in Telegram."""
    T.call("setMyCommands", commands=[{"command": c, "description": d} for c, d in MENU])
    T.call("setMyDescription", description=(
        "Your NSE terminal in chat. Try:\nprice TCS\nTCS  (trade verdict)\nvalue TCS  (investing verdict)\ntop\nhedge TCS\n"
        "alert TCS above 3450\nalert NVDA below 150\nwatch RELIANCE\nmy alerts\nstatus"))
    T.call("setMyShortDescription", short_description="Prices, verdicts, top setups, hedges and alerts from your NSE terminal.")


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["menu"]:
        set_menu()
        print("menu set")
    elif sys.argv[1:2] == ["say"]:
        print(re.sub(r"<[^>]+>", "", Bot("NSE", state={}).handle(" ".join(sys.argv[2:]))))
