"""Research profile for every Nifty 500 stock: what a research desk would check before a name goes on a list.

For each stock, from Dhan data only:
  * setups:     technical signals active today, and which of them passed the back-test (tech_model)
  * investor:   6-12 month rules active today, and which passed (value_model)
  * flow:       last session's VWAP position, value-area acceptance and estimated buyer share (auction, 1-minute bars)
  * options:    put/call ratio, implied volatility and dealer gamma when the stock has options
  * valuation:  P/E, P/E against its sector, P/B against the industry, dividend yield (Dhan company info)
  * quality:    ROCE, debt/equity
  * ownership:  promoter, FII and DII holdings and their latest change (Dhan)
  * why down:   the last 3 months' move split into market (beta x Nifty), sector (peers in the same industry)
                and stock-specific parts, plus ownership and valuation changes
  * score:      counts only evidence that passed a back-test; everything else is a filter, labelled untested
"""
from __future__ import annotations

import datetime as dt
import json
import math
import statistics as stt
from pathlib import Path

HIST_EVERY = 6        # days between stored fundamentals snapshots (weekly history, to show ratios improving)
HIST_KEEP = 60


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def compact_fund(raw: dict) -> dict:
    d = (raw or {}).get("data") or raw or {}
    co, ra, sh = d.get("CO") or {}, d.get("RATIOS") or {}, d.get("SHP") or {}
    return {"pe": _f(ra.get("PE_RATIO")), "pe_sec": _f(ra.get("PE_TO_SECTOR_PE")), "pb": _f(ra.get("PB_RATIO")),
            "pb_ind": _f(ra.get("INDUSTRY_PB_RATIO")), "roce": _f(ra.get("ROCE")), "roe": _f(ra.get("ROE")),
            "de": _f(ra.get("DEBT_TO_EQUITY")), "de_ind": _f(ra.get("INDUSTRY_DEBT_TO_EQUITY")),
            "dy": _f(co.get("DIVIDEND_YIELD")), "dy_ind": _f(ra.get("INDUSTRY_DIVIDEND_YIELD")), "eps": _f(co.get("EPS")),
            "mcap": _f(co.get("MARKET_CAP")), "sector": co.get("SECTOR"), "industry": co.get("INDUSTRY"),
            "prom": _f(sh.get("PROMOTER_HOLDING")), "fii": _f(sh.get("FII_HOLDING")), "dii": _f(sh.get("DII_HOLDING")),
            "d_fii": _f(sh.get("CHANGE_IN_FII_HOLDING")), "d_dii": _f(sh.get("CHANGE_IN_DII_HOLDING"))}


def fetch_fund(dhan, rows: list, root: Path, today: str) -> dict:
    """Dhan company info for every stock (about 2 minutes); keeps a weekly history of the key ratios."""
    p = root / "docs/fund500.json"
    try:
        store = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        store = {"now": {}, "hist": {}}
    ok = 0
    for r in rows:
        sid = r.get("sid")
        if not sid:
            continue
        try:
            f = compact_fund(dhan.company(sid))
        except Exception as e:
            print(f"  company info {r['s']}: {str(e)[:80]}")
            continue
        ok += 1
        store["now"][r["s"]] = f
        h = store["hist"].setdefault(r["s"], [])
        if not h or (dt.date.fromisoformat(today) - dt.date.fromisoformat(h[-1][0])).days >= HIST_EVERY:
            h.append([today, f["pe"], f["eps"], f["roce"], f["de"], f["prom"], f["fii"], f["dii"]])
            del h[:-HIST_KEEP]
    store["asof"] = today
    p.write_text(json.dumps(store, separators=(",", ":")), encoding="utf-8")
    print(f"  company info: {ok} of {len(rows)} stocks")
    return store


def _ret(c, n):
    return c[-1] / c[-1 - n] - 1 if len(c) > n and c[-1 - n] else None


