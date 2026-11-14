"""Does a stock suit the owner's portfolio?

Holdings come from Dhan (/holdings for India, /globalstocks/holdings for US). The checks follow the owner's
portfolio-management notes (Drive: PM LM1-LM3, Damodaran) — see docs/portfolio-model.md for sources:
  * diversification: correlation of the stock with the existing portfolio, and the change in portfolio
    volatility when it is added at a starting weight (two-asset formula)
  * beta (characteristic line vs the Nifty) and the portfolio beta before and after
  * Jensen's alpha and the information ratio (alpha / residual risk)
  * number of holdings (~30 for most of the diversification benefit)
  * sector and single-stock concentration
  * mean-variance utility U = E(R) - 0.5 A sigma^2 with E(R) from CAPM
  * tail risk: 1-day 95% historical VaR before and after
Numbers the notes do not give (caps, bands, starting weight, risk aversion) are marked ASSUMED and can be
changed in config/portfolio.json.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

DEFAULTS = {"start_weight": 0.05, "stock_cap": 0.10, "sector_cap": 0.25, "corr_good": 0.5, "corr_poor": 0.75,
            "beta_band": [0.9, 1.1], "risk_aversion": 3.0, "min_traded_cr": 1.0, "var_worse": 0.20, "target_count": 30}
SOURCE = {"start_weight": "ASSUMED", "stock_cap": "ASSUMED", "sector_cap": "ASSUMED", "corr_good": "ASSUMED band",
          "beta_band": "ASSUMED (moderate risk profile)", "risk_aversion": "ASSUMED (A=3)", "min_traded_cr": "ASSUMED",
          "var_worse": "ASSUMED", "target_count": "notes (~30 stocks)"}


def config(root: Path) -> dict:
    try:
        c = json.loads((root / "config/portfolio.json").read_text(encoding="utf-8"))
    except Exception:
        c = {}
    return {**DEFAULTS, **{k: v for k, v in c.items() if k in DEFAULTS}}, c.get("extra", [])


# ---------------------------------------------------------------- holdings from Dhan
def _num(x, *keys):
    for k in keys:
        if x.get(k) not in (None, ""):
            try:
                return float(x[k])
            except (TypeError, ValueError):
                pass
    return 0.0


def normalise(india, us) -> list:
    out = []
    for x in india or []:
        qty = _num(x, "totalQty", "availableQty", "dpQty", "quantity")
        if qty <= 0:
            continue
        out.append({"sym": str(x.get("tradingSymbol") or x.get("symbol") or "").upper().replace("-EQ", ""),
                    "sid": str(x.get("securityId") or ""), "mkt": "NSE", "qty": qty,
                    "avg": _num(x, "avgCostPrice", "averagePrice", "avgPrice"), "isin": x.get("isin")})
    for x in us or []:
        qty = _num(x, "quantity", "totalQty", "netQty", "qty", "availableQty")
        if qty <= 0:
            continue
        out.append({"sym": str(x.get("tradingSymbol") or x.get("symbol") or x.get("displayName") or "").upper(),
                    "sid": str(x.get("securityId") or ""), "mkt": "US", "qty": qty,
                    "avg": _num(x, "avgCostPrice", "averagePrice", "avgPrice", "avgCost")})
    return out


def _list(resp):
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict):
        for k in ("data", "holdings", "result"):
            if isinstance(resp.get(k), list):
                return resp[k]
    return []


def fetch(client) -> dict:
    """Both holdings calls; an empty book comes back from Dhan as an error, which is recorded, not raised."""
    notes, india, us = [], [], []
    for path, put in (("/holdings", "india"), ("/globalstocks/holdings", "us")):
        try:
            r = _list(client.get(path))
            (india if put == "india" else us).extend(r)
            print(f"  holdings {path}: {len(r)} rows; fields {sorted(r[0])[:14] if r else []}")
        except Exception as e:
            msg = str(e)[:160]
            notes.append(f"{path}: {msg}")
            print(f"  holdings {path}: {msg}")
    return {"holdings": normalise(india, us), "notes": notes}


# ---------------------------------------------------------------- maths
def _rets(c):
    return [c[k] / c[k - 1] - 1 for k in range(1, len(c)) if c[k - 1]]


def _mean(x):
    return sum(x) / len(x) if x else 0.0


def _cov(a, b):
    n = min(len(a), len(b))
    a, b = a[-n:], b[-n:]
    ma, mb = _mean(a), _mean(b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (n - 1) if n > 1 else 0.0


def _var95(r):
    if len(r) < 50:
        return None
    s = sorted(r)
    return -s[int(0.05 * len(s))]


def aligned_returns(series: dict, dates: list) -> dict:
    """series {sym: {d, c}} -> daily returns on the common date list (missing days carried forward)."""
    out = {}
    for s, o in series.items():
        m = dict(zip(o["d"], o["c"]))
        c, last = [], None
        for d in dates:
            last = m.get(d, last)
            c.append(last)
        if sum(x is not None for x in c) < len(dates) * 0.8:
            continue
        first = next(k for k, x in enumerate(c) if x is not None)
        c = [c[first]] * first + c[first:]
        out[s] = _rets(c)
    return out


def weekly(r, step=5):
    return [math.prod(1 + x for x in r[k:k + step]) - 1 for k in range(len(r) % step, len(r), step)]


def beta_alpha(r, m, rf_d):
    """Characteristic line on weekly excess returns: beta, Jensen's alpha (yearly), residual sd (yearly), R^2."""
    rw, mw = weekly(r), weekly(m)
    n = min(len(rw), len(mw))
    if n < 30:
        return None
    rw, mw = [x - rf_d * 5 for x in rw[-n:]], [x - rf_d * 5 for x in mw[-n:]]
    vm = _cov(mw, mw)
    b = _cov(rw, mw) / vm if vm else 1.0
    a = _mean(rw) - b * _mean(mw)
    res = [x - a - b * y for x, y in zip(rw, mw)]
    sr = math.sqrt(_cov(res, res)) if n > 2 else 0
    vr = _cov(rw, rw)
    return {"beta": b, "alpha": a * 52, "resid": sr * math.sqrt(52), "r2": (b * b * vm / vr) if vr else 0}


