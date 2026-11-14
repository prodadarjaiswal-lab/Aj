"""Everything-else snapshot from Dhan: commodities (MCX), currency, indices, and news.

  * MCX futures (nearest expiry): gold, silver, crude oil, natural gas, copper.
  * NSE currency future: USDINR (nearest expiry).
  * Indices already tracked by the terminal (IDX_I).
  * Dhan news headlines (POST /v2/data/newsheadline): the general market feed, and
    per-stock headlines for the day's biggest Nifty 500 movers, so the bot can show
    the likely reason a stock rose or fell. A headline next to a move is a possible
    reason, not a proven cause.
All prices come from Dhan; anything Dhan did not return is left out and reported.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
from pathlib import Path

COMMODITIES = ("GOLD", "SILVER", "CRUDEOIL", "NATURALGAS", "COPPER")
NAMES = {"GOLD": "Gold (MCX, Rs/10 g)", "SILVER": "Silver (MCX, Rs/kg)", "CRUDEOIL": "Crude oil (MCX, Rs/bbl)",
         "NATURALGAS": "Natural gas (MCX, Rs/mmBtu)", "COPPER": "Copper (MCX, Rs/kg)", "USDINR": "USD/INR (NSE future)"}


def _expiry(r: dict):
    for k in ("SEM_EXPIRY_DATE", "SM_EXPIRY_DATE"):
        v = (r.get(k) or "").strip()
        if v:
            try:
                return dt.date.fromisoformat(v[:10])
            except ValueError:
                continue
    return None


def pick_futures(scrip_csv: str, today: dt.date) -> dict:
    """{name: (segment, security_id, trading_symbol, expiry)} for the nearest live future of each."""
    best = {}
    for r in csv.DictReader(io.StringIO(scrip_csv)):
        exch, inst = r.get("SEM_EXM_EXCH_ID", ""), r.get("SEM_INSTRUMENT_NAME", "")
        sym = (r.get("SEM_TRADING_SYMBOL") or "").upper()
        base = sym.split("-")[0]
        if exch == "MCX" and inst == "FUTCOM" and base in COMMODITIES:
            seg, name = "MCX_COMM", base
        elif base == "USDINR" and inst.startswith("FUT") and exch in ("NSE", "BSE"):
            seg, name = ("NSE_CURRENCY" if exch == "NSE" else "BSE_CURRENCY"), "USDINR"
        else:
            continue
        exp = _expiry(r)
        if not exp or exp < today:
            continue
        if name not in best or exp < best[name][3]:
            best[name] = (seg, r["SEM_SMST_SECURITY_ID"], sym, exp)
    return best


def _headlines(obj) -> list:
    """Find headline records anywhere in Dhan's reply, whatever the nesting."""
    out = []
    if isinstance(obj, dict):
        title = obj.get("title") or obj.get("headline") or obj.get("newsTitle")
        if isinstance(title, str) and title.strip():
            out.append({"title": title.strip(),
                        "time": str(obj.get("publishedAt") or obj.get("publishTime") or obj.get("time") or obj.get("date") or obj.get("createdAt") or ""),
                        "source": str(obj.get("source") or obj.get("publisher") or ""),
                        "category": str(obj.get("category") or "")})
        for v in obj.values():
            if isinstance(v, (dict, list)):
                out += _headlines(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _headlines(v)
    seen, uniq = set(), []
    for h in out:
        if h["title"] not in seen:
            seen.add(h["title"])
            uniq.append(h)
    return uniq


def news(dhan, client_id: str, categories=("ALL",), stock_ids=None, limit: int = 20) -> list:
    body = {"dhanClientId": client_id, "categories": list(categories), "limit": limit}
    if stock_ids:
        body["stockList"] = [str(x) for x in stock_ids]
    return _headlines(dhan.post("/data/newsheadline", body))


def run(dhan, scrip_csv: str, root, now: dt.datetime) -> str:
    root = Path(root)
    out = {"asof": now.strftime("%Y-%m-%d %H:%M"), "source": "Dhan", "futures": {}, "news": {}, "movers": [], "missing": []}
    fut = pick_futures(scrip_csv, now.date())
    body = {}
    for name, (seg, sid, sym, exp) in fut.items():
        body.setdefault(seg, []).append(int(sid))
    out["missing"] += [n for n in list(COMMODITIES) + ["USDINR"] if n not in fut]
    if "USDINR" not in fut:                                   # show what Dhan's list calls it, to fix the match
        seen = [(r.get("SEM_EXM_EXCH_ID"), r.get("SEM_INSTRUMENT_NAME"), r.get("SEM_TRADING_SYMBOL"), r.get("SEM_EXPIRY_DATE"))
                for r in csv.DictReader(io.StringIO(scrip_csv)) if "USDINR" in (r.get("SEM_TRADING_SYMBOL") or "").upper()][:5]
        print(f"  USDINR rows in Dhan's list: {seen}")
        out["missing"] = [m for m in out["missing"] if m != "USDINR"] + ["USDINR (no live contract in Dhan's instrument list)"]
    if body:
        try:
            q = dhan.post("/marketfeed/quote", body).get("data") or {}
            for name, (seg, sid, sym, exp) in fut.items():
                v = (q.get(seg) or {}).get(str(sid))
                if not v or not v.get("last_price"):
                    out["missing"].append(name)
                    continue
                prev = float((v.get("ohlc") or {}).get("close") or 0)
                ltp = float(v["last_price"])
                out["futures"][name] = {"name": NAMES[name], "contract": sym, "expiry": exp.isoformat(), "ltp": ltp, "prev": prev,
                                        "chg": round(ltp / prev - 1, 5) if prev else None, "oi": v.get("oi"),
                                        "high": (v.get("ohlc") or {}).get("high"), "low": (v.get("ohlc") or {}).get("low")}
        except Exception as e:
            out["missing"].append(f"futures quote failed: {str(e)[:80]}")
    cid = getattr(dhan, "client_id", "")
    for cat in ("EQUITY_MARKETS", "COMMODITIES", "CURRENCY", "GLOBAL", "INDIAN_ECONOMY"):
        try:
            out["news"][cat] = news(dhan, cid, (cat,), limit=8)
        except Exception as e:
            out["missing"].append(f"news {cat}: {str(e)[:60]}")
    try:
        board = json.loads((root / "docs/n500.json").read_text(encoding="utf-8"))
        rows = [r for r in board.get("rows", []) if r.get("r1") is not None and r.get("sid")]
        rows.sort(key=lambda r: r["r1"])
        movers = rows[:6] + rows[-6:][::-1]
        for r in movers:
            try:
                hs = news(dhan, cid, ("ALL",), [r["sid"]], limit=3)
            except Exception as e:
                hs = []
                out["missing"].append(f"news {r['s']}: {str(e)[:40]}")
            out["movers"].append({"s": r["s"], "r1": r["r1"], "last": r.get("last"), "headlines": hs})
    except Exception as e:
        out["missing"].append(f"movers: {str(e)[:60]}")
    (root / "docs/markets.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    return f"markets: {len(out['futures'])} futures, {sum(len(v) for v in out['news'].values())} headlines, {len(out['movers'])} movers; missing {out['missing'][:4]}"


if __name__ == "__main__":
    import os
    import sys
    import requests
    import refresh as R
    root = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else Path("../..")
    cid, pin, sec = (os.environ[k] for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"))
    d = R.Dhan(cid, R.login(cid, pin, sec))
    print(run(d, requests.get(R.SCRIP_MASTER, timeout=60).text, root, dt.datetime.now(R.IST)))
