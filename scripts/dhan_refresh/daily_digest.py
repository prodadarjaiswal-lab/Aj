"""Nightly: review the owner's research journal against the desk, and send the day's digest to Telegram.

Journal: every stock asked about in Telegram (bot state, encrypted on the 'bot' branch). The review says
  * what happened to the stocks you researched since you looked (vs the Nifty),
  * follow-ups: stocks you researched whose evidence changed (a tested signal fired, a tested warning, a big move),
  * blind spots: strong-evidence stocks and industries you have not looked at, and screens you never use,
  * habit check: the kind of stocks you look at (falling vs leading) and how they did against the top-evidence names.
Writes docs/journal-review.json (for the desk) and sends one Telegram message with the desk link.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _j(name, default):
    try:
        return json.loads((ROOT / name).read_text(encoding="utf-8"))
    except Exception:
        return default


def review(journal: list, rs: dict, board: dict, days: int = 60) -> dict:
    stocks = rs.get("stocks", {})
    bysym = {r["s"]: r for r in board.get("rows", [])}
    tested = set((rs.get("tested") or {}).get("tech", [])) | set((rs.get("tested") or {}).get("inv", []))
    cut = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    recent = [x for x in journal if str(x.get("t", ""))[:10] >= cut and x.get("sym")]
    seen = {}
    for x in recent:
        seen.setdefault(x["sym"], []).append(x)
    looked = []
    for s, xs in seen.items():
        first = xs[0]
        now = (bysym.get(s) or {}).get("last") or (stocks.get(s) or {}).get("last")
        chg = (now / first["price"] - 1) if now and first.get("price") else None
        looked.append({"s": s, "n": len(xs), "first": first["t"][:10], "last_t": xs[-1]["t"][:10], "price": first.get("price"),
                       "now": now, "chg": round(chg, 4) if chg is not None else None, "cmds": sorted({x.get("cmd") for x in xs})})
    looked.sort(key=lambda x: x["last_t"], reverse=True)
    follow = []
    for x in looked:
        r = stocks.get(x["s"]) or {}
        why = []
        new_t = [k for k in r.get("setups", []) + r.get("inv", []) if k in tested]
        if new_t:
            why.append("tested signal now: " + ", ".join(new_t))
        if r.get("warn"):
            why.append("tested warning: " + ", ".join(r["warn"]))
        if x["chg"] is not None and abs(x["chg"]) >= 0.08:
            why.append(f"{x['chg'] * 100:+.0f}% since you looked on {x['first']}")
        if (r.get("d_fii") or 0) <= -1 or (r.get("d_fii") or 0) >= 1:
            why.append(f"FII holding {r['d_fii']:+.1f} pp")
        if why:
            follow.append({"s": x["s"], "why": why, "score": r.get("score")})
    mine = set(seen)
    top = sorted(((s, x) for s, x in stocks.items() if x.get("score", 0) >= 4 and s not in mine), key=lambda z: -z[1]["score"])
    blind = [{"s": s, "score": x["score"], "ind": x.get("ind"), "ev": [e[1] for e in x.get("ev", []) if e[0] in ("tech", "inv", "fund")][:3]}
             for s, x in top[:10]]
    ind_seen = {(stocks.get(s) or {}).get("ind") for s in mine}
    ind_strength = {}
    for s, x in stocks.items():
        if x.get("score", 0) >= 4:
            ind_strength.setdefault(x.get("ind") or "?", []).append(s)
    blind_ind = sorted(([i, len(v), v[:3]] for i, v in ind_strength.items() if i not in ind_seen and len(v) >= 2), key=lambda z: -z[1])[:5]
    falling = sum(1 for s in mine if ((stocks.get(s) or {}).get("r3m") or 0) <= -0.10)
    leading = sum(1 for s in mine if ((stocks.get(s) or {}).get("rs3") or 0) >= 0.10)
    habit = []
    if mine:
        if falling / len(mine) >= 0.5:
            habit.append(f"{falling} of {len(mine)} stocks you researched are down 10%+ in 3 months. The back-test favours strength "
                         "(momentum, trend recovery); falling stocks only pay with a tested dip signal.")
        if leading / len(mine) < 0.2 and len(mine) >= 5:
            habit.append("You rarely look at leaders (3-month strength 10%+ over the Nifty). Try the 'Best evidence' and 'Leaders' screens.")
    mean = lambda a: sum(a) / len(a) if a else None
    my_ret = mean([x["chg"] for x in looked if x["chg"] is not None])
    return {"asof": rs.get("asof"), "days": days, "lookups": len(recent), "stocks": len(mine), "looked": looked[:40],
            "follow": follow[:12], "blind": blind, "blind_ind": blind_ind, "habit": habit,
            "my_avg_since": round(my_ret, 4) if my_ret is not None else None}


def digest_text(rv: dict, rs: dict, desk_url: str) -> str:
    import telegram as T
    st = rs.get("stocks", {})
    top = sorted(st.items(), key=lambda z: -z[1].get("score", 0))[:5]
    lines = [f"<b>Desk updated</b> · Dhan data to {T.esc(rs.get('asof'))} · {'rising' if rs.get('side') == 'up' else 'weak'} market",
             "<b>Best evidence</b>: " + ", ".join(f"{T.esc(s)} ({x['score']:g})" for s, x in top)]
    if rv["follow"]:
        lines.append("<b>Follow up (you researched these)</b>")
        lines += [f"• {T.esc(f['s'])}: {T.esc('; '.join(f['why']))}" for f in rv["follow"][:4]]
    if rv["blind"]:
        lines.append("<b>You haven't looked at</b>: " + ", ".join(f"{T.esc(b['s'])} ({b['score']:g})" for b in rv["blind"][:5]))
    if rv["blind_ind"]:
        lines.append("<b>Strong industries you skip</b>: " + ", ".join(f"{T.esc(i)} ({n})" for i, n, _ in rv["blind_ind"][:3]))
    for h in rv["habit"][:1]:
        lines.append("<i>" + T.esc(h) + "</i>")
    lines.append(f'<a href="{desk_url}">Open the Technical Desk</a>')
    return "\n".join(lines)


def main() -> int:
    import bot as B
    import telegram as T
    st = B.load_state() if T.enabled() else {}
    rs, board = _j("docs/research.json", {}), _j("docs/n500.json", {"rows": []})
    rv = review(st.get("journal", []), rs, board)
    (ROOT / "docs/journal-review.json").write_text(json.dumps(rv, separators=(",", ":")), encoding="utf-8")
    print(f"journal review: {rv['lookups']} lookups, {rv['stocks']} stocks, {len(rv['follow'])} follow-ups, {len(rv['blind'])} blind spots")
    if "--send" in sys.argv and T.enabled() and rs.get("stocks"):
        print("digest sent" if T.send(digest_text(rv, rs, B.DESK_URL)) else "digest not sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
