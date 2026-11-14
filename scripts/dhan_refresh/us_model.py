"""US stocks for the desk.

Prices: Dhan's US feed (us-watch branch: live quotes and the daily closes it records).
History: Dhan has no US history API, so if the FMP_API_KEY secret is set, 3 years of daily closes come from
Financial Modeling Prep; otherwise the desk uses only the closes Dhan's feed has recorded so far.
Options: neither Dhan nor a free source has US option chains (Alpha Vantage's are premium), so none are shown.
Fundamentals: docs/us-value.json (FMP).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import subprocess
from pathlib import Path

FMP = "https://financialmodelingprep.com/stable/historical-price-eod/light"
FOREIGN_CAP = 0.25          # ASSUMED cap on foreign equity (owner's notes give no number; FX risk applies)


def _show(root: Path, branch: str, path: str):
    try:
        subprocess.run(["git", "-C", str(root), "fetch", "-q", "origin", branch], check=True, capture_output=True, timeout=60)
        return json.loads(subprocess.run(["git", "-C", str(root), "show", f"FETCH_HEAD:{path}"], check=True,
                                         capture_output=True, text=True).stdout)
    except Exception:
        return None


def fmp_history(sym: str, key: str, years: int = 3) -> dict:
    import requests
    start = (dt.date.today() - dt.timedelta(days=365 * years + 10)).isoformat()
    r = requests.get(FMP, params={"symbol": sym, "from": start, "apikey": key}, timeout=30)
    r.raise_for_status()
    rows = sorted((x["date"], float(x["price"])) for x in r.json() if x.get("price"))
    return {"d": [d for d, _ in rows], "c": [c for _, c in rows], "src": "FMP"}


def merge(hist: dict | None, dhan_days: dict | None) -> dict:
    """FMP history (if any) plus Dhan's recorded closes; Dhan wins on the days both have."""
    m = dict(zip((hist or {}).get("d", []), (hist or {}).get("c", [])))
    for d, v in (dhan_days or {}).items():
        m[d] = v[2]
    ds = sorted(m)
    return {"d": ds, "c": [m[d] for d in ds]}


def _rsi(c, n=14):
    if len(c) <= n:
        return None
    g = l = 0.0
    for k in range(1, n + 1):
        ch = c[k] - c[k - 1]
        g, l = g + max(ch, 0), l + max(-ch, 0)
    g, l = g / n, l / n
    for k in range(n + 1, len(c)):
        ch = c[k] - c[k - 1]
        g, l = (g * (n - 1) + max(ch, 0)) / n, (l * (n - 1) + max(-ch, 0)) / n
    return 100.0 if l == 0 else 100 - 100 / (1 + g / l)


def readout(c: list, bench: list | None) -> dict:
    out = {"n": len(c)}
    if len(c) >= 50:
        out["vs50"] = round((c[-1] / (sum(c[-50:]) / 50) - 1) * 100, 1)
    if len(c) >= 200:
        out["vs200"] = round((c[-1] / (sum(c[-200:]) / 200) - 1) * 100, 1)
    if len(c) >= 15:
        out["rsi"] = round(_rsi(c[-200:]), 1)
    if len(c) >= 252:
        out["hi52"] = round((c[-1] / max(c[-252:]) - 1) * 100, 1)
    if bench and len(c) >= 64 and len(bench) >= 64:
        out["rs3"] = round(((c[-1] / c[-64]) - (bench[-1] / bench[-64])) * 100, 1)
    return out


def run(root: Path) -> str:
    rows = (json.loads((root / "docs/us-value.json").read_text(encoding="utf-8")) if (root / "docs/us-value.json").exists() else {}).get("rows", [])
    st = _show(root, "us-watch", "state.json") or {}
    q, dh = st.get("quotes") or {}, st.get("hist") or {}
    syms = list(dict.fromkeys([r["s"] for r in rows if r.get("s")] + list(q)))
    key = os.environ.get("FMP_API_KEY", "").strip()
    cache_p = root / "data/us-history.json"
    try:
        cache = json.loads(cache_p.read_text(encoding="utf-8"))
    except Exception:
        cache = {}
    notes = []
    if key:
        for s in syms + ["SPY"]:
            try:
                cache[s] = fmp_history(s, key)
            except Exception as e:
                notes.append(f"FMP {s}: {str(e)[:80]}")
        cache_p.write_text(json.dumps(cache, separators=(",", ":")), encoding="utf-8")
    else:
        notes.append("No FMP_API_KEY secret: US history is only what Dhan's feed has recorded.")
    try:
        import quant
    except Exception:
        quant = None
    bench = merge(cache.get("SPY"), dh.get("SPY"))["c"]
    try:
        pf = json.loads((root / "docs/portfolio.json").read_text(encoding="utf-8"))
    except Exception:
        pf = {}
    us_share = (pf.get("summary") or {}).get("us_share") or 0
    out = {}
    for s in syms:
        h = merge(cache.get(s), dh.get(s))
        c = h["c"]
        x = {"days": len(c), "from": h["d"][0] if h["d"] else None, "src": ("FMP + Dhan" if s in cache else "Dhan") if c else None,
             "tech": readout(c, bench)}
        if quant and len(c) >= 300:
            try:
                x["mc"] = quant.monte_carlo(c, None, fan=True)
                x["var"] = quant.var_report(quant.logret(c))
            except Exception as e:
                notes.append(f"{s} risk: {str(e)[:60]}")
        held = s in (pf.get("weights") or {})
        x["fit"] = {"held": held, "us_share": us_share, "cap": FOREIGN_CAP,
                    "v": "no" if us_share >= FOREIGN_CAP and not held else "partly" if us_share >= FOREIGN_CAP * 0.8 else "suits",
                    "why": [f"US stocks are {us_share * 100:.0f}% of your portfolio (cap {FOREIGN_CAP * 100:.0f}%, ASSUMED); "
                            "returns also move with USD/INR"]}
        out[s] = x
    res = {"asof": dt.date.today().isoformat(), "stocks": out, "notes": notes,
           "sources": "Prices: Dhan US feed. History: FMP (if keyed) + Dhan's recorded closes. No US options source."}
    (root / "docs/us-desk.json").write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
    return f"us model: {len(out)} stocks, {sum(1 for v in out.values() if v.get('mc'))} with risk models; {'; '.join(notes)[:200]}"


if __name__ == "__main__":
    print(run(Path(__file__).resolve().parents[2]))