def beta(c, m, n=250):
    r = [c[k] / c[k - 1] - 1 for k in range(len(c) - n, len(c)) if c[k - 1]]
    q = [m[k] / m[k - 1] - 1 for k in range(len(m) - n, len(m)) if m[k - 1]]
    k = min(len(r), len(q))
    if k < 60:
        return 1.0
    r, q = r[-k:], q[-k:]
    mq = sum(q) / k
    vq = sum((x - mq) ** 2 for x in q)
    return sum((a - sum(r) / k) * (b - mq) for a, b in zip(r, q)) / vq if vq else 1.0


def why_move(sym: str, c: list, nifty_c: list, peers: list, b: float, fund: dict | None, hist: list | None, n: int = 63) -> dict:
    """Split the last n sessions' return into market, sector and stock-specific parts, with ownership and
    valuation changes. peers: n-day returns of other stocks in the same industry."""
    r, mr = _ret(c, n), _ret(nifty_c, n)
    if r is None or mr is None:
        return {}
    market = b * mr
    sector = (stt.median(peers) - mr) if len(peers) >= 3 else 0.0
    own = r - market - sector
    parts = {"market": round(market, 4), "sector": round(sector, 4), "stock": round(own, 4), "total": round(r, 4)}
    big = max(parts, key=lambda k: abs(parts[k]) if k != "total" else -1)
    label = {"market": "mostly the whole market", "sector": "mostly its sector", "stock": "mostly company-specific"}[big]
    notes = []
    f = fund or {}
    if f.get("d_fii") is not None and abs(f["d_fii"]) >= 0.5:
        notes.append(f"FIIs {'added' if f['d_fii'] > 0 else 'cut'} {abs(f['d_fii']):.1f} pp last quarter")
    if f.get("d_dii") is not None and abs(f["d_dii"]) >= 0.5:
        notes.append(f"DIIs {'added' if f['d_dii'] > 0 else 'cut'} {abs(f['d_dii']):.1f} pp")
    if hist and len(hist) >= 2:
        a, z = hist[0], hist[-1]
        if a[2] and z[2] and abs(z[2] / a[2] - 1) >= 0.05:
            notes.append(f"EPS {'up' if z[2] > a[2] else 'down'} {abs(z[2] / a[2] - 1) * 100:.0f}% since {a[0]}")
        if a[1] and z[1] and abs(z[1] / a[1] - 1) >= 0.10 and (not a[2] or not z[2] or abs(z[2] / a[2] - 1) < 0.05):
            notes.append(f"P/E {'re-rated up' if z[1] > a[1] else 'de-rated'} {a[1]:.0f} → {z[1]:.0f} with earnings flat")
    return {**parts, "driver": big, "label": label, "notes": notes, "days": n}


