"""Every NSE-listed equity, so the desk can analyse any stock Dhan has.

Nightly (after the main refresh, same Dhan login queue):
  * the universe from Dhan's instrument list: NSE equities in the EQ and BE series, with names for search
  * 2 years of Dhan daily bars per stock: technical readout and signals (same code as the back-tested model),
    a 1-year chart, and the stock's own swings of 10%+ with likely reasons
  * Dhan company information (valuation, quality, ownership) for stocks outside the Nifty 500, once a week
Writes docs/all-stocks.json (search index + per-stock profiles); the desk splits the profiles into small files.

Swing reasons are evidence, not proof: the Nifty's move over the same days (market), the industry's median move
(sector, where Dhan gives the industry), quarterly results filed inside the swing (NSE XBRL, Nifty 500), and the
stock's own move beyond both.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import statistics as stt
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERIES = ("EQ", "BE")
SWING = 0.10


def universe(scrip_csv: str) -> list:
    out, seen = [], set()
    for r in csv.DictReader(io.StringIO(scrip_csv)):
        if r.get("SEM_EXM_EXCH_ID") != "NSE" or r.get("SEM_INSTRUMENT_NAME") != "EQUITY" or r.get("SEM_SEGMENT") != "E":
            continue
        if r.get("SEM_SERIES") not in SERIES:
            continue
        s = r.get("SEM_TRADING_SYMBOL", "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        name = (r.get("SM_SYMBOL_NAME") or r.get("SEM_CUSTOM_SYMBOL") or s).strip()
        out.append({"s": s, "sid": r["SEM_SMST_SECURITY_ID"], "name": name, "series": r.get("SEM_SERIES")})
    return out


def zigzag(d: list, c: list, th: float = SWING) -> list:
    """Swings of th or more on closes: [[start_date, end_date, start_px, end_px, move]], oldest first.
    The last item is the move in progress since the latest turning point (it may be under th)."""
    if len(c) < 3:
        return []
    piv, trend, ext = [0], 0, 0
    for i in range(1, len(c)):
        if trend == 0:
            if c[i] >= c[piv[0]] * (1 + th):
                trend, ext = 1, i
            elif c[i] <= c[piv[0]] * (1 - th):
                trend, ext = -1, i
            elif (c[i] < c[piv[0]] and c[i] < c[0]) or (c[i] > c[piv[0]] and c[i] > c[0]):
                pass
        elif trend == 1:
            if c[i] > c[ext]:
                ext = i
            elif c[i] <= c[ext] * (1 - th):
                piv.append(ext)
                trend, ext = -1, i
        else:
            if c[i] < c[ext]:
                ext = i
            elif c[i] >= c[ext] * (1 + th):
                piv.append(ext)
                trend, ext = 1, i
    if trend != 0 and ext != piv[-1]:
        piv.append(ext)
    if piv[-1] != len(c) - 1:
        piv.append(len(c) - 1)
    out = []
    for a, b in zip(piv, piv[1:]):
        if b > a and c[a]:
            out.append([d[a], d[b], round(c[a], 2), round(c[b], 2), round(c[b] / c[a] - 1, 4)])
    return out


def explain(sw: list, nmap: dict, peers_ret=None, filings: list | None = None) -> dict:
    """Market / sector / own split of one swing, plus results or filings dated inside it."""
    a, b, _, _, mv = sw
    na, nb = nmap.get(a), nmap.get(b)
    mkt = (nb / na - 1) if na and nb else None
    sec = peers_ret(a, b) if peers_ret else None
    own = mv - (mkt or 0)                                  # the move beyond the Nifty; the industry is reported separately
    parts = {"mkt": round(mkt, 4) if mkt is not None else None, "sec": round(sec, 4) if sec is not None else None, "own": round(own, 4)}
    why = []
    if mkt is not None and abs(mkt) >= 0.6 * abs(mv) and (mkt > 0) == (mv > 0):
        why.append(f"mostly the market (Nifty {mkt * 100:+.0f}%)")
    elif sec is not None and abs(sec) >= 0.6 * abs(mv) and (sec > 0) == (mv > 0):
        why.append(f"its industry moved too ({sec * 100:+.0f}%)")
    else:
        why.append("mostly company-specific")
    if sec is not None and not why[0].startswith("its industry"):
        why.append(f"industry {sec * 100:+.0f}% over the same days")
    for f in filings or []:
        if a <= f["d"] <= b:
            why.append(f["t"])
    return {**parts, "why": why[:4]}


def results_events(cache_entry: dict | None) -> list:
    """Quarterly results filed (NSE XBRL cache): [{d, t}] with profit growth when available."""
    out = []
    q = sorted((cache_entry or {}).values(), key=lambda x: x.get("end", ""))
    for i, x in enumerate(q):
        filed = x.get("filed")
        d = None
        for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                d = dt.datetime.strptime(str(filed)[:20].strip(), fmt).date().isoformat()
                break
            except ValueError:
                continue
        if not d:
            continue
        ya = next((y for y in q[:i] if abs((dt.date.fromisoformat(x["end"]) - dt.date.fromisoformat(y["end"])).days - 365) <= 20), None)
        g = (x["pat"] / ya["pat"] - 1) if x.get("pat") is not None and ya and ya.get("pat") and ya["pat"] > 0 else None
        out.append({"d": d, "t": f"results for {x['end'][:7]}" + (f": profit {g * 100:+.0f}% on a year ago" if g is not None else "")})
    return out


def run(dhan, scrip_csv: str, root: Path = ROOT, limit: int | None = None) -> str:
    import research as RS
    import tech_model as TM
    uni = universe(scrip_csv)
    if limit:
        uni = uni[:limit]
    n500 = {r["s"] for r in json.loads((root / "docs/n500.json").read_text(encoding="utf-8")).get("rows", [])}
    end = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).date()
    start = end - dt.timedelta(days=760)

    def series(resp):
        ts = resp.get("timestamp") or []
        return {"d": [dt.datetime.fromtimestamp(t, dt.timezone(dt.timedelta(hours=5, minutes=30))).date().isoformat() for t in ts],
                "o": list(resp["open"]), "h": list(resp["high"]), "l": list(resp["low"]), "c": list(resp["close"]),
                "v": list(resp.get("volume") or [])}
    import refresh as R
    _, ix = R.build_maps(scrip_csv, [], ["Nifty 50"])
    nifty = series(dhan.daily(ix["Nifty 50"], "IDX_I", "INDEX", start, end))
    nmap = dict(zip(nifty["d"], nifty["c"]))
    try:
        fund_all = json.loads((root / "docs/fund-all.json").read_text(encoding="utf-8"))
    except Exception:
        fund_all = {"now": {}, "asof": None}
    f500 = {}
    try:
        f500 = json.loads((root / "docs/fund500.json").read_text(encoding="utf-8")).get("now", {})
    except Exception:
        pass
    weekly_fund = end.weekday() == 4 or not fund_all.get("asof")           # Fridays, or the first run
    try:
        rcache = json.loads((root / "data/results-cache.json").read_text(encoding="utf-8"))
    except Exception:
        rcache = {}
    data, failed = {}, 0
    t0 = time.time()
    for u in uni:
        try:
            data[u["s"]] = series(dhan.daily(u["sid"], "NSE_EQ", "EQUITY", start, end))
        except Exception:
            failed += 1
        if weekly_fund and u["s"] not in n500:
            try:
                fund_all["now"][u["s"]] = RS.compact_fund(dhan.company(u["sid"]))
            except Exception:
                pass
        if time.time() - t0 > 50 * 60:
            print("  time limit: stopping early")
            break
    if weekly_fund:
        fund_all["asof"] = end.isoformat()
        (root / "docs/fund-all.json").write_text(json.dumps(fund_all, separators=(",", ":")), encoding="utf-8")
    # industry peers for the sector part of a swing
    ind = {s: ((f500.get(s) or fund_all["now"].get(s) or {}).get("industry")) for s in data}
    cmap = {s: dict(zip(o["d"], o["c"])) for s, o in data.items()}
    by_ind = {}
    for s, i in ind.items():
        if i:
            by_ind.setdefault(i, []).append(s)

    def peers_fn(sym):
        peers = [p for p in by_ind.get(ind.get(sym), []) if p != sym]
        if len(peers) < 3:
            return None

        def f(a, b):
            rs = [cmap[p][b] / cmap[p][a] - 1 for p in peers if cmap[p].get(a) and cmap[p].get(b)]
            return stt.median(rs) if len(rs) >= 3 else None
        return f
    prof = {}
    for s, o in data.items():
        keep = [k for k, d in enumerate(o["d"]) if d in nmap and o["c"][k]]
        if len(keep) < 60:
            continue
        d = [o["d"][k] for k in keep]
        cols = {k: [o[k][j] for j in keep] for k in ("o", "h", "l", "c")}
        v = [o["v"][j] for j in keep] if len(o["v"]) == len(o["d"]) else None
        c = cols["c"]
        p = {"last": round(c[-1], 2), "d": d[-1]}
        if len(c) >= 260:
            T = TM.Tech(cols["o"], cols["h"], cols["l"], c, v, [nmap[x] for x in d])
            i = len(c) - 1
            now = T.flags(i)
            recent = set().union(*(T.flags(k) - T.flags(k - 1) for k in range(i - 2, i + 1)))
            p.update({"on": sorted(now), "new": sorted(recent & now), "atr": round(T.atr[i], 2) if T.atr[i] else None, **TM.readout(T, i)})
        rets = lambda n: round(c[-1] / c[-1 - n] - 1, 4) if len(c) > n and c[-1 - n] else None
        p.update({"r1m": rets(21), "r3m": rets(63), "r1y": rets(250)})
        p["ch"] = {"b": round(c[-250:][0], 2), "k": 10 if c[-1] < 500 else 1,
                   "x": [round((x - c[-250:][0]) * (10 if c[-1] < 500 else 1)) for x in c[-250:]]}
        if v:
            p["ch"]["v"] = [int(x) for x in v[-250:][::5]]
        sw = zigzag(d, c)[-6:]
        events = results_events(rcache.get(s))
        pf = peers_fn(s)
        p["swings"] = [sw_ + [explain(sw_, nmap, pf, events)] for sw_ in sw]
        if s not in n500:
            f = fund_all["now"].get(s)
            if f:
                p["fund"] = {k: f.get(k) for k in ("pe", "pe_sec", "pb", "roce", "de", "dy", "prom", "fii", "d_fii", "dii", "d_dii", "industry", "sector")}
        prof[s] = p
    names = {u["s"]: u["name"] for u in uni}
    out = {"asof": end.isoformat(), "count": len(uni), "index": [[u["s"], u["name"], 1 if u["s"] in n500 else 0] for u in uni],
           "s": prof, "fund_asof": fund_all.get("asof"),
           "note": "Every NSE equity (EQ and BE series) from Dhan's instrument list; 2 years of Dhan daily bars. "
                   "Signals use the same code as the back-tested model; only signals that passed count."}
    (root / "docs/all-stocks.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    return f"all stocks: {len(uni)} in the universe, {len(prof)} profiled, {failed} failed; names for search {len(names)}"


def main() -> int:
    import refresh as R
    import requests
    cid, pin, sec = (os.environ[k] for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"))
    dhan = R.Dhan(cid, R.login(cid, pin, sec))
    scrip = requests.get(R.SCRIP_MASTER, timeout=90).text
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    print(run(dhan, scrip, limit=lim))
    return 0


if __name__ == "__main__":
    sys.exit(main())