def portfolio_series(rets: dict, weights: dict) -> list:
    syms = [s for s in weights if s in rets]
    tot = sum(weights[s] for s in syms)
    if not syms or tot <= 0:
        return []
    n = min(len(rets[s]) for s in syms)
    return [sum(weights[s] / tot * rets[s][-n + k] for s in syms) for k in range(n)]


def fit(sym: str, r: list, p: list, m: list, held: dict, sectors: dict, cfg: dict, rf: float, erp: float,
        traded_cr: float | None, p_beta: float | None) -> dict:
    """One candidate against the current portfolio. r, p, m: daily returns (stock, portfolio, Nifty)."""
    checks = []

    def add(key, ok, val, need, src, soft=True):
        checks.append({"k": key, "ok": ok, "v": val, "need": need, "src": src, "soft": soft})

    if len(r) < 250:
        return {"v": "no", "why": ["less than a year of Dhan history"], "checks": []}
    n = min(len(r), len(p), 756)
    r3, p3, m3 = r[-n:], p[-n:], m[-n:]
    r1, p1 = r[-252:], p[-252:]
    sc, sp = math.sqrt(_cov(r1, r1) * 252), math.sqrt(_cov(p1, p1) * 252)
    rho = _cov(r1, p1) / math.sqrt(_cov(r1, r1) * _cov(p1, p1)) if sc and sp else 0
    cur = held.get(sym, 0.0)
    room = max(0.0, cfg["stock_cap"] - cur)
    w = min(cfg["start_weight"], room)
    if traded_cr is not None:
        add("liquidity", traded_cr >= cfg["min_traded_cr"], f"₹{traded_cr:.1f} Cr a day", f"≥ ₹{cfg['min_traded_cr']:.0f} Cr",
            SOURCE["min_traded_cr"], soft=False)
    add("correlation", rho <= cfg["corr_poor"], round(rho, 2), f"≤ {cfg['corr_good']} good, > {cfg['corr_poor']} poor",
        "notes: ρ < 1 diversifies; bands " + SOURCE["corr_good"])
    s_new = math.sqrt(max(0.0, (w * sc) ** 2 + ((1 - w) * sp) ** 2 + 2 * w * (1 - w) * rho * sc * sp)) if w else sp
    add("volatility", s_new <= sp + 1e-9, f"{sp * 100:.1f}% → {s_new * 100:.1f}%", "not higher", "notes: two-asset σ formula")
    ba = beta_alpha(r3, m3, rf / 252)
    if ba:
        b_new = (1 - w) * (p_beta if p_beta is not None else 1.0) + w * ba["beta"]
        lo, hi = cfg["beta_band"]
        add("beta", lo - 0.05 <= b_new <= hi + 0.05 or (p_beta is not None and abs(b_new - lo - (hi - lo) / 2) <= abs(p_beta - lo - (hi - lo) / 2)),
            f"stock {ba['beta']:.2f}; portfolio {p_beta if p_beta is not None else 1:.2f} → {b_new:.2f}", f"{lo}–{hi}",
            "notes: portfolio β = Σwβ; band " + SOURCE["beta_band"])
        ir = ba["alpha"] / ba["resid"] if ba["resid"] else 0
        add("alpha", ir > 0, f"α {ba['alpha'] * 100:+.1f}%/yr, IR {ir:.2f}", "IR > 0", "notes: Jensen α, information ratio")
        er_c, er_p = rf + ba["beta"] * erp, rf + (p_beta or 1.0) * erp
        u_old = er_p - 0.5 * cfg["risk_aversion"] * sp ** 2
        u_new = (1 - w) * er_p + w * er_c - 0.5 * cfg["risk_aversion"] * s_new ** 2
        add("utility", u_new >= u_old - 1e-6, f"{u_old * 100:.2f} → {u_new * 100:.2f}", "not lower",
            "notes: U = E(R) − ½Aσ², E(R) from CAPM; " + SOURCE["risk_aversion"])
    v_old = _var95(p1)
    v_new = _var95([(1 - w) * a + w * b for a, b in zip(p1, r1)])
    if v_old and v_new:
        add("tail risk", v_new <= v_old * (1 + cfg["var_worse"]), f"{v_old * 100:.2f}% → {v_new * 100:.2f}% a day", "≤ +20%",
            "notes: VaR beyond mean-variance; " + SOURCE["var_worse"])
    sec = sectors.get(sym)
    if sec:
        sw = sum(x for s, x in held.items() if sectors.get(s) == sec) * (1 - w) + w
        add("sector", sw <= cfg["sector_cap"], f"{sec}: {sw * 100:.0f}% after", f"≤ {cfg['sector_cap'] * 100:.0f}%", SOURCE["sector_cap"], soft=False)
    add("single stock", cur + w <= cfg["stock_cap"] + 1e-9, f"{(cur + w) * 100:.0f}% after" if w else f"already {cur * 100:.0f}%",
        f"≤ {cfg['stock_cap'] * 100:.0f}%", SOURCE["stock_cap"], soft=False)
    hard = [c for c in checks if not c["ok"] and not c["soft"]]
    soft = [c for c in checks if not c["ok"] and c["soft"]]
    corr_bad = rho > cfg["corr_poor"] and s_new > sp
    verdict = "no" if hard or corr_bad or len(soft) >= 3 else "partly" if soft or rho > cfg["corr_good"] else "suits"
    why = [f"{c['k']}: {c['v']} (needs {c['need']})" for c in hard + soft]
    if verdict == "suits":
        why = [f"lowers or holds risk (ρ {rho:.2f} with your portfolio)", f"start at {w * 100:.0f}%"]
    return {"v": verdict, "w": round(w, 3), "rho": round(rho, 3), "sig": [round(sp, 4), round(s_new, 4)],
            "beta": round(ba["beta"], 2) if ba else None, "why": why, "checks": checks}