def run(data: dict, nifty: dict, root: Path, dhan=None) -> str:
    rows = json.loads((root / "docs/n500.json").read_text(encoding="utf-8")).get("rows", [])
    today = nifty["d"][-1]
    if dhan is not None:
        fund = fetch_fund(dhan, rows, root, today)
    else:
        try:
            fund = json.loads((root / "docs/fund500.json").read_text(encoding="utf-8"))
        except Exception:
            fund = {"now": {}, "hist": {}}
    j = lambda name, default: (json.loads((root / name).read_text(encoding="utf-8")) if (root / name).exists() else default)
    tech, model = j("docs/tech-today.json", {}).get("stocks", {}), j("docs/tech-model.json", {})
    vm, auc, quant = j("docs/value-model.json", {}), j("docs/auction.json", {}).get("symbols", {}), j("docs/quant.json", {})
    nc = nifty["c"]
    n200 = sum(nc[-200:]) / 200 if len(nc) >= 200 else None
    side = "up" if n200 and nc[-1] > n200 else "weak"
    sig = model.get("signals", {})
    warn = {"extended", "downtrend"}
    t_ok = {k for k, v in sig.items() if v.get("tested" if side == "up" else "tested_weak") and k not in warn}
    t_warn = {k for k, v in sig.items() if k in warn and v.get("tested" if side == "up" else "tested_weak")}
    v_ok = {k for k, v in (vm.get("rules") or {}).items() if v.get(f"tested_{side}")}
    fq = ((vm.get("fundamental") or {}).get("quintiles")) or {}
    by_ind = {}
    r63 = {}
    for r in rows:
        o = data.get(r["s"])
        if o and len(o["c"]) > 64:
            r63[r["s"]] = _ret(o["c"], 63)
            by_ind.setdefault(r.get("ind") or (fund["now"].get(r["s"]) or {}).get("industry") or "?", []).append(r["s"])
    out = {}
    for r in rows:
        s = r["s"]
        o = data.get(s)
        if not o or len(o["c"]) < 260:
            continue
        c = o["c"]
        t = tech.get(s, {})
        f = fund["now"].get(s) or {}
        a = auc.get(s) or {}
        ind = r.get("ind") or f.get("industry") or "?"
        peers = [r63[x] for x in by_ind.get(ind, []) if x != s and r63.get(x) is not None]
        b = beta(c, nc)
        turnover = (sum(x * y for x, y in zip(c[-20:], (o.get("v") or [0] * 20)[-20:])) / 20) / 1e7 if o.get("v") else None
        on = set(t.get("new", []))          # fired in the last 3 sessions: the back-test measured signals on the day they appear
        vin = set(((vm.get("today") or {}).get(s) or {}).get("on", []))
        score, ev = 0.0, []
        for k in sorted(on & t_ok):
            score += 2
            ev.append(["tech", k])
        for k in sorted(on & t_warn):
            score -= 2
            ev.append(["warn", k])
        for n_, k in enumerate(sorted(vin & v_ok)):      # investor rules overlap (most measure strength): 2, then 1, 1; at most 4
            score += 2 if n_ == 0 else 1 if n_ < 3 else 0
            ev.append(["inv", k])
        for k, q in (fq.get(s) or {}).items():
            if q >= 4:
                score += 1
                ev.append(["fund", k])
        mc = (quant.get("mc") or {}).get(s)
        if mc and mc.get("p_up") is not None and mc["p_up"] >= 0.55:
            score += 0.5
            ev.append(["mc", round(mc["p_up"], 2)])
        vw, au, de = a.get("vwap") or {}, a.get("auction") or {}, a.get("delta") or {}
        val = None
        if f.get("pe_sec") is not None and f.get("pe") and f["pe"] > 0:
            cheap = f["pe_sec"] <= 0.8
            dear = f["pe_sec"] >= 1.3
            quality = (f.get("roce") or 0) >= 12 and (f.get("de") is None or f["de"] <= 1.5)
            val = "cheap" if cheap and quality else "cheap, weak quality" if cheap else "expensive" if dear else "fair"
        elif f.get("pe") is not None and f["pe"] <= 0:
            val = "loss-making"
        out[s] = {
            "ind": ind, "last": round(c[-1], 2), "r1m": _ret(c, 21), "r3m": _ret(c, 63), "r6m": _ret(c, 126),
            "rs3": (t.get("rs3") / 100) if t.get("rs3") is not None else None, "vs200": t.get("vs200"), "rsi": t.get("rsi"),
            "adx": t.get("adx"), "volx": t.get("volx"), "beta": round(b, 2), "turnover_cr": round(turnover, 1) if turnover else None,
            "setups": sorted(on - warn), "warn": sorted(on & warn), "inv": sorted(vin),
            "vwap": vw.get("state"), "vwap_sd": vw.get("dev_sd"), "auction": au.get("read"), "buy": de.get("buy_share_est"),
            "swing": a.get("swing") or [],
            "pe": f.get("pe"), "pe_sec": f.get("pe_sec"), "pb": f.get("pb"), "pb_ind": f.get("pb_ind"), "roce": f.get("roce"),
            "de": f.get("de"), "dy": f.get("dy"), "prom": f.get("prom"), "fii": f.get("fii"), "d_fii": f.get("d_fii"),
            "dii": f.get("dii"), "d_dii": f.get("d_dii"), "value": val, "fq": fq.get(s) or {},
            "p_up": round(mc["p_up"], 2) if mc and mc.get("p_up") is not None else None,
            "score": round(score, 1), "ev": ev,
            "why": why_move(s, c, nc, peers, b, f, (fund.get("hist") or {}).get(s)),
        }
        for k in ("r1m", "r3m", "r6m"):
            if out[s][k] is not None:
                out[s][k] = round(out[s][k], 4)
    res = {"asof": today, "side": side, "stocks": out, "tested": {"tech": sorted(t_ok), "warn": sorted(t_warn), "inv": sorted(v_ok)},
           "fund_asof": fund.get("asof"),
           "method": ("Score = 2 per technical signal that passed the 6-year back-test for today's market, 2 for the first investor rule that passed and 1 each for "
                      "the next two (they overlap), 1 per tested value factor in the top two-fifths, 0.5 if the Monte Carlo chance of a rise is 55%+, minus 2 "
                      "per tested warning. Valuation, ownership, order flow and options are filters and context: they have not passed "
                      "a back-test, so they do not add to the score.")}
    (root / "docs/research.json").write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
    top = sorted(out.items(), key=lambda x: -x[1]["score"])[:5]
    return f"research: {len(out)} stocks; fundamentals for {len(fund.get('now', {}))}; top {[(k, v['score']) for k, v in top]}"


