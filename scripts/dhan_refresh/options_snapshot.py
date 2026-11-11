"""Nightly options snapshot: one row of option-derived features per underlying.

Saves data/options/<trading-date>.json so we can later test whether the
options gates (expected move, call-put IV spread, skew, PCR, OI walls) help
screener picks on NSE. Never touches the RA Desk page; a failure here does
not block the price refresh.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import sys
import time
from pathlib import Path

import refresh as R

INDEXES = {"NIFTY": ("13", "IDX_I"), "BANKNIFTY": ("25", "IDX_I")}
MIN_DAYS = 3  # skip an expiry this close; use the next one


def clean_leg(leg: dict | None) -> dict | None:
    """Keep usable quotes only: live price, some OI, IV between 3% and 150%."""
    if not isinstance(leg, dict):
        return None
    ltp = float(leg.get("last_price") or 0)
    iv = float(leg.get("implied_volatility") or 0)
    oi = float(leg.get("oi") or 0)
    if ltp <= 0 or oi <= 0 or not (3 <= iv <= 150):
        return {"ltp": ltp, "oi": oi, "iv": None, "vol": float(leg.get("volume") or 0),
                "poi": float(leg.get("previous_oi") or 0), "g": {}}
    return {"ltp": ltp, "oi": oi, "iv": iv, "vol": float(leg.get("volume") or 0),
            "poi": float(leg.get("previous_oi") or 0), "g": leg.get("greeks") or {}}


def parse_chain(resp: dict) -> tuple[float, list[tuple[float, dict, dict]]]:
    d = resp.get("data", resp)
    spot = float(d.get("last_price") or 0)
    rows = []
    for k, v in (d.get("oc") or {}).items():
        rows.append((float(k), clean_leg(v.get("ce")), clean_leg(v.get("pe"))))
    rows.sort(key=lambda r: r[0])
    if spot <= 0 or len(rows) < 5:
        raise R.RefreshError("chain too thin")
    return spot, rows


def max_pain(rows):
    strikes = [k for k, _, _ in rows]
    best, best_k = None, None
    for s in strikes:
        pain = sum((max(s - k, 0) * (c or {}).get("oi", 0)) + (max(k - s, 0) * (p or {}).get("oi", 0)) for k, c, p in rows)
        if best is None or pain < best:
            best, best_k = pain, s
    return best_k


def features(spot: float, rows, expiry: str, today: dt.date) -> dict:
    atm = min(rows, key=lambda r: abs(r[0] - spot))
    k, c, p = atm
    days = (dt.date.fromisoformat(expiry) - today).days
    f = {"spot": spot, "expiry": expiry, "days": days, "atm": k}
    if c and p and c["ltp"] > 0 and p["ltp"] > 0:
        f["straddle"] = c["ltp"] + p["ltp"]
        f["exp_move"] = f["straddle"] / spot
    # IVs: use OTM side on each, nearest usable strike to ATM
    calls = [(kk, cc) for kk, cc, _ in rows if cc and cc["iv"] and kk >= spot]
    puts = [(kk, pp) for kk, _, pp in rows if pp and pp["iv"] and kk <= spot]
    if calls:
        f["iv_call"] = calls[0][1]["iv"]
        f["delta_call"] = calls[0][1]["g"].get("delta")
    if puts:
        f["iv_put"] = puts[-1][1]["iv"]
    if "iv_call" in f and "iv_put" in f:
        f["cp_spread"] = f["iv_call"] - f["iv_put"]          # >0 calls rich (bullish lean)
    otm = [(kk, pp) for kk, pp in puts if kk <= spot * 0.95]
    if otm and "iv_call" in f:
        k90 = min(otm, key=lambda x: abs(x[0] - spot * 0.90))
        f["skew"] = k90[1]["iv"] - f["iv_call"]               # >0 puts rich (fear)
        f["skew_strike"] = k90[0]
    coi = sum((c or {}).get("oi", 0) for _, c, _ in rows)
    poi = sum((p or {}).get("oi", 0) for _, _, p in rows)
    cv = sum((c or {}).get("vol", 0) for _, c, _ in rows)
    pv = sum((p or {}).get("vol", 0) for _, _, p in rows)
    if coi:
        f["pcr_oi"] = poi / coi
    if cv:
        f["pcr_vol"] = pv / cv
    f["opt_vol"] = cv + pv
    f["oi_chg"] = (coi + poi) - sum((c or {}).get("poi", 0) + (p or {}).get("poi", 0) for _, c, p in rows)
    above = [(kk, cc["oi"]) for kk, cc, _ in rows if cc and kk > spot]
    below = [(kk, pp["oi"]) for kk, _, pp in rows if pp and kk < spot]
    if above:
        f["call_wall"] = max(above, key=lambda x: x[1])[0]
    if below:
        f["put_wall"] = max(below, key=lambda x: x[1])[0]
    f["max_pain"] = max_pain(rows)
    return {k2: (round(v, 6) if isinstance(v, float) and math.isfinite(v) else v) for k2, v in f.items()}


def pick_expiry(dates: list[str], today: dt.date) -> str | None:
    ok = sorted(d for d in dates if (dt.date.fromisoformat(d) - today).days >= MIN_DAYS)
    return ok[0] if ok else None


class OptionsClient:
    """Thin wrapper; spacing respects 1 chain request per 3 s and 10 underlyings per 8 s."""

    def __init__(self, dhan: R.Dhan):
        self.d = dhan

    def _post(self, path, body):
        time.sleep(3.1)
        return self.d.post(path, body)

    def expiries(self, sid, seg):
        r = self._post("/optionchain/expirylist", {"UnderlyingScrip": int(sid), "UnderlyingSeg": seg})
        return r.get("data") or []

    def chain(self, sid, seg, expiry):
        return self._post("/optionchain", {"UnderlyingScrip": int(sid), "UnderlyingSeg": seg, "Expiry": expiry})


def snapshot(client, underlyings: dict, today: dt.date) -> dict:
    out, errors = {}, {}
    for name, (sid, seg) in underlyings.items():
        try:
            exp = pick_expiry(client.expiries(sid, seg), today)
            if not exp:
                errors[name] = "no expiry"
                continue
            spot, rows = parse_chain(client.chain(sid, seg, exp))
            out[name] = features(spot, rows, exp, today)
        except Exception as e:  # one bad underlying must not stop the rest
            errors[name] = str(e)[:120]
    return {"date": today.isoformat(), "rows": out, "errors": errors}


def save_snapshot(dhan, scrip_csv: str, root: Path = Path(".")) -> str:
    """Use an already logged-in client: Dhan allows one new token per 2 minutes."""
    nset = R.read_nset((root / "docs/ra-desk.html").read_text(encoding="utf-8"))
    day = dt.datetime.now(R.IST).date().isoformat()   # the day the chain was captured
    outdir = root / "data/options"
    outdir.mkdir(parents=True, exist_ok=True)
    target = outdir / f"{day}.json"
    if target.exists():
        return f"options snapshot for {day} already saved"
    eq, _ = R.build_maps(scrip_csv, list(nset["stocks"]), [])
    unders = dict(INDEXES)
    unders.update({s: (sid, "NSE_FNO") for s, sid in eq.items()})
    snap = snapshot(OptionsClient(dhan), unders, dt.date.fromisoformat(day))
    target.write_text(json.dumps(snap, separators=(",", ":")), encoding="utf-8")
    msg = f"options snapshot {target.name}: {len(snap['rows'])} underlyings, {len(snap['errors'])} skipped"
    if snap["errors"]:
        msg += "\n  skipped: " + ", ".join(f"{k} ({v})" for k, v in list(snap["errors"].items())[:12])
    return msg
