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

DESK_URL = "https://claude.ai/artifact/QHCtbgKuHA17eSSS4zbd9h"
TERMINAL_URL = "https://claude.ai/artifact/JBe9w1vLcwPQFyfmYHoRDz"
LINKS = (f'📌 <b>Your trading desks</b>\n<a href="{DESK_URL}">Technical Desk</a>: screener, then Analyze for any stock '
         f'(technical, value, combined verdict and fit with your portfolio).\n<a href="{TERMINAL_URL}">NSE Terminal</a>: '
         "markets, sectors and valuations.\nOpen while signed in to claude.ai. Prices from Dhan.")

MENU = [("desk", "Open the Technical Desk and NSE Terminal"), ("flow", "Order flow and auction levels: flow TCS"), ("options", "Option OI, expected move and gamma: options NIFTY"),
        ("rising", "Turning bullish: tested breakout signals, with value"), ("dips", "Proven stocks after a sharp fall (tested)"),
        ("bargains", "Blue chips now cheap, India and US"), ("portfolio", "Markowitz portfolios (Nifty 50)"), ("pairs", "Pairs trading scan"), ("markets", "Commodities, USD/INR and the day's movers with news"), ("record", "Live track record of the bot's picks"), ("alert", "Your alerts (alert TCS above 3450 to add)")]
DESCRIPTION = ("Your NSE terminal. Prices from Dhan.\n"
               "price TCS\n"
               "TCS (trade verdict)\n"
               "value TCS (invest verdict)\n"
               "hedge TCS\n"
               "flow TCS (order flow)\n"
               "options NIFTY\n"
               "why TCS (news behind a move)\n"
               "rising (turning bullish)\n"
               "dips (proven stocks after a fall)\n"
               "bargains (cheap blue chips, India+US)\n"
               "markets (MCX, USD/INR, movers)\n"
               "mc TCS (Monte Carlo) · var TCS\n"
               "portfolio · pairs\n"
               "bs NIFTY 25500 CE (Black-Scholes)\n"
               "record (how picks did)\n"
               "journal\n"
               "alert TCS above 3450\n"
               "desk (links to the desk and terminal)")
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
        self.pf = _load(ROOT / "docs/portfolio.json", {})
        self.vm = _load(ROOT / "docs/value-model.json", {})
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


def live_flow_lines(f: dict, t: str) -> list:
    L = [f"<b>Live order flow</b> ({esc(t)} IST; snapshot-derived from Dhan quotes every 5 s, not a full trade tape)"]
    L.append(f"Delta {f['delta']:,} (buy {f['buy_vol']:,} / sell {f['sell_vol']:,}, buyers {f['buy_share'] * 100:.0f}%), {f['prints']} prints.")
    if f.get("book_ratio5") or f.get("pending_ratio"):
        L.append(f"Book: top-5 bids/asks {f.get('book_ratio5', '–')}x, pending buy/sell {f.get('pending_ratio', '–')}x.")
    if f.get("stacked"):
        L.append("Stacked imbalances: " + "; ".join(f"{s_[2]} {s_[0]:,} to {s_[1]:,}" for s_ in f["stacked"]))
    big = f.get("large_prints") or []
    if big:
        L.append("Large prints: " + ", ".join(f"{x[0][:5]} {x[2]:,.0f} at {x[1]:,} ({'buy' if x[3] > 0 else 'sell'})" for x in big[-4:]))
    ev = [e for e in (f.get("events") or []) if "absorption" in e[1]]
    if ev:
        L.append("Absorption: " + ", ".join(f"{e[0][:5]} {e[1].split(': ')[1]} at {e[2]:,}" for e in ev[-3:]))
    for k in ("divergence", "exhaustion", "trapped"):
        if f.get(k):
            L.append(f"{k.capitalize()}: {esc(f[k])}.")
    return L


def flow(d: Data, sym: str, live: dict | None = None) -> str:
    lf = (live or {}).get("s", {}).get(sym)
    if lf:
        return "\n".join([f"<b>{esc(sym)}</b> order flow · context only (not back-tested yet)"] + live_flow_lines(lf, live.get("t", "")))
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


