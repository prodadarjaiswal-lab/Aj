"""Quarterly results for every Nifty 500 stock, from NSE's XBRL results filings (the method of the owner's
nse-day-trader skill): revenue, EBITDA and margin, profit, EPS, with growth against the same quarter a year
earlier (YoY) and the previous quarter (QoQ), and the change in margin.

Results change once a quarter, so the job is incremental: it checks each stock's filing list and downloads an
XBRL file only when it has not been read before (cache in data/results-cache.json). The first run reads about
three filings per stock; later runs mostly just check the lists.
Writes docs/results.json. Context only: there is not enough filing history to back-test results-based rules.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import nse_feeds as NF

ROOT = Path(__file__).resolve().parents[2]
PAUSE = 0.35


def xval(text: str, tag: str):
    m = re.search(r"<[\w-]+:%s\s+contextRef=\"OneD\"[^>]*>([^<]+)<" % tag, text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def parse_xbrl(text: str) -> dict:
    """Quarter figures (context OneD). Banks use different tags from companies. Amounts as filed (usually lakh)."""
    if xval(text, "InterestEarned") is not None:
        ie, ix = xval(text, "InterestEarned"), xval(text, "InterestExpended") or 0
        return {"bank": True, "rev": ie, "nii": ie - ix, "ebitda": xval(text, "OperatingProfitBeforeProvisionAndContingencies"),
                "pat": xval(text, "ProfitLossForThePeriod"), "eps": xval(text, "BasicEarningsPerShareAfterExtraordinaryItems")}
    rev, exp = xval(text, "RevenueFromOperations"), xval(text, "Expenses")
    v = {"bank": False, "rev": rev, "pat": xval(text, "ProfitLossForPeriod"),
         "eps": xval(text, "BasicEarningsLossPerShareFromContinuingOperations")}
    if rev is not None and exp is not None:
        v["ebitda"] = rev - exp + (xval(text, "FinanceCosts") or 0) + (xval(text, "DepreciationDepletionAndAmortisationExpense") or 0)
    return v


def filing_list(sym: str) -> list:
    """Quarterly XBRL filings, newest first, consolidated when the company files them."""
    rows, q = [], urllib.parse.quote(sym)
    try:
        j = NF.nse_json(f"integrated-filing-results?index=equities&symbol={q}&period=Quarterly")
        for r in (j.get("data") if isinstance(j, dict) else j) or []:
            if r.get("consolidated") in ("Consolidated", "Standalone") and r.get("xbrl"):
                rows.append({"end": dt.datetime.strptime(r["qe_Date"].title(), "%d-%b-%Y").date().isoformat(),
                             "kind": r["consolidated"], "xbrl": r["xbrl"], "filed": r.get("broadcast_Date")})
    except Exception:
        pass
    try:
        for r in NF.nse_json(f"corporates-financial-results?index=equities&symbol={q}&period=Quarterly") or []:
            if r.get("xbrl"):
                rows.append({"end": dt.datetime.strptime(r["toDate"], "%d-%b-%Y").date().isoformat(),
                             "kind": "Consolidated" if r.get("consolidated") == "Consolidated" else "Standalone",
                             "xbrl": r["xbrl"], "filed": r.get("broadCastDate")})
    except Exception:
        pass
    want = "Consolidated" if any(r["kind"] == "Consolidated" for r in rows) else "Standalone"
    seen, out = set(), []
    for r in sorted((r for r in rows if r["kind"] == want), key=lambda r: (r["end"], r["filed"] or ""), reverse=True):
        if r["end"] not in seen:
            seen.add(r["end"])
            out.append(r)
    return out


def _g(a, b):
    return round(a / b - 1, 4) if a is not None and b not in (None, 0) and b > 0 else None


def summarise(q: list) -> dict | None:
    """q: parsed quarters, newest first, each {end, rev, ebitda, pat, eps, bank}."""
    if not q or q[0].get("rev") is None:
        return None
    a = q[0]
    end = dt.date.fromisoformat(a["end"])
    ya = next((x for x in q[1:] if abs((dt.date.fromisoformat(x["end"]) - end).days + 365) <= 20), None)
    pq = next((x for x in q[1:] if 70 <= (end - dt.date.fromisoformat(x["end"])).days <= 110), None)
    m = (a["ebitda"] / a["rev"]) if a.get("ebitda") is not None and a["rev"] else None
    my = (ya["ebitda"] / ya["rev"]) if ya and ya.get("ebitda") is not None and ya.get("rev") else None
    out = {"q": a["end"], "bank": a.get("bank"), "rev": a["rev"], "pat": a.get("pat"), "eps": a.get("eps"),
           "margin": round(m, 4) if m is not None else None,
           "rev_yoy": _g(a["rev"], ya and ya.get("rev")), "pat_yoy": _g(a.get("pat"), ya and ya.get("pat")),
           "eps_yoy": _g(a.get("eps"), ya and ya.get("eps")), "rev_qoq": _g(a["rev"], pq and pq.get("rev")),
           "margin_chg": round(m - my, 4) if m is not None and my is not None else None, "filed": a.get("filed")}
    if out["pat"] is not None and ya and ya.get("pat") is not None and ya["pat"] <= 0 < out["pat"]:
        out["turnaround"] = True
    flags = []
    if (out["rev_yoy"] or 0) >= 0.10 and (out["pat_yoy"] or 0) >= 0.15 and (out["margin_chg"] or 0) >= 0:
        flags.append("improving")
    if (out["pat_yoy"] is not None and out["pat_yoy"] <= -0.15) or (out["margin_chg"] or 0) <= -0.03:
        flags.append("deteriorating")
    out["flags"] = flags
    return out


def run(root: Path = ROOT, limit: int | None = None) -> str:
    cache_p, out_p = root / "data/results-cache.json", root / "docs/results.json"
    try:
        cache = json.loads(cache_p.read_text(encoding="utf-8"))
    except Exception:
        cache = {}
    rows = json.loads((root / "docs/n500.json").read_text(encoding="utf-8")).get("rows", [])
    syms = [r["s"] for r in rows][:limit] if limit else [r["s"] for r in rows]
    got = fetched = errs = 0
    t0 = time.time()
    for s in syms:
        try:
            fl = filing_list(s)
            time.sleep(PAUSE)
        except Exception:
            errs += 1
            continue
        if not fl:
            continue
        got += 1
        have = cache.setdefault(s, {})
        for f in fl[:5]:                                  # latest, previous quarter and the year-ago quarter are in the first 5
            if f["end"] in have and have[f["end"]].get("xbrl") == f["xbrl"]:
                continue
            try:
                txt = NF._get(f["xbrl"], accept="*/*")
                have[f["end"]] = {**parse_xbrl(txt), "end": f["end"], "xbrl": f["xbrl"], "filed": f.get("filed")}
                fetched += 1
            except Exception:
                errs += 1
            time.sleep(PAUSE)
        for k in sorted(have)[:-8]:                      # keep 2 years
            del have[k]
        if time.time() - t0 > 40 * 60:                    # stay inside the job's time limit; the next run continues
            print("  time limit reached; the next run continues")
            break
    cache_p.write_text(json.dumps(cache, separators=(",", ":")), encoding="utf-8")
    res = {}
    for s, have in cache.items():
        q = sorted(have.values(), key=lambda x: x["end"], reverse=True)
        sm = summarise(q)
        if sm:
            res[s] = sm
    out = {"asof": dt.datetime.now(NF.IST).strftime("%Y-%m-%d %H:%M"), "stocks": res,
           "note": "NSE XBRL results filings, consolidated where filed. YoY = same quarter a year earlier. Context only: "
                   "too little filing history to back-test."}
    out_p.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    imp = sum("improving" in v["flags"] for v in res.values())
    det = sum("deteriorating" in v["flags"] for v in res.values())
    return f"results: lists for {got} of {len(syms)}, {fetched} filings read, {errs} errors; {len(res)} stocks, {imp} improving, {det} deteriorating"


if __name__ == "__main__":
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    print(run(limit=lim))
