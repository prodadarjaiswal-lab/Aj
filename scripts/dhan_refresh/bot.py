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

MENU = [("flow", "Order flow and auction levels: flow TCS"), ("options", "Option OI, expected move and gamma: options NIFTY"),
        ("rising", "Turning bullish: tested breakout signals, with value"), ("dips", "Proven stocks after a sharp fall (tested)"),
        ("bargains", "Blue chips now cheap, India and US"), ("record", "Live track record of the bot's picks"), ("alert", "Your alerts (alert TCS above 3450 to add)")]
DESCRIPTION = ("Your NSE terminal in chat. Commands:\n"
               "price TCS\n"
               "TCS  (trade verdict)\n"
               "value TCS  (investing verdict)\n"
               "hedge TCS\n"
               "flow TCS  (VWAP, volume and market profile, delta estimate)\n"
               "options NIFTY  (expected move, OI walls, gamma)\n"
               "rising  (turning bullish, with value)\n"
               "dips  (proven stocks after a sharp fall)\n"
               "bargains  (blue chips now cheap, India and US)\n"
               "record  (how the bot's picks have done)\n"
               "journal  (your last questions)\n"
               "alert TCS above 3450  (alert alone lists; alert remove 1)")
SIGNAL = {"hi52v": "a new 52-week closing high on 1.5x average volume",
          "volbreak": "a breakout above its 20-day high on 1.5x average volume",
          "nr7": "its tightest day in 7, inside the prior day, in an uptrend",
          "trend": "a trend-template pattern (above rising 50, 150 and 200-day averages, near its high)",
          "vcp": "a volatility contraction near its high",
          "adx": "the start of a strong trend (ADX above 25, buyers in control)",
          "rsi2": "a short, sharp dip (RSI(2) under 10) while above its 200-day average",
          "st_up": "a Supertrend turn up",
          "accum": "steady accumulation (up-day volume 1.5x down-day volume)",
          "gap": "a gap up of 3% that held on 2x volume",
          "pullback": "a pullback within an uptrend",
          "don55": "a close above its 55-day high",
          "macd0": "a MACD cross up while above zero",
          "bbsq": "a breakout from a Bollinger squeeze",
          "rsnew": "a 1-year high in relative strength before price",
          "dip3": "three down days in a row while above its 200-day average",
          "ibs": "a close near the day's low while above its 200-day average",
          "reclaim200": "a close back above its 200-day average"}
WARN_SIGNALS = ("extended", "downtrend")
DIP_SIGNALS = ("qdrop25", "qdrop", "qdrop10", "qdd", "qdd_hold")
SIGNAL.update({"qdrop10": "a 10%+ fall within 10 days after beating the Nifty for 2 years",
               "qdrop25": "a 25%+ fall within 20 days after beating the Nifty for 2 years","qdrop": "a 15%+ fall within 10 days after beating the Nifty for 2 years",
               "qdd": "a fall to 25% below its 52-week high after beating the Nifty for 2 years",
               "qdd_hold": "its first close back above the 20-day average after such a fall"})
SECTOR_INDEX = {"Information Technology": "Nifty IT", "Financial Services": "Nifty Bank", "Automobile and Auto Components": "Nifty Auto",
                "Fast Moving Consumer Goods": "Nifty FMCG", "Healthcare": "Nifty Pharma", "Metals & Mining": "Nifty Metal",
                "Oil Gas & Consumable Fuels": "Nifty Energy", "Power": "Nifty Energy", "Realty": "Nifty Realty",
                "Media Entertainment & Publication": "Nifty Media"}