def markets_reply() -> str:
    m = _load(ROOT / "docs/markets.json", {})
    if not m:
        return "Markets snapshot not available yet (it is saved by the nightly Dhan refresh)."
    L = [f"<b>Markets</b> · Dhan, {esc(m.get('asof', ''))}"]
    for k, f in (m.get("futures") or {}).items():
        ch = f" ({f['chg'] * 100:+.2f}%)" if f.get("chg") is not None else ""
        L.append(f"{esc(f['name'])}: {f['ltp']:,.2f}{ch}")
    mv = m.get("movers") or []
    if mv:
        L.append("<b>Biggest moves today, with Dhan headlines</b> (a headline is a possible reason, not proof)")
        for x in mv[:6] + mv[-0:]:
            h = (x.get("headlines") or [{}])[0].get("title")
            L.append(f"• {esc(x['s'])} {x['r1'] * 100:+.1f}%" + (f": {esc(h[:100])}" if h else ": no Dhan headline"))
    if m.get("missing"):
        L.append("Not available from Dhan: " + esc(", ".join(str(x) for x in m["missing"][:5])))
    return "\n".join(L)


def why(d: Data, sym: str) -> str:
    """Why did it move: the day's move with Dhan headlines (movers) or NSE news and filings (Nifty 50)."""
    r = d.find(sym)
    if not r:
        return f"{esc(sym)}: not a Nifty 500 stock."
    s = r["s"]
    L = [f"<b>{esc(s)}</b> {pct(r.get('r1') or 0)} on the day, {pct(r.get('r5') or 0)} over 5 days, {pct(r.get('r21') or 0)} over a month"]
    m = _load(ROOT / "docs/markets.json", {})
    hs = next((x.get("headlines") for x in m.get("movers", []) if x["s"] == s), None) or []
    st_ = d.stocks.get(s) or {}
    items = hs + [{"title": x.get("title"), "time": x.get("time", "")} for x in (st_.get("filings") or [])[:2] + (st_.get("news") or [])[:3]]
    if items:
        L.append("Possible reasons (headlines near the move; not proven causes):")
        L += [f"• {esc(str(x.get('time', ''))[:10])} {esc(str(x.get('title', ''))[:120])}" for x in items[:5] if x.get("title")]
    else:
        L.append("No headline found in Dhan news or NSE filings for this stock.")
    ind = d.industry_r21(r)
    if ind is not None and r.get("r21") is not None:
        L.append(f"Against its industry over a month: {pct(r['r21'] - ind)}.")
    return "\n".join(L)


def _quant():
    return _load(ROOT / "docs/quant.json", {})


def mc_reply(d: Data, sym: str) -> str:
    q = _quant()
    m = (q.get("mc") or {}).get(sym)
    if not m:
        return f"{esc(sym)}: no Monte Carlo yet (Nifty 500 stocks, built nightly from Dhan history)."
    cal = q.get("mc_calibration") or {}
    L = [f"<b>{esc(sym)}</b> Monte Carlo · {m['paths']:,} paths, {m['days']} trading days, from ₹{m['last']:,.2f}",
         f"Middle 50%: ₹{m['p25']:,.0f} to ₹{m['p75']:,.0f}. 90% range: ₹{m['p5']:,.0f} to ₹{m['p95']:,.0f}. Median ₹{m['p50']:,.0f}.",
         f"Chance of ending higher: {m['p_up'] * 100:.0f}%."]
    if m.get("p_target_first") is not None:
        L.append(f"Target (3x daily range) before stop (2x): {m['p_target_first'] * 100:.0f}%; stop first: {m['p_stop_first'] * 100:.0f}%.")
    if cal.get("inside_90") is not None:
        L.append(f"Check: on Nifty 50 history the 90% range held {cal['inside_90'] * 100:.0f}% of the time ({cal['cases']} cases).")
    L.append("Built by resampling the stock's own last 2 years of daily moves; not a forecast of one outcome.")
    return "\n".join(L)


def var_reply(d: Data, sym: str) -> str:
    q = _quant()
    v = (q.get("var") or {}).get(sym) if sym != "PORTFOLIO" else (q.get("portfolio") or {}).get("var")
    if not v:
        return f"{esc(sym)}: VaR covers the Nifty 50 and the minimum-variance portfolio (send: var portfolio)."
    a, b = v["95"], v["99"]
    bt = q.get("var_backtest") or {}
    L = [f"<b>{esc(sym)}</b> Value at Risk on ₹1,00,000",
         f"1 day, 95%: historical ₹{a['hist_1d']:,}, normal ₹{a['param_1d']:,}, simulated ₹{a['mc_1d']:,}. Expected shortfall ₹{a['es_1d']:,}.",
         f"1 day, 99%: historical ₹{b['hist_1d']:,}, normal ₹{b['param_1d']:,}, simulated ₹{b['mc_1d']:,}. Expected shortfall ₹{b['es_1d']:,}.",
         f"10 days, 99%: simulated ₹{b['mc_10d']:,}, normal ₹{b['param_10d']:,}; expected shortfall ₹{b['mc_es_10d']:,}."]
    if bt.get("stocks"):
        L.append(f"Check: 99% historical VaR passed the exceedance test on {bt['passed']} of {bt['stocks']} Nifty 50 stocks over 2 years.")
    return "\n".join(L)


