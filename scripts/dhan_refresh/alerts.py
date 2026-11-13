"""Morning brief, intraday alerts and close summary for Telegram.

Everything here is built from data the repo already has: docs/n500.json (nightly
Nifty 500 board with setups, trigger and fail levels), docs/setup-backtest-n500.json
(6-year back-test) and the live quotes the poller fetches every 5 seconds.
Optional config/watchlist.json lists your own positions and stocks to watch:

  {"positions": [{"s": "TCS", "stop": 3200, "target": 3600}], "watch": ["RELIANCE"]}
"""
from __future__ import annotations

import json
from pathlib import Path

from telegram import esc

ROOT = Path(__file__).resolve().parents[2]
EDGE = ("volbreak", "pullback")          # the two setups with a tested edge on the Nifty 500
SETUP_NAME = {"volbreak": "Volume breakout", "pullback": "Pullback in uptrend", "breakout": "Breakout",
              "coiled": "Coiled range", "turn": "Turn up"}
MOVE_PCT = 3.0                            # alert when a picked or watched stock moves this much
NIFTY_PCT = 1.0                           # alert when Nifty moves this much


def _load(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def board() -> dict:
    return _load(ROOT / "docs/n500.json", {"rows": []})


def watchlist() -> dict:
    w = _load(ROOT / "config/watchlist.json", {})
    return {"positions": w.get("positions", []), "watch": w.get("watch", [])}


def backtest() -> dict:
    return _load(ROOT / "docs/setup-backtest-n500.json", {}).get("setups", {})


def picks(rows: list, n: int = 5) -> list:
    """Today's candidates: tested-edge setups on stocks that are leading or improving, best score first."""
    good = [r for r in rows if r.get("setup") in EDGE and r.get("status") in ("lead", "improve") and r.get("trig")]
    good.sort(key=lambda r: -(r.get("score") or 0))
    return good[:n]


def watching(rows: list) -> list:
    """Other setups worth a look but without a tested edge."""
    other = [r for r in rows if r.get("setup") and r.get("setup") not in EDGE and r.get("status") in ("lead", "improve")]
    other.sort(key=lambda r: -(r.get("score") or 0))
    return other[:5]


def pct(x) -> str:
    return f"{x * 100:+.1f}%"


def morning_brief(nset: dict, b: dict | None = None) -> str:
    b = b or board()
    rows = b.get("rows", [])
    bt = backtest()
    nf = nset.get("idx", {}).get("Nifty 50", {})
    c = nf.get("c", [])
    lines = [f"<b>NSE brief</b> · data to {esc(b.get('asof', '?'))} close"]
    if len(c) >= 2:
        ma50 = sum(c[-50:]) / min(50, len(c))
        trend = "above" if c[-1] > ma50 else "below"
        lines.append(f"Nifty 50 {c[-1]:,.0f} ({pct(c[-1] / c[-2] - 1)}), {trend} its 50-day average.")
        if trend == "below":
            lines.append("The setups' edge was measured in rising markets, so size down while Nifty is below its 50-day average.")
    vix = nset.get("idx", {}).get("India VIX", {}).get("c", [])
    if vix:
        lines.append(f"India VIX {vix[-1]:.1f}.")
    if rows:
        up = sum(1 for r in rows if (r.get("r1") or 0) > 0)
        lead = sum(1 for r in rows if r.get("status") == "lead")
        lines.append(f"Breadth: {up} of {len(rows)} Nifty 500 stocks rose; {lead} are leaders.")
    p = picks(rows)
    lines.append("")
    if p:
        lines.append("<b>Setups with a tested edge</b>")
        for r in p:
            s = bt.get(r["setup"], {}).get("up", {})
            edge = f", past 21-day avg {s['m21'] * 100:+.1f}%" if s.get("m21") is not None else ""
            if r["last"] > r["trig"]:
                plan = f"broke out above ₹{r['trig']:,.1f}; alert if it pulls back there"
            else:
                plan = f"alert above ₹{r['trig']:,.1f}"
            lines.append(f"• <b>{esc(r['s'])}</b> {esc(SETUP_NAME.get(r['setup'], r['setup']))}: ₹{r['last']:,.1f}, {plan}; "
                         f"off below ₹{r['fail']:,.1f} (score {r.get('score')}{edge})")
    else:
        lines.append("No tested-edge setups on leading stocks today. Sitting out is a position.")
    w = watching(rows)
    if w:
        lines.append("")
        lines.append("<b>Also on the radar</b> (no tested edge): " + ", ".join(
            f"{esc(r['s'])} ({esc(SETUP_NAME.get(r['setup'], r['setup']).lower())})" for r in w))
    wl = watchlist()
    if wl["positions"]:
        bysym = {r["s"]: r for r in rows}
        lines.append("")
        lines.append("<b>Your positions</b>")
        for pos in wl["positions"]:
            r = bysym.get(pos.get("s"), {})
            last = r.get("last")
            bits = [f"• {esc(pos.get('s'))}"]
            if last:
                bits.append(f"₹{last:,.1f}")
            if pos.get("stop") and last:
                bits.append(f"stop ₹{pos['stop']:,.1f} ({(pos['stop'] / last - 1) * 100:+.1f}%)")
            if pos.get("target") and last:
                bits.append(f"target ₹{pos['target']:,.1f} ({(pos['target'] / last - 1) * 100:+.1f}%)")
            if r.get("status"):
                bits.append(f"[{r['status']}]")
            lines.append(" ".join(bits))
    lines.append("")
    lines.append("Research, not advice. Back-test: 6 years, Nifty 500, rising markets.")
    return "\n".join(lines)


class Alerts:
    """Checks each poll against today's picks, watchlist and Nifty; each alert fires once a day."""

    def __init__(self, idx_names: dict, sent: list | None = None, b: dict | None = None):
        b = b or board()
        rows = b.get("rows", [])
        self.bysid = {str(r["sid"]): r for r in rows if r.get("sid")}
        self.bysym = {r["s"]: r for r in rows}
        self.picks = {str(r["sid"]): r for r in picks(rows)}
        wl = watchlist()
        self.positions = {}
        for p in wl["positions"]:
            r = self.bysym.get(p.get("s"))
            if r and r.get("sid"):
                self.positions[str(r["sid"])] = p
        self.watch = {str(self.bysym[s]["sid"]) for s in wl["watch"] if s in self.bysym and self.bysym[s].get("sid")}
        self.nifty = next((k for k, v in idx_names.items() if v == "Nifty 50"), "13")
        self.sent = set(sent or [])
        # Dhan's "close" field is yesterday's close during the session but today's after 15:30,
        # so remember yesterday's close the first time each instrument is seen before 15:29.
        self.prev: dict = {}

    def base(self, seg: str, sid: str, v: list, hhmm: str) -> float:
        key = f"{seg}:{sid}"
        if key not in self.prev and hhmm < "15:29" and v[4] > 0:
            self.prev[key] = v[4]
        if key in self.prev:
            return self.prev[key]
        r = self.bysid.get(sid) if seg == "NSE_EQ" else None
        return (r or {}).get("last") or (v[4] if hhmm < "15:29" else 0.0)

    def _once(self, key: str, text: str, out: list) -> None:
        if key not in self.sent:
            self.sent.add(key)
            out.append(text)

    def check(self, q: dict, hhmm: str) -> list:
        out: list = []
        eq = q.get("NSE_EQ", {})
        for sid, v in eq.items():
            ltp, prev = v[0], self.base("NSE_EQ", sid, v, hhmm)
            r = self.bysid.get(sid)
            if not r or ltp <= 0:
                continue
            chg = (ltp / prev - 1) * 100 if prev > 0 else 0.0
            name = esc(r["s"])
            before = len(out)
            if sid in self.picks:
                p = self.picks[sid]
                if p["last"] <= p["trig"] and ltp > p["trig"]:
                    self._once(f"trig:{sid}", f"🟢 <b>{name}</b> broke its trigger ₹{p['trig']:,.1f}: now ₹{ltp:,.1f} ({chg:+.1f}%) at {hhmm}. "
                               f"Setup fails below ₹{p['fail']:,.1f}.", out)
                elif p["last"] > p["trig"] and p["fail"] < ltp <= p["trig"] * 1.01:
                    self._once(f"retest:{sid}", f"🔵 <b>{name}</b> is back at its breakout level ₹{p['trig']:,.1f}: now ₹{ltp:,.1f} at {hhmm}. "
                               f"Setup holds while above ₹{p['fail']:,.1f}.", out)
                if ltp < p["fail"]:
                    self._once(f"fail:{sid}", f"🔴 <b>{name}</b> fell below its fail level ₹{p['fail']:,.1f}: now ₹{ltp:,.1f} at {hhmm}. Setup is off.", out)
            if sid in self.positions:
                pos = self.positions[sid]
                if pos.get("stop") and ltp <= pos["stop"]:
                    self._once(f"stop:{sid}", f"🛑 <b>{name}</b> hit your stop ₹{pos['stop']:,.1f}: now ₹{ltp:,.1f} at {hhmm}.", out)
                if pos.get("target") and ltp >= pos["target"]:
                    self._once(f"tgt:{sid}", f"🎯 <b>{name}</b> reached your target ₹{pos['target']:,.1f}: now ₹{ltp:,.1f} at {hhmm}.", out)
            if (sid in self.picks or sid in self.positions or sid in self.watch) and abs(chg) >= MOVE_PCT:
                if len(out) > before:          # one message per stock per check
                    self.sent.add(f"move{'+' if chg > 0 else '-'}:{sid}")
                    continue
                self._once(f"move{'+' if chg > 0 else '-'}:{sid}", f"{'📈' if chg > 0 else '📉'} <b>{name}</b> {chg:+.1f}% at ₹{ltp:,.1f} ({hhmm}).", out)
        nv = q.get("IDX_I", {}).get(self.nifty)
        nprev = self.base("IDX_I", self.nifty, nv, hhmm) if nv else 0
        if nv and nprev > 0:
            chg = (nv[0] / nprev - 1) * 100
            if abs(chg) >= NIFTY_PCT:
                self._once(f"nifty{'+' if chg > 0 else '-'}", f"{'📈' if chg > 0 else '📉'} Nifty 50 {chg:+.1f}% at {nv[0]:,.0f} ({hhmm}).", out)
        return out


def close_summary(q: dict, idx_names: dict, prev: dict | None = None, b: dict | None = None) -> str:
    """prev: {"SEG:sid": yesterday's close} recorded during the session (see Alerts.base)."""
    b = b or board()
    prev = prev or {}
    rows = b.get("rows", [])
    bysid = {str(r["sid"]): r for r in rows if r.get("sid")}
    eq = q.get("NSE_EQ", {})
    lines = ["<b>Close summary</b>"]
    for sid, nm in idx_names.items():
        if nm in ("Nifty 50", "Nifty Bank", "Nifty Midcap 100"):
            v = q.get("IDX_I", {}).get(str(sid))
            pv = prev.get(f"IDX_I:{sid}")
            if v and pv:
                lines.append(f"{esc(nm)} {v[0]:,.0f} ({(v[0] / pv - 1) * 100:+.2f}%)")
    moves = []
    for sid, v in eq.items():
        pv = prev.get(f"NSE_EQ:{sid}") or (bysid.get(sid) or {}).get("last")
        if sid in bysid and v[0] > 0 and pv:
            moves.append((v[0] / pv - 1, bysid[sid]["s"]))
    if moves:
        moves.sort()
        up = sum(1 for m, _ in moves if m > 0)
        down = sum(1 for m, _ in moves if m < 0)
        lines.append(f"Breadth: {up} up, {down} down, {len(moves) - up - down} unchanged.")
        top = [(m, s) for m, s in moves[::-1] if m > 0][:5]
        bottom = [(m, s) for m, s in moves if m < 0][:5]
        if top:
            lines.append("Top: " + ", ".join(f"{esc(s)} {m * 100:+.1f}%" for m, s in top))
        if bottom:
            lines.append("Bottom: " + ", ".join(f"{esc(s)} {m * 100:+.1f}%" for m, s in bottom))
    p = picks(rows)
    if p:
        lines.append("")
        lines.append("<b>This morning's setups</b>")
        for r in p:
            v = eq.get(str(r["sid"]))
            if not v or v[0] <= 0:
                continue
            state = ("held the breakout" if v[0] > r["trig"] else "back below the breakout level") if r["last"] > r["trig"] \
                else ("triggered" if v[2] > r["trig"] else "not triggered")
            if v[0] < r["fail"]:
                state = "failed"
            pv = prev.get(f"NSE_EQ:{r['sid']}") or r["last"]
            lines.append(f"• {esc(r['s'])} ₹{v[0]:,.1f} ({(v[0] / pv - 1) * 100:+.1f}%), {state}")
    return "\n".join(lines)