def _load(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


class Data:
    """Read-only view of what the nightly and weekly jobs produced."""

    def __init__(self, board=None, nset=None, opts=None, tech=None, model=None):
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
        self.tech = (tech if tech is not None else _load(ROOT / "docs/tech-today.json", {})).get("stocks", {})
        self.model = model if model is not None else _load(ROOT / "docs/tech-model.json", {})
        up = self.nifty_up_raw(nset)
        flag = "tested_weak" if up is False else "tested"
        sigs = self.model.get("signals", {})
        # only signals that passed the back-test in the market condition we are in now, strongest first
        self.dips = [k for k in DIP_SIGNALS if sigs.get(k, {}).get(flag)]
        self.tested = sorted([k for k, v in sigs.items() if v.get(flag) and k not in WARN_SIGNALS and k not in DIP_SIGNALS],
                             key=lambda k: -((v := sigs[k]).get("lift_out_x10" if flag == "tested" else "lift_out_x10_weak") or 0))
        self.regime_flag = flag
        self.asof = board.get("asof", "?")
        self.rows = board.get("rows", [])
        self.bysym = {r["s"]: r for r in self.rows}
        self.stocks = nset.get("stocks", {})
        self.idx = nset.get("idx", {})
        self.opts = opts.get("rows", {})
        self.auction = _load(ROOT / "docs/auction.json", {}).get("symbols", {})

    def last(self, r: dict) -> float:
        """Newest close we hold: the board's or the technical file's, whichever is later."""
        t = self.tech.get(r["s"], {})
        return t["c"] if t.get("c") and t.get("d", "") >= self.asof else r["last"]

    def find(self, word: str):
        w = word.upper().strip()
        if w in self.bysym:
            return self.bysym[w]
        hits = [r for r in self.rows if w in r["name"].upper().split() or r["name"].upper().startswith(w)]
        return hits[0] if len(hits) == 1 else None

    @staticmethod
    def nifty_up_raw(nset):
        c = (nset or {}).get("idx", {}).get("Nifty 50", {}).get("c", [])
        if len(c) < 200:
            return None
        return c[-1] > sum(c[-200:]) / 200

    def nifty_up(self):
        """True when the Nifty 50 is above its 200-day average (the regime the signals were tested in)."""
        return self.nifty_up_raw({"idx": self.idx})

    def stat(self, sig):
        side = "weak" if self.regime_flag == "tested_weak" else "up"
        return self.model.get("signals", {}).get(sig, {}).get("out", {}).get(side, {})

    def base(self):
        side = "weak" if self.regime_flag == "tested_weak" else "up"
        return self.model.get("base", {}).get("out", {}).get(side, {})

    def ret21(self, name):
        c = self.idx.get(name, {}).get("c", [])
        return c[-1] / c[-22] - 1 if len(c) > 22 else None

    def industry_r21(self, r):
        peers = sorted(x["r21"] for x in self.rows if x.get("ind") == r.get("ind") and x["s"] != r["s"] and x.get("r21") is not None)
        return peers[len(peers) // 2] if len(peers) >= 3 else None



def rupee(x) -> str:
    return f"₹{x:,.1f}" if x < 1000 else f"₹{x:,.0f}"


def pct(x, d=1) -> str:
    return f"{x * 100:+.{d}f}%"


def value_tag(d: Data, sym: str) -> str:
    v = (d.stocks.get(sym) or {}).get("val") or {}
    g = v.get("gap")
    if g is None:
        return ""
    return "value support" if g <= -0.03 else "fairly priced" if g < 0.05 else "expensive"


def rising(d: Data) -> str:
    """Stocks turning bullish on a tested signal; those with value support first."""
    cands = []
    for sym, t in d.tech.items():
        new = [k for k in d.tested if k in t.get("new", [])]
        r = d.bysym.get(sym)
        if new and r and r.get("status") in ("lead", "improve"):
            tag = value_tag(d, sym)
            cands.append(({"value support": 0, "fairly priced": 1, "": 2, "expensive": 3}[tag], d.tested.index(new[0]),
                          -(r.get("score") or 0), sym, new[0], t, tag))
    cands.sort()
    head = f"<b>Turning bullish</b> · {esc(d.asof)} close"
    if not cands:
        return head + ("\nNone today among leading stocks." if d.tested else "\nNo signal has passed the back-test for the current market.")
    lines = [head]
    for i, (_, _, _, sym, sig, t, tag) in enumerate(cands[:5], 1):
        a = t.get("atr") or 0
        val = f" [{tag}]" if tag else ""
        lines.append(f"{i}. <b>{esc(sym)}</b> {rupee(t['c'])}{val}: {SIGNAL.get(sig, sig)}. Stop {rupee(t['c'] - 2 * a)}, target {rupee(t['c'] + 3 * a)}.")
    if d.nifty_up() is False:
        lines.append("Weak market: only signals that passed the back-test in weak markets are used.")
    return "\n".join(lines)


top = rising


def dips(d: Data) -> str:
    """Proven stocks after a sharp fall, only for dip signals that passed the back-test."""
    head = f"<b>Proven stocks after a sharp fall</b> · {esc(d.asof)} close"
    if not d.dips:
        return head + "\nNo dip signal has passed the back-test for the current market, so none is shown."
    cands = []
    for sym, t in d.tech.items():
        hit = [k for k in d.dips if k in t.get("dip10", [])]
        if hit:
            cands.append((d.dips.index(hit[0]), t.get("hi52") or 0, sym, hit[0], t))
    cands.sort()
    if not cands:
        return head + "\nNone in the last 10 trading days."
    lines = [head]
    for i, (_, _, sym, sig, t) in enumerate(cands[:5], 1):
        s = d.stat(sig)
        lines.append(f"{i}. <b>{esc(sym)}</b> {rupee(t['c'])}, {t.get('hi52')}% from its 52-week high: {SIGNAL.get(sig, sig)}.")
        if i == 1 and s.get("n"):
            lines.append(f"   Last 2 years, {s['n']:,} cases: beat the Nifty in {s.get('hit21', 0) * 100:.0f}% within 21 days, average {pct(s.get('x21', 0))}.")
    return "\n".join(lines)


def bargains(d: Data, us: dict | None = None) -> str:
    """Blue chips with a record of growth that now trade cheaply. A screen: fundamentals have no
    history to back-test against, so this is not a tested signal."""
    india = []
    for sym, s in d.stocks.items():
        v, r = s.get("val") or {}, d.bysym.get(sym) or {}
        if v.get("gap") is None or v.get("g3") is None:
            continue
        hi = (r.get("hi52") or 0)
        if v["gap"] <= -0.03 and v["g3"] > 0.05 and v.get("pe") and v.get("pe_med") and v["pe"] < v["pe_med"] and hi <= -0.10:
            india.append((v["gap"], sym, v, r))
    india.sort()
    us = us if us is not None else _load(ROOT / "docs/us-value.json", {})
    usl = []
    def growth(x):
        for yrs in (5, 4):
            g = [x.get(f"eps_cagr{yrs}"), x.get(f"rev_cagr{yrs}")]
            g = [v for v in g if v is not None]
            if g:
                return max(g), yrs
        return None, None
    for x in us.get("rows", []):
        g, yrs = growth(x)
        x["_g"], x["_y"] = g, yrs
        if g is not None and g > 0.05 and (x.get("roe_avg") or 0) > 0.15 and (x.get("off_high") or 0) <= -0.10 and x.get("pe_now") and x.get("pe_hist_median") \
                and 0 < x["pe_now"] < x["pe_hist_median"]:
            usl.append((x["pe_now"] / x["pe_hist_median"], x))
    usl.sort(key=lambda z: z[0])
    lines = ["<b>Blue chips now cheap</b> (a valuation screen, not a back-tested signal)"]
    lines.append("<b>India</b> (Nifty 50)")
    if india:
        for gap, sym, v, r in india[:4]:
            lines.append(f"• <b>{esc(sym)}</b> {rupee(d.last(r))}, {r.get('hi52', 0) * 100:.0f}% from its high: "
                         + (f"price assumes profits shrink {-v['g_impl'] * 100:.0f}% a year" if v['g_impl'] < 0 else f"price needs {v['g_impl'] * 100:.0f}% growth a year")
                         + f", delivered {v['g3'] * 100:.0f}%; P/E {v['pe']:.0f} vs median {v['pe_med']:.0f}.")
    else:
        lines.append("None passes today.")
    lines.append(f"<b>US</b> ({esc(us.get('asof', 'no data'))})")
    if usl:
        for _, x in usl[:4]:
            lines.append(f"• <b>{esc(x['s'])}</b> ${x['price']:,.2f}, {x['off_high'] * 100:.0f}% from its high: P/E {x['pe_now']:.0f} vs its usual {x['pe_hist_median']:.0f}; "
                         f"{x['_y']}-year growth {x['_g'] * 100:.0f}% a year, ROE {x['roe_avg'] * 100:.0f}%.")
    else:
        lines.append("None passes today." if us.get("rows") else "US data not loaded yet.")
    return "\n".join(lines)


def flow(d: Data, sym: str) -> str:
    a = d.auction.get("Nifty 50" if sym in ("NIFTY", "NIFTY50") else "Nifty Bank" if sym == "BANKNIFTY" else sym)
    if not a:
        return f"{esc(sym)}: no 1-minute auction data. Covered: Nifty 50 stocks, the indices and stocks you ask about (from the next nightly refresh)."
    L = [f"<b>{esc(sym)}</b> order flow · session {esc(a['date'])} · context only (no auction signal passed the back-test)"]
    v, w, dl, t = a.get("vp"), a.get("vwap") or {}, a.get("delta") or {}, a.get("tpo") or {}
    if w.get("vwap"):
        L.append(f"VWAP {w['vwap']:,} (±1σ {w['dn1']:,} to {w['up1']:,}); price {w['dev_sd']}σ away, {w['state']} for {w['minutes_on_side']} min.")
    if v and v.get("poc"):
        L.append(f"Volume profile (derived): POC {v['poc']:,}, value {v['val']:,} to {v['vah']:,}.")
    if t.get("tpo_poc") is not None:
        L.append(f"Market profile: POC {t['tpo_poc']:,}, value {t['tpo_val']:,} to {t['tpo_vah']:,}; first hour {t['ib_low']:,} to {t['ib_high']:,}, "
                 f"broke {t['ib_extension']}; {'excess' if t['excess_high'] else 'poor'} high, {'excess' if t['excess_low'] else 'poor'} low.")
    if a.get("auction"):
        L.append(f"Opened {a['auction']['open_vs_prev_value']}: {a['auction']['read']}.")
    if dl.get("cum_delta_est") is not None:
        L.append(f"Delta (estimate from bar closes; Dhan has no bid/ask tape): {dl['cum_delta_est']:,}, buy share {dl['buy_share_est']}"
                 + (f"; {dl['divergence_est']}" if dl.get("divergence_est") else "") + ".")
    if a.get("composite"):
        c = a["composite"]
        L.append(f"{c['days']}-day value {c['val']:,} to {c['vah']:,}, POC {c['poc']:,}.")
    return "\n".join(L)


def options(d: Data, sym: str) -> str:
    o = d.opts.get(sym)
    if not o:
        return f"{esc(sym)}: no option chain in the nightly snapshot (Nifty, Bank Nifty and 50 F&O stocks are covered)."
    L = [f"<b>{esc(sym)}</b> options to {esc(o['expiry'])} ({o.get('days')} days) · spot {o['spot']:,}"]
    if o.get("exp_move"):
        L.append(f"Expected move ±{o['exp_move'] * 100:.1f}% (at-the-money straddle {o['straddle']:,.1f}).")
    L.append(f"Put/call open interest {o.get('pcr_oi', 0):.2f}, volume {o.get('pcr_vol', 0):.2f}. Heaviest calls {o.get('call_wall', 0):,.0f}, "
             f"puts {o.get('put_wall', 0):,.0f}; max pain {o.get('max_pain', 0):,.0f}.")
    if o.get("iv_call") and o.get("iv_put"):
        L.append(f"Implied volatility: calls {o['iv_call']:.1f}%, puts {o['iv_put']:.1f}%.")
    if o.get("net_gex") is not None:
        L.append(f"Gamma (derived; assumes dealers long calls, short puts): {o['gex_regime']}. Flip at {o['gamma_flip']:,}; "
                 f"call gamma at {', '.join(str(x) for x in o.get('call_gamma_strikes', []))}; put gamma at {', '.join(str(x) for x in o.get('put_gamma_strikes', []))}.")
    L.append("Context only: these option readings have not been back-tested yet (history builds nightly).")
    return "\n".join(L)


def record() -> str:
    """The bot's own live track record (picks logged before the outcome existed)."""
    log = _load(ROOT / "docs/track-record.json", {})
    s = log.get("summary") or {}
    if not s:
        return "Track record: no picks logged yet. It starts with the next nightly refresh."
    L = [f"<b>Live track record</b> · since {esc((log.get('picks') or [{}])[0].get('d', '?'))}"]
    for kind, name in (("rising", "Turning bullish"), ("dips", "Dips")):
        r = s.get(kind) or {}
        if not r.get("picks"):
            continue
        line = f"{name}: {r['picks']} picks, {r['open']} still open."
        if r.get("n10"):
            line += f" After 10 days ({r['n10']}): beat the Nifty {r['beat10'] * 100:.0f}%, average {pct(r['avg10'])}."
        if r.get("n21"):
            line += f" After 21 days ({r['n21']}): {r['beat21'] * 100:.0f}%, {pct(r['avg21'])}."
        if r.get("target_first") is not None:
            line += f" Target before stop: {r['target_first'] * 100:.0f}%."
        L.append(line)
    return "\n".join(L)


def options_line(d: Data, sym: str) -> str:
    o = d.opts.get(sym)
    if not o:
        return ""
    return (f"Options to {esc(o.get('expiry', ''))}: expected move ±{o['exp_move'] * 100:.1f}%, "
            f"put/call open interest {o['pcr_oi']:.2f}, heaviest calls {o['call_wall']:,.0f}, puts {o['put_wall']:,.0f}.")


def technical(d: Data, r: dict, ltp: float | None = None) -> str:
    sym = r["s"]
    t = d.tech.get(sym, {})
    last = ltp or d.last(r)
    atr = t.get("atr")
    new = [k for k in d.tested if k in t.get("new", [])]
    trade_levels = False
    st_, regime = r.get("status"), d.nifty_up()
    lines = [f"<b>{esc(sym)}</b> {rupee(last)} · trade"]
    mkt = "weak market (Nifty below its 200-day average)" if regime is False else "rising market"
    if new and st_ not in ("weak", "fade"):
        sig = new[0]
        s, b = d.stat(sig), d.base()
        lines.append(f"<b>Buy candidate.</b> It just made {SIGNAL.get(sig, sig)}, a signal that passed the back-test in a {mkt}.")
        trade_levels = True
        if s.get("n"):
            lines.append(f"Last 2 years, {s['n']:,} cases: beat the Nifty in {s['hit10'] * 100:.0f}% within 10 days, "
                         f"average {pct(s['x10'])} vs the Nifty (a typical stock: {pct(b.get('x10', 0))}).")
    elif new:
        lines.append(f"<b>Wait.</b> It made {SIGNAL.get(new[0], new[0])}, but the stock itself is lagging the Nifty 500.")
    elif st_ in ("weak", "fade"):
        lines.append(f"<b>Avoid.</b> It is {STATUS[st_]} against the Nifty 500 and has no tested entry signal.")
    elif st_ in ("lead", "improve"):
        lines.append(f"<b>Wait.</b> A {'leading' if st_ == 'lead' else 'improving'} stock, but no tested entry signal today.")
    else:
        lines.append("<b>No trade.</b> Neither leading nor lagging, and no tested entry signal.")
    if atr and trade_levels:
        lines.append(f"Stop {rupee(last - 2 * atr)} ({pct(-2 * atr / last)}), target {rupee(last + 3 * atr)} ({pct(3 * atr / last)}), "
                     f"from 2 and 3 times its daily range.")
    facts = [f"rank {r.get('rank')} of {len(d.rows)}"]
    if r.get("vs50") is not None:
        facts.append(f"{pct(r['vs50'], 0)} vs 50-day avg, {pct(r['vs200'], 0)} vs 200-day")
    if r.get("rs3") is not None:
        facts.append(f"3 months vs Nifty 500 {pct(r['rs3'], 0)}")
    if r.get("rsi") is not None:
        facts.append(f"RSI {r['rsi']:.0f}")
    lines.append("; ".join(facts) + ".")
    ol = options_line(d, sym)
    if ol:
        lines.append(ol)
    return "\n".join(lines)


def value(d: Data, sym: str, ltp: float | None = None) -> str:
    s = d.stocks.get(sym)
    if not s or not s.get("val"):
        return f"{esc(sym)}: the investing view covers the Nifty 50 stocks only."
    v = s["val"]
    last = ltp or (d.last(d.bysym[sym]) if sym in d.bysym else (s.get("ohlc", {}).get("c") or [0])[-1])
    lines = [f"<b>{esc(sym)}</b> {rupee(last)} · invest" if last else f"<b>{esc(sym)}</b> · invest"]
    gap = v.get("gap")
    if gap is None:
        lines.append("<b>No verdict.</b> Not enough history to compare price with growth.")
    elif gap <= -0.03:
        lines.append("<b>Reasonable to accumulate.</b> The price needs less growth than the company has delivered.")
    elif gap < 0.05:
        lines.append("<b>Fairly priced.</b> The price needs about the growth the company has delivered.")
    else:
        lines.append("<b>Expensive.</b> The price needs faster growth than the company has delivered.")
    if v.get("g_impl") is not None and v.get("g3") is not None:
        need = (f"The price assumes profits shrink {-v['g_impl'] * 100:.0f}% a year for 10 years." if v["g_impl"] < 0
                else f"Growth the price needs: {v['g_impl'] * 100:.0f}% a year for 10 years.")
        lines.append(f"{need} Delivered over 3 years: {v['g3'] * 100:.0f}% a year.")
    if v.get("pe") and v.get("pe_med"):
        lines.append(f"P/E {v['pe']:.0f} against its own median of {v['pe_med']:.0f}.")
    if v.get("fair_at_g3") and last:
        lines.append(f"Value if growth stays at the delivered rate: {rupee(v['fair_at_g3'])} ({pct(v['fair_at_g3'] / last - 1, 0)}).")
    return "\n".join(lines)


ADVERSE = ("resign", "probe", "penalt", "fraud", "raid", "default", "downgrad", "loss", "slump", "plunge", "cut ",
           "sebi order", "show cause", "investigat", "lawsuit", "pledge", "fire", "strike", "recall", "ban", "warning", "weak")


def company_news(d: Data, sym: str, days: int = 7) -> tuple:
    """Recent news and NSE filings for a Nifty 50 stock; (headlines, adverse) by a plain keyword screen."""
    s = d.stocks.get(sym)
    if s is None:
        return None, False
    items = sorted((s.get("news") or []) + (s.get("filings") or []), key=lambda x: x.get("time", ""), reverse=True)
    if not items:
        return [], False
    newest = items[0].get("time", "")[:10]
    import datetime as _dt
    try:
        cut = (_dt.date.fromisoformat(newest) - _dt.timedelta(days=days)).isoformat()
    except ValueError:
        cut = ""
    recent = [x for x in items if x.get("time", "")[:10] >= cut][:6]
    bad = [x for x in recent if any(k in x.get("title", "").lower() for k in ADVERSE)]
    return (bad or recent)[:2], bool(bad)


def hedge(d: Data, r: dict, ltp: float | None = None) -> str:
    sym = r["s"]
    t = d.tech.get(sym, {})
    last = ltp or d.last(r)
    beta = (d.stocks.get(sym, {}).get("val") or {}).get("beta")
    o, nf = d.opts.get(sym), d.opts.get("NIFTY")
    lines = [f"<b>Hedging {esc(sym)}</b> {rupee(last)}"]
    lines.append("<b>1. Across asset classes</b>")
    lines.append("Hold part of the portfolio outside Indian equities: gold (ETF) and a liquid or government bond fund. "
                 "When foreign investors sell Indian stocks the rupee usually weakens, so US holdings gain in rupees. "
                 "Gold is insurance, not a return source: in 2008 the Nifty fell 52% while gold rose 28% in rupees, but the link is weak in some falls.")
    sr, ir, mr = r.get("r21"), d.industry_r21(r), d.ret21("Nifty 50")
    lines.append("<b>2. Market, sector or company risk</b>")
    if sr is not None and ir is not None and mr is not None:
        lines.append(f"Last month: {esc(sym)} {pct(sr)}, its industry {pct(ir)}, Nifty {pct(mr)}.")
        company = sr - ir <= -0.05
        sector = ir <= -0.03 or mr <= -0.03
    else:
        company, sector = False, False
    news, adverse = company_news(d, sym)
    if news is None:
        lines.append("News check covers Nifty 50 stocks only.")
    elif adverse:
        company = True
        lines.append("Possibly adverse company news (keyword screen): " + "; ".join(
            f"{esc(x['title'][:110])} ({esc(x.get('time', '')[:10])})" for x in news))
    elif news:
        lines.append(f"No adverse company news in the last week (latest: {esc(news[0]['title'][:90])}).")
    if company:
        lines.append("The risk is company-specific, so a Nifty hedge would not help.")
    elif sector:
        lines.append("The fall is sector or market wide, so a stop or put on the stock alone protects only part.")
    else:
        lines.append("No broad fall right now; choose the hedge by the risk you fear.")
    if o:
        lines.append(f"• Company risk: an at-the-money put to {esc(o['expiry'])} costs about {o['straddle'] / 2 / o['spot'] * 100:.1f}% "
                     f"(implied volatility {o['iv_put']:.0f}%). A collar (sell a higher call) cuts that cost but caps the upside.")
    else:
        lines.append("• Company risk: no stock options in the snapshot, so the choices are a smaller position or an exit.")
    b = beta or 1.0
    idx = "Nifty Bank" if SECTOR_INDEX.get(r.get("ind")) == "Nifty Bank" else "Nifty"
    nl = f"• Market or sector risk: short {idx} worth {b:.2f}x the position (beta{'' if beta else ' assumed 1'})"
    if nf and idx == "Nifty":
        nl += f"; a Nifty at-the-money put to {esc(nf['expiry'])} costs about {nf['straddle'] / 2 / nf['spot'] * 100:.1f}%"
    lines.append(nl + ". One index contract is ₹15-20 lakh, so this suits larger portfolios.")
    lines.append("<b>3. Stop-loss</b>")
    atr = t.get("atr")
    if atr:
        stop = last - 2 * atr
        lines.append(f"Stop at {rupee(stop)} ({pct(stop / last - 1)}), 2 times its daily range. "
                     f"Risking 1% of ₹10 lakh allows {int(10000 / (last - stop)):,} shares.")
    if r.get("fail") and r["fail"] < last:
        lines.append(f"Chart level: the setup fails below {rupee(r['fail'])}.")
    soon = d.stocks.get(sym, {}).get("res_soon")
    lines.append(("Results are due soon: a" if soon else "A") + " stop does not protect against an overnight gap; a put does.")
    return "\n".join(lines)


class Bot:
    """Polls Telegram, answers commands, and checks user alerts against live prices."""

    def __init__(self, market: str, data: Data | None = None, state: dict | None = None):
        self.market = market                      # "NSE", "US" (alert checking) or "ANY" (the listener)
        self.reload = state is None
        self.d = data or Data()
        self.state = state if state is not None else load_state()
        self.state.setdefault("offset", 0)
        self.state.setdefault("alerts", [])
        self.state.setdefault("watch", [])
        self.dirty = False
        self.quotes = {}                          # NSE: {sym: (ltp, prev)}; US: {sym: (ltp, prev)}
        self.us_symbols = set()
        self.us_quotes = {}                       # {sym: {price, prev, t, live}} from the US tracker
        self.status_line = ""
        self.feed_note = ""
        self.state.setdefault("journal", [])

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
            return f"<b>{esc(sym)}</b> ₹{ltp:,.2f}{chg}, live from Dhan"
        if sym in self.us_quotes and self.us_quotes[sym].get("price"):
            q = self.us_quotes[sym]
            chg = f" ({(q['price'] / q['prev'] - 1) * 100:+.2f}%)" if q.get("prev") else ""
            when = "live from Dhan" if q.get("live") else f"last Dhan price, {esc(q.get('t', ''))}"
            return f"<b>{esc(sym)}</b> ${q['price']:,.2f}{chg}, {when}"
        r = self.d.find(word)
        if r:
            t = self.d.tech.get(r["s"], {})
            day = t["d"] if t.get("c") and t.get("d", "") >= self.d.asof else self.d.asof
            why = self.feed_note or "Market closed"
            return f"<b>{esc(r['s'])}</b> {rupee(self.d.last(r))}, Dhan close of {esc(day)}. {why}."
        return f"{esc(sym)}: not a Nifty 500 stock, and not tracked in the US session."

    def log(self, cmd: str, sym: str, reply: str) -> None:
        """Journal of every stock asked about (kept on the 'bot' branch, last 500)."""
        first = re.sub(r"<[^>]+>", "", reply.split("\n")[1] if "\n" in reply else reply)[:160]
        j = self.state.setdefault("journal", [])
        j.append({"t": __import__("datetime").datetime.now(__import__("zoneinfo").ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M"),
                  "cmd": cmd, "sym": sym, "price": self.ltp(sym), "said": first})
        del j[:-500]
        self.dirty = True

    def handle(self, text: str) -> str:
        low = re.sub(r"\s+", " ", text.strip()).lower().lstrip("/")
        w = low.split(" ")
        if low in ("rising", "top", "top 5", "top5", "picks", "bullish"):
            return rising(self.d)
        if low in ("journal", "my journal", "history"):
            j = self.state.get("journal", [])[-15:]
            if not j:
                return "Journal is empty."
            return "<b>Your last questions</b>\n" + "\n".join(
                f"{esc(x['t'])} · {esc(x['sym'])} ({esc(x['cmd'])}): {esc(x['said'][:90])}" for x in reversed(j))
        if low in ("record", "track", "scorecard", "track record"):
            return record()
        if low in ("dips", "dip", "discount", "discounts"):
            return dips(self.d)
        if low in ("bargains", "bargain", "value", "cheap"):
            return bargains(self.d)
        if w[0] == "price" and len(w) == 2:
            out = self.price(w[1])
            self.log("price", w[1].upper(), out)
            return out
        if w[0] in ("flow", "orderflow", "auction") and len(w) == 2:
            out = flow(self.d, w[1].upper())
            self.log("flow", w[1].upper(), out)
            return out
        if w[0] in ("options", "option", "oi", "gamma") and len(w) == 2:
            return options(self.d, w[1].upper())
        if w[0] in ("value", "hedge") and len(w) == 2:
            r = self.d.find(w[1])
            sym = r["s"] if r else w[1].upper()
            if w[0] == "value":
                out = value(self.d, sym, self.ltp(sym))
            else:
                out = hedge(self.d, r, self.ltp(sym)) if r else f"{esc(sym)}: not a Nifty 500 stock."
            self.log(w[0], sym, out)
            return out
        if w[0] == "alert":
            if len(w) == 1:
                return self.list_alerts()
            if len(w) == 3 and w[1] == "remove" and w[2].isdigit():
                return self.remove(int(w[2]))
            m = re.match(r"alert (\S+) (above|below|over|under|>|<) ?\$?₹?([\d.,]+)( us)?$", low)
            if m:
                return self.add_alert(m.group(1).upper(), "above" if m.group(2) in ("above", "over", ">") else "below",
                                      float(m.group(3).replace(",", "")), bool(m.group(4)))
            return "Alert format: alert TCS above 3450"
        if len(w) == 1 and re.fullmatch(r"[a-z0-9&\-]{2,15}", w[0]):
            r = self.d.find(w[0])
            if r:
                out = technical(self.d, r, self.ltp(r["s"]))
                self.log("trade", r["s"], out)
                return out
            if w[0].upper() in self.quotes or w[0].upper() in self.us_quotes:
                return self.price(w[0])
            return f"{esc(w[0].upper())}: not a Nifty 500 stock."
        return "Not a command. The six commands are in my description."

    def ltp(self, sym: str):
        q = self.quotes.get(sym)
        return q[0] if q and q[0] else None

    def market_of(self, sym: str, us_flag: bool) -> str | None:
        if us_flag or self.is_us(sym):
            return "US"
        return "NSE" if sym in self.d.bysym else None

    def add_alert(self, sym: str, side: str, level: float, us_flag: bool) -> str:
        mkt = self.market_of(sym, us_flag)
        if not mkt:
            return f"{esc(sym)}: not a Nifty 500 stock. For a US stock end with 'us'."
        if len(self.state["alerts"]) >= 40:
            return "40 alerts already. Remove one first."
        self.state["alerts"].append({"sym": sym, "mkt": mkt, "side": side, "level": level})
        self.dirty = True
        cur = "$" if mkt == "US" else "₹"
        return f"Alert set: {esc(sym)} {side} {cur}{level:,.2f}."

    def list_alerts(self) -> str:
        a = self.state["alerts"]
        if not a:
            return "No alerts."
        return "<b>Your alerts</b>\n" + "\n".join(
            f"{i}. {esc(x['sym'])} {x['side']} {'$' if x['mkt'] == 'US' else '₹'}{x['level']:,.2f}" for i, x in enumerate(a, 1))

    def remove(self, i: int) -> str:
        a = self.state["alerts"]
        if not 1 <= i <= len(a):
            return "No alert with that number."
        x = a.pop(i - 1)
        self.dirty = True
        return f"Removed: {esc(x['sym'])} {x['side']} {x['level']:,.2f}."

    # -- user alerts ------------------------------------------------------
    def check(self, when: str) -> list:
        """Fire user alerts for this market against self.quotes. Each fires once, then is deleted.
        The listener edits alerts too, so the stored state is re-read before anything is removed."""
        out, keep = [], []
        quotes = self.quotes if self.market == "NSE" else {k: (v.get("price"), v.get("prev")) for k, v in self.us_quotes.items()}
        fired = []
        for x in self.state["alerts"]:
            q = quotes.get(x["sym"])
            if x["mkt"] == self.market and q and q[0] and (q[0] >= x["level"] if x["side"] == "above" else q[0] <= x["level"]):
                fired.append(x)
        if not fired:
            return []
        fresh = load_state() if self.reload else self.state
        if fresh:
            self.state = fresh
        for x in self.state["alerts"]:
            q = quotes.get(x["sym"])
            hit = x in fired or (x["mkt"] == self.market and q and q[0] and (q[0] >= x["level"] if x["side"] == "above" else q[0] <= x["level"]))
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
def _secret():
    import os
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")


def load_state() -> dict:
    """Bot state (alerts, journal, read position) from the 'bot' branch, encrypted with the bot token."""
    import token_cache as TC
    try:
        subprocess.run(["git", "-C", str(ROOT), "fetch", "-q", "origin", "bot"], check=True, capture_output=True, timeout=60)
        raw = json.loads(subprocess.run(["git", "-C", str(ROOT), "show", "FETCH_HEAD:bot.json"],
                                        check=True, capture_output=True, text=True).stdout)
        if "ct" in raw:
            txt = TC.unseal(raw, "bot-state", _secret())
            return json.loads(txt) if txt else {}
        return raw                                   # older plain-text state: read once, re-saved encrypted
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
        import token_cache as TC
        if not _secret():
            print("bot: no TELEGRAM_BOT_TOKEN, state not saved")
            return
        (OUT / "bot.json").write_text(json.dumps(TC.seal(json.dumps(st), "bot-state", _secret())), encoding="utf-8")
        run("add", "bot.json")
        run("commit", "-q", "--allow-empty", "-m", "Bot state")
        run("push", "-q", "-f", "origin", "HEAD:refs/heads/bot")
    except Exception as e:
        print(f"bot: state not saved: {str(e)[:100]}")


def set_menu() -> None:
    """Register the command menu and description shown in Telegram."""
    T.call("setMyCommands", commands=[{"command": c, "description": d} for c, d in MENU])
    T.call("setMyDescription", description=DESCRIPTION)
    T.call("setMyShortDescription", short_description="price TCS · TCS · value TCS · hedge TCS · top · alert TCS above 3450")


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["menu"]:
        set_menu()
        print("menu set")
    elif sys.argv[1:2] == ["say"]:
        print(re.sub(r"<[^>]+>", "", Bot("NSE", state={}).handle(" ".join(sys.argv[2:]))))