def rescore(root: Path) -> str:
    """Recompute setups, evidence and score in docs/research.json from the latest model files (no Dhan calls)."""
    j = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    res, tech, model, vm, quant = j("docs/research.json"), j("docs/tech-today.json")["stocks"], j("docs/tech-model.json"), j("docs/value-model.json"), j("docs/quant.json")
    side, sig, warn = res["side"], model.get("signals", {}), {"extended", "downtrend"}
    t_ok = {k for k, v in sig.items() if v.get("tested" if side == "up" else "tested_weak") and k not in warn}
    t_warn = {k for k, v in sig.items() if k in warn and v.get("tested" if side == "up" else "tested_weak")}
    v_ok = {k for k, v in (vm.get("rules") or {}).items() if v.get(f"tested_{side}")}
    fq = ((vm.get("fundamental") or {}).get("quintiles")) or {}
    for s, x in res["stocks"].items():
        on = set((tech.get(s) or {}).get("new", []))
        vin = set(((vm.get("today") or {}).get(s) or {}).get("on", []))
        score, ev = 0.0, []
        for k in sorted(on & t_ok):
            score, ev = score + 2, ev + [["tech", k]]
        for k in sorted(on & t_warn):
            score, ev = score - 2, ev + [["warn", k]]
        for n_, k in enumerate(sorted(vin & v_ok)):
            score, ev = score + (2 if n_ == 0 else 1 if n_ < 3 else 0), ev + [["inv", k]]
        for k, q in (fq.get(s) or {}).items():
            if q >= 4:
                score, ev = score + 1, ev + [["fund", k]]
        mc = (quant.get("mc") or {}).get(s)
        if mc and mc.get("p_up") is not None and mc["p_up"] >= 0.55:
            score, ev = score + 0.5, ev + [["mc", round(mc["p_up"], 2)]]
        x.update({"setups": sorted(on - warn), "warn": sorted(on & warn), "inv": sorted(vin), "score": round(score, 1), "ev": ev})
    res["tested"] = {"tech": sorted(t_ok), "warn": sorted(t_warn), "inv": sorted(v_ok)}
    (root / "docs/research.json").write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
    return f"rescored {len(res['stocks'])}"


if __name__ == "__main__":
    import sys
    print(rescore(Path(__file__).resolve().parents[2]) if sys.argv[1:2] == ["rescore"] else "usage: research.py rescore")