def run(client, data: dict, nifty: dict, root: Path, nset: dict, us_px: dict | None = None) -> str:
    """Nightly: fetch holdings, value them, and score every Nifty 500 stock (and held US stocks) for fit."""
    cfg, extra = config(root)
    book = fetch(client) if client is not None else {"holdings": [], "notes": ["no Dhan client"]}
    hold = book["holdings"] + [dict(h, manual=True) for h in extra]
    stocks = nset.get("stocks", {})
    sectors = {s: x.get("sector") for s, x in stocks.items()}
    board = {}
    try:
        for row in json.loads((root / "docs/n500.json").read_text(encoding="utf-8")).get("rows", []):
            board[row["s"]] = row
            sectors.setdefault(row["s"], row.get("sector") or row.get("ind"))
    except Exception:
        pass
    usdinr = ((nset.get("fx") or {}).get("inr_now")) or None
    # value each holding in rupees
    for h in hold:
        px = None
        if h["mkt"] == "NSE":
            o = data.get(h["sym"])
            px = o["c"][-1] if o and o.get("c") else (board.get(h["sym"]) or {}).get("last")
            if px is None and client is not None and h.get("sid"):
                try:
                    import datetime as _dt
                    end = _dt.date.fromisoformat(nifty["d"][-1])
                    resp = client.daily(h["sid"], "NSE_EQ", "EQUITY", end - _dt.timedelta(days=1100), end)
                    import tech_model as TM
                    data[h["sym"]] = {"d": [_dt.datetime.fromtimestamp(t, TM.dt.timezone(TM.dt.timedelta(hours=5, minutes=30))).date().isoformat() for t in resp["timestamp"]], "c": list(resp["close"])}
                    px = data[h["sym"]]["c"][-1]
                except Exception as e:
                    print(f"  no history for holding {h['sym']}: {str(e)[:80]}")
        else:
            px = (us_px or {}).get(h["sym"]) or h.get("avg")
        h["px"] = px
        h["value"] = (px or 0) * h["qty"] * (usdinr if h["mkt"] == "US" and usdinr else 1)
    total = sum(h["value"] for h in hold) or 0.0
    held = {}
    for h in hold:
        if total:
            held[h["sym"]] = held.get(h["sym"], 0) + h["value"] / total
    dates = nifty["d"][-757:]
    m = aligned_returns({"NIFTY": nifty}, dates)["NIFTY"]
    nse_w = {h["sym"]: held[h["sym"]] for h in hold if h["mkt"] == "NSE" and h["sym"] in data}
    rets = aligned_returns({s: o for s, o in data.items() if o.get("c")}, dates)
    proxy = not nse_w
    p = portfolio_series(rets, nse_w) if nse_w else m
    rf = float(nset.get("gsec") or 7.0) / 100
    erp = float(((nset.get("fund") or {}).get("erp")) or 0.05)
    pb = None
    if nse_w and len(p) > 150:
        ba = beta_alpha(p, m, rf / 252)
        pb = ba["beta"] if ba else None
    elif proxy:
        pb = 1.0
    out, check_src = {}, {}
    for s, r in rets.items():
        o = data.get(s) or {}
        tcr = None
        if o.get("v") and o.get("c"):
            tv = [a * b for a, b in zip(o["c"][-60:], o["v"][-60:]) if a and b]
            tcr = _mean(tv) / 1e7 if tv else None
        f = fit(s, r, p, m, held if not proxy else {}, sectors, cfg, rf, erp, tcr, pb)
        out[s] = {k: f[k] for k in ("v", "w", "rho", "sig", "beta", "why") if k in f}
        out[s]["c"] = [[x["k"], 1 if x["ok"] else 0, x["v"], x["need"]] for x in f.get("checks", [])]
        for x in f.get("checks", []):
            check_src[x["k"]] = x["src"]
    secw = {}
    for h in hold:
        k = "US stocks" if h["mkt"] == "US" else (sectors.get(h["sym"]) or "Other")
        secw[k] = secw.get(k, 0) + (h["value"] / total if total else 0)
    summary = {"count": len(held), "value_inr": round(total), "beta": round(pb, 2) if pb is not None else None,
               "vol": round(math.sqrt(_cov(p[-252:], p[-252:]) * 252), 4) if len(p) > 252 else None,
               "var95_1d": round(_var95(p[-252:]) or 0, 4) if p else None, "sectors": dict(sorted(secw.items(), key=lambda x: -x[1])),
               "us_share": round(sum(h["value"] for h in hold if h["mkt"] == "US") / total, 3) if total else 0,
               "proxy": proxy, "usdinr": usdinr}
    res = {"asof": nifty["d"][-1], "config": cfg, "sources": SOURCE, "notes": book["notes"],
           "holdings": [{k: h.get(k) for k in ("sym", "mkt", "qty", "avg", "px", "value", "manual")} for h in hold],
           "weights": {k: round(v, 4) for k, v in held.items()}, "summary": summary, "fit": out, "check_src": check_src,
           "basis": ("Fit measured against your Dhan holdings." if not proxy else
                     "No holdings found in Dhan, so fit is measured against the Nifty 50 as a stand-in portfolio.")}
    (root / "docs/portfolio.json").write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
    cnt = {k: sum(1 for x in out.values() if x["v"] == k) for k in ("suits", "partly", "no")}
    return f"portfolio fit: {len(hold)} holdings ({'proxy: Nifty' if proxy else 'from Dhan'}); {cnt}"