def portfolio_reply() -> str:
    p = (_quant().get("portfolio") or {})
    if not p:
        return "Portfolio optimisation not built yet (nightly, Nifty 50)."
    L = [f"<b>Nifty 50 portfolios</b> (1 year of Dhan data, long-only, max {p['cap'] * 100:.0f}% per stock, risk-free {p['rf'] * 100:.1f}%)"]
    for k, name in (("min_variance", "Minimum variance"), ("max_sharpe", "Maximum Sharpe")):
        x = p[k]
        top = ", ".join(f"{s} {w * 100:.0f}%" for s, w in list(x["weights"].items())[:6])
        L.append(f"<b>{name}</b>: return {x['ret'] * 100:.1f}%, volatility {x['vol'] * 100:.1f}%, Sharpe {x['sharpe']}. {top}")
    wf = p.get("walk_forward") or {}
    if wf:
        L.append("Check (refit every 3 months, measured on the next 3): " + "; ".join(
            f"{n} Sharpe {wf[k]['sharpe']}, max fall {wf[k]['max_dd'] * 100:.0f}%" for k, n in
            (("min_variance", "min variance"), ("max_sharpe", "max Sharpe"), ("equal", "equal weight")) if k in wf))
        eq = (wf.get("equal") or {}).get("sharpe")
        best = max((wf[k]["sharpe"] for k in ("min_variance", "max_sharpe") if k in wf and wf[k].get("sharpe") is not None), default=None)
        if eq is not None and best is not None and best <= eq:
            L.append("<b>Verdict:</b> out of sample, neither optimised portfolio beat equal weight. Treat these weights as risk information, not a recommendation.")
        elif eq is not None and best is not None:
            L.append("<b>Verdict:</b> out of sample, the optimised portfolio beat equal weight on risk-adjusted return.")
    return "\n".join(L)


def pairs_reply() -> str:
    pr = (_quant().get("pairs") or {})
    st_ = pr.get("strategy_oos") or {}
    if not pr:
        return "Pairs scan not built yet (nightly)."
    L = [f"<b>Pairs (mean reversion)</b> · {pr.get('rule', '')}"]
    if st_.get("trades"):
        L.append(f"Walk-forward test: {st_['trades']} trades, average {st_.get('avg', 0) * 100:+.2f}% per trade, hit {st_.get('hit', 0) * 100:.0f}%, "
                 f"t {st_.get('t')}, max fall {st_.get('max_dd', 0) * 100:.0f}%.")
    if not st_.get("tested"):
        L.append("The strategy did not pass the walk-forward test, so no trade is suggested. Cointegrated pairs right now (context):")
    live = pr.get("current") or []
    for p in live[:6]:
        L.append(f"• {esc(p['y'])}/{esc(p['x'])} ({esc(p['industry'])}): z {p['z']:+.2f}, half-life {p['half_life']} days"
                 + (f" → {esc(p['signal'])}" if st_.get("tested") and p["signal"] != "no trade" else ""))
    if not live:
        L.append("No cointegrated pair today.")
    return "\n".join(L)


def bs_reply(d: Data, args: list, live_index: dict) -> str:
    """bs NIFTY 25500 CE [days]  - Black-Scholes with the Dhan option chain's implied volatility."""
    import datetime as _dt
    import quant as Qm
    if len(args) < 3:
        return "Format: bs NIFTY 25500 CE (optional days to expiry)"
    u, kind = args[0].upper(), ("call" if args[2].upper() in ("CE", "CALL", "C") else "put")
    try:
        K = float(args[1].replace(",", ""))
    except ValueError:
        return "Strike must be a number: bs NIFTY 25500 CE"
    o = d.opts.get(u)
    if not o:
        return f"{esc(u)}: no option chain in the nightly Dhan snapshot."
    S = live_index.get(u) or o["spot"]
    days = float(args[3]) if len(args) > 3 else max(o.get("days") or 1, 0.5)
    iv = ((o.get("iv_call") or 0) + (o.get("iv_put") or o.get("iv_call") or 0)) / 200
    rf = _quant().get("rf") or 0.07
    g = Qm.black_scholes(S, K, days / 365, rf, iv, kind)
    return "\n".join([f"<b>{esc(u)} {K:,.0f} {'CE' if kind == 'call' else 'PE'}</b> · Black-Scholes",
                       f"Spot {S:,.2f} ({'live' if live_index.get(u) else 'last close'}, Dhan), {days:g} days, IV {iv * 100:.1f}% (Dhan chain, at-the-money), rate {rf * 100:.1f}%",
                       f"Price ₹{g['price']:,.2f}",
                       f"Delta {g['delta']:+.3f} · Gamma {g['gamma']:.5f} · Theta ₹{g['theta']:,.2f}/day · Vega ₹{g['vega']:,.2f} per 1% vol · Rho ₹{g['rho']:,.2f} per 1% rate",
                       "Uses the at-the-money IV for every strike, so far strikes ignore the skew."])


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
    fl = fit_line(d, sym)
    if fl:
        lines.append(fl)
    return "\n".join(lines)


def fit_line(d: Data, sym: str) -> str:
    """One line: does it suit the owner's portfolio (docs/portfolio.json, rules from the owner's notes)."""
    f = ((getattr(d, "pf", None) or {}).get("fit") or {}).get(sym)
    if not f:
        return ""
    lab = {"suits": "Suits your portfolio", "partly": "Partly suits your portfolio", "no": "Does not suit your portfolio"}[f["v"]]
    why = "; ".join((f.get("why") or [])[:2])
    size = f" Start at {f['w'] * 100:.0f}%." if f.get("w") and f["v"] != "no" else ""
    basis = " (vs the Nifty: no Dhan holdings found)" if ((d.pf.get("summary") or {}).get("proxy")) else ""
    return f"<b>{lab}</b>{basis}: {esc(why)}.{size}"


def tested_value_line(d: Data, sym: str) -> str:
    vm = getattr(d, "vm", None) or {}
    side = "weak" if d.regime_flag == "tested_weak" else "up"
    on = ((vm.get("today") or {}).get(sym) or {}).get("on") or []
    hits = [k for k in on if (vm.get("rules") or {}).get(k, {}).get(f"tested_{side}")]
    if not hits:
        return ""
    h = vm["rules"][hits[0]].get(f"h_{side}") or "12m"
    r = vm["rules"][hits[0]][f"{h}_{side}"]
    return (f"Tested investor rule active: {esc(vm['names'][hits[0]])} (beat the average stock by {r['lift'] * 100:+.1f}% "
            f"over {h[:-1]} months, t {r['t']}).")


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
    for extra in (tested_value_line(d, sym), fit_line(d, sym)):
        if extra:
            lines.append(extra)
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
        self.live_flow = {}
        self.live_index = {}                      # {"NIFTY": spot} from the live feed
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
        if low in ("desk", "terminal", "links", "link", "dashboard"):
            return LINKS
        if low in ("rising", "top", "top 5", "top5", "picks", "bullish"):
            return rising(self.d)
        if w[0] in ("mc", "montecarlo", "simulate") and len(w) == 2:
            out = mc_reply(self.d, w[1].upper())
            self.log("mc", w[1].upper(), out)
            return out
        if w[0] == "var" and len(w) == 2:
            return var_reply(self.d, w[1].upper())
        if low in ("portfolio", "markowitz", "optimise", "optimize"):
            return portfolio_reply()
        if low in ("pairs", "pair", "mean reversion"):
            return pairs_reply()
        if w[0] in ("bs", "blackscholes", "price-option"):
            return bs_reply(self.d, t.split()[1:] if (t := text.strip()) else [], self.live_index)
        if low in ("markets", "market", "commodities", "mcx"):
            return markets_reply()
        if w[0] in ("why", "news") and len(w) == 2:
            out = why(self.d, w[1])
            self.log("why", w[1].upper(), out)
            return out
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
            out = flow(self.d, w[1].upper(), self.live_flow)
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


def pin_links() -> str:
    """Pin the desk links in the owner's chat, once: skipped when the pinned message already carries them."""
    chat = T.call("getChat", chat_id=T.chat_id())
    pinned = (chat.get("pinned_message") or {})
    if DESK_URL in str(pinned.get("text", "")) + str(pinned.get("entities", "")):
        return "links already pinned"
    m = T.call("sendMessage", chat_id=T.chat_id(), text=LINKS, parse_mode="HTML", disable_web_page_preview=True)
    T.call("pinChatMessage", chat_id=T.chat_id(), message_id=m["message_id"], disable_notification=True)
    return "links pinned"


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
        try:
            print(pin_links())
        except Exception as e:
            print(f"pin failed: {str(e)[:200]}")
    elif sys.argv[1:2] == ["say"]:
        print(re.sub(r"<[^>]+>", "", Bot("NSE", state={}).handle(" ".join(sys.argv[2:]))))
