"""Nightly Dhan refresh for RA Desk.

Logs in with TOTP, pulls daily candles for every stock and index in the page,
plus company fundamentals, checks the data, and patches the embedded data
in docs/ra-desk.html. If anything looks wrong, the page is left untouched.

Secrets (environment variables): DHAN_CLIENT_ID, DHAN_PIN, DHAN_TOTP_SECRET.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import statistics as st
import sys
import time
from pathlib import Path

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
API = "https://api.dhan.co/v2"
AUTH = "https://auth.dhan.co/app/generateAccessToken"
SCRIP_MASTER = "https://images.dhan.co/api-data/api-scrip-master.csv"
BARS = 286            # bars kept per series (same as the page today)
LOOKBACK_DAYS = 430   # calendar days requested, enough for 286 trading days
DATA_RE = re.compile(r"(<script>window\.NSET=)(\{.*?\})(;?</script>)", re.S)

INDEX_ALIASES = {
    "Nifty 50": ["NIFTY", "NIFTY 50"],
    "Nifty Bank": ["BANKNIFTY", "NIFTY BANK"],
    "India VIX": ["INDIA VIX", "INDIAVIX"],
    "Nifty Financial Services": ["FINNIFTY", "NIFTY FIN SERVICE", "NIFTY FINANCIAL SERVICES"],
    "Nifty Midcap 100": ["NIFTY MIDCAP 100", "NIFTY MIDCAP100", "MIDCAP 100"],
    "Nifty Infrastructure": ["NIFTY INFRA", "NIFTY INFRASTRUCTURE"],
    "Nifty PSU Bank": ["NIFTY PSU BANK", "PSUBANK"],
}


class RefreshError(Exception):
    """Raised when the data fails a check. The page is not written."""


# ---------------------------------------------------------------- Dhan client
class Dhan:
    def __init__(self, client_id: str, token: str):
        import requests  # imported here so tests can run without it
        self.s = requests.Session()
        self.s.headers.update({"access-token": token, "client-id": client_id,
                               "Content-Type": "application/json", "Accept": "application/json"})
        self.client_id = client_id

    def post(self, path: str, body: dict) -> dict:
        return _retry(lambda: self._post(path, body))

    def _post(self, path, body):
        time.sleep(0.25)  # data APIs allow 5 requests a second
        r = self.s.post(API + path, json=body, timeout=30)
        if r.status_code == 429 or "RL001" in r.text or '"805"' in r.text:
            raise TransientError(f"rate limited on {path}")
        if r.status_code >= 500:
            raise TransientError(f"{r.status_code} on {path}")
        if r.status_code != 200:
            raise RefreshError(f"{path} returned {r.status_code}: {r.text[:200]}")
        return r.json()

    def daily(self, security_id: str, segment: str, instrument: str, start: dt.date, end: dt.date) -> dict:
        return self.post("/charts/historical", {
            "securityId": str(security_id), "exchangeSegment": segment, "instrument": instrument,
            "expiryCode": 0, "oi": False,
            "fromDate": start.isoformat(), "toDate": (end + dt.timedelta(days=1)).isoformat()})

    def company(self, security_id: str) -> dict:
        return self.post("/data/companyinfo", {"securityId": str(security_id), "exchangeSegment": "NSE_EQ",
                                               "instrument": "EQUITY", "metrics": ["CO", "RATIOS", "SHP"]})


class TransientError(Exception):
    pass


def _retry(fn, tries=3, waits=(60, 120, 240)):
    for i in range(tries):
        try:
            return fn()
        except TransientError as e:
            if i == tries - 1:
                raise RefreshError(f"gave up after {tries} tries: {e}")
            print(f"  retry in {waits[i]}s ({e})", flush=True)
            time.sleep(waits[i])


def clean_secrets(client_id: str, pin: str, totp_secret: str) -> tuple[str, str, str]:
    """Strip the spaces, dashes and line breaks that copy-paste adds."""
    cid = re.sub(r"\s", "", client_id or "")
    p = re.sub(r"\s", "", pin or "")
    sec = re.sub(r"[\s\-]", "", totp_secret or "").upper().rstrip("=")
    return cid, p, sec


def describe_secrets(cid: str, pin: str, sec: str) -> list[str]:
    """Safe format checks. Never prints the values themselves."""
    import base64
    try:
        base64.b32decode(sec + "=" * (-len(sec) % 8))
        b32 = True
    except Exception:
        b32 = False
    notes = [f"client id: {len(cid)} chars, {'all digits' if cid.isdigit() else 'NOT all digits'}",
             f"pin: {len(pin)} chars, {'all digits' if pin.isdigit() else 'NOT all digits'}",
             f"totp secret: {len(sec)} chars, {'valid' if b32 else 'NOT valid'} base32 (A-Z, 2-7)"]
    return notes


def login(client_id: str, pin: str, totp_secret: str) -> str:
    import pyotp
    import requests

    cid, pin, sec = clean_secrets(client_id, pin, totp_secret)
    for n in describe_secrets(cid, pin, sec):
        print("  check " + n, flush=True)
    tries = {"n": 0}

    def once():
        tries["n"] += 1
        code = pyotp.TOTP(sec).now()
        r = requests.post(AUTH, params={"dhanClientId": cid, "pin": pin, "totp": code}, timeout=30)
        if r.status_code >= 500:
            raise TransientError(f"auth {r.status_code}")
        try:
            j = r.json()
        except ValueError:
            j = {"raw": r.text[:160]}
        tok = j.get("accessToken") or (j.get("data") or {}).get("accessToken") if isinstance(j, dict) else None
        if tok:
            return tok
        msg = str(j)[:200]
        # A code can be rejected right at the 30-second boundary: retry once with the next code.
        if tries["n"] == 1:
            raise TransientError(f"login refused ({r.status_code}): {msg}")
        raise RefreshError(
            f"Dhan refused the login ({r.status_code}): {msg}. Check: DHAN_PIN is the Dhan login PIN "
            "(not the CDSL T-PIN), DHAN_TOTP_SECRET is the setup key from Dhan's API TOTP setup, "
            "and TOTP is enabled on the account.")

    return _retry(once, tries=2, waits=(31, 0))


# ---------------------------------------------------------------- symbol map
def norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def build_maps(scrip_csv: str, symbols: list[str], indices: list[str]) -> tuple[dict, dict]:
    eq, ix = {}, {}
    rows = list(csv.DictReader(io.StringIO(scrip_csv)))
    want = set(symbols)
    for r in rows:
        if r.get("SEM_EXM_EXCH_ID") != "NSE":
            continue
        inst = r.get("SEM_INSTRUMENT_NAME", "")
        if inst == "EQUITY" and r.get("SEM_SEGMENT") == "E":
            sym = r.get("SEM_TRADING_SYMBOL", "")
            if sym in want and (sym not in eq or r.get("SEM_SERIES") == "EQ"):
                eq[sym] = r["SEM_SMST_SECURITY_ID"]
        elif inst == "INDEX":
            keys = {norm(r.get("SEM_TRADING_SYMBOL")), norm(r.get("SM_SYMBOL_NAME")), norm(r.get("SEM_CUSTOM_SYMBOL"))}
            for name in indices:
                cands = {norm(a) for a in INDEX_ALIASES.get(name, [])} | {norm(name)}
                if name not in ix and keys & cands:
                    ix[name] = r["SEM_SMST_SECURITY_ID"]
    return eq, ix


# ---------------------------------------------------------------- data shaping
CLOSE_DONE = dt.time(15, 35)


def drop_partial(o: dict, now: dt.datetime) -> dict:
    """A run during market hours must not store today's unfinished candle as a close."""
    if o["d"] and o["d"][-1] == now.date().isoformat() and now.timetz().replace(tzinfo=None) < CLOSE_DONE:
        return {k: v[:-1] for k, v in o.items()}
    return o


def quotes(dhan, eq_ids, idx_ids) -> dict:
    """Today's OHLC/LTP (and volume when given) from Dhan's quote API: {(seg, sid): (o, h, l, ltp, vol)}."""
    out = {}
    eq_ids, idx_ids = [int(x) for x in eq_ids], [int(x) for x in idx_ids]
    for i in range(0, max(len(eq_ids), 1), 900):
        body = {}
        if eq_ids[i:i + 900]:
            body["NSE_EQ"] = eq_ids[i:i + 900]
        if i == 0 and idx_ids:
            body["IDX_I"] = idx_ids
        if not body:
            continue
        time.sleep(1.1)
        try:
            r = dhan.post("/marketfeed/quote", body)
        except Exception as e:
            print(f"  quote call failed ({str(e)[:80]}); trying ohlc")
            r = dhan.post("/marketfeed/ohlc", body)
        for seg, rows in (r.get("data") or {}).items():
            for sid, q in (rows or {}).items():
                o = (q or {}).get("ohlc") or {}
                ltp = float(q.get("last_price") or 0)
                if ltp > 0:
                    out[(seg, str(sid))] = (float(o.get("open") or 0), float(o.get("high") or 0), float(o.get("low") or 0), ltp, float(q.get("volume") or 0))
    return out


def append_today(o: dict, q, now: dt.datetime) -> bool:
    """Add today's bar from a quote when the daily history does not have it yet (Dhan adds it later)."""
    if not q or not o["d"]:
        return False
    day = now.date().isoformat()
    op, hi, lo, ltp, vol = q
    if o["d"][-1] >= day or now.weekday() >= 5 or now.timetz().replace(tzinfo=None) < CLOSE_DONE or op <= 0:
        return False
    if abs(op / o["o"][-1] - 1) < 2e-4 and abs(hi / o["h"][-1] - 1) < 2e-4:
        return False          # quote repeats the last stored session: holiday
    o["d"].append(day)
    for k, v in (("o", op), ("h", max(hi, ltp)), ("l", min(lo or ltp, ltp)), ("c", ltp)):
        o[k].append(v)
    if "v" in o:
        o["v"].append(vol)
    for k in list(o):
        o[k] = o[k][-BARS:]
    return True


def to_series(resp: dict) -> dict:
    ts = resp.get("timestamp") or []
    if not ts:
        raise RefreshError("empty candle reply")
    d = [dt.datetime.fromtimestamp(t, IST).date().isoformat() for t in ts]
    out = {"d": d, "o": resp["open"], "h": resp["high"], "l": resp["low"], "c": resp["close"]}
    if "volume" in resp:
        out["v"] = [float(x) for x in resp["volume"]]
    return {k: v[-BARS:] for k, v in out.items()}


def sma(a, n):
    return st.mean(a[-n:]) if len(a) >= n else None


def ema_series(a, n):
    k, e, out = 2 / (n + 1), a[0], []
    for x in a:
        e = x * k + e * (1 - k)
        out.append(e)
    return out


def rsi(c, n=14):
    g = [max(c[i] - c[i - 1], 0) for i in range(1, len(c))]
    l_ = [max(c[i - 1] - c[i], 0) for i in range(1, len(c))]
    if len(g) < n:
        return None
    ag, al = st.mean(g[:n]), st.mean(l_[:n])
    for i in range(n, len(g)):
        ag, al = (ag * (n - 1) + g[i]) / n, (al * (n - 1) + l_[i]) / n
    return 100.0 if al == 0 else 100 - 100 / (1 + ag / al)


def tech(o: dict, nifty_c: list[float]) -> dict:
    """Recompute the price-based fields the page shows. Same definitions as before."""
    c, h, l_, v = o["c"], o["h"], o["l"], o.get("v") or []
    last = c[-1]
    ret = lambda k: last / c[-1 - k] - 1 if len(c) > k else None
    vs = lambda k: (last / sma(c, k) - 1) if sma(c, k) else None
    tr = [max(h[i] - l_[i], abs(h[i] - c[i - 1]), abs(l_[i] - c[i - 1])) for i in range(1, len(c))]
    macd = [a - b for a, b in zip(ema_series(c, 12), ema_series(c, 26))]
    sig = ema_series(macd, 9)
    n20 = nifty_c[-1] / nifty_c[-21] - 1 if len(nifty_c) > 20 else 0
    r = {"r1": ret(1), "r5": ret(5), "r21": ret(21), "r63": ret(63), "r252": ret(252),
         "rs20": (ret(20) or 0) - n20, "rsi": rsi(c), "atr_pct": st.mean(tr[-14:]) / last if tr else None,
         "vs20": vs(20), "vs50": vs(50), "vs200": vs(200), "hi52": last / max(h[-250:]) - 1,
         "macd_up": macd[-1] > sig[-1], "volr": (v[-1] / st.mean(v[-21:-1])) if len(v) > 21 and st.mean(v[-21:-1]) else None}
    v50, v200 = r["vs50"] or 0, r["vs200"] or 0
    r["trend"] = "Uptrend" if v50 > 0 and v200 > 0 else "Downtrend" if v50 < 0 and v200 < 0 else "Mixed"
    return r


# ---------------------------------------------------------------- checks
def check(new_idx: dict, new_stk: dict, old: dict, today: dt.date) -> str:
    """Raise RefreshError if the pull looks wrong. Return the new last bar date."""
    if "Nifty 50" not in new_idx:
        raise RefreshError("Nifty 50 not fetched")
    last = new_idx["Nifty 50"]["d"][-1]
    if last > today.isoformat():
        raise RefreshError(f"bar dated in the future: {last}")
    missing = [s for s in old["stocks"] if s not in new_stk]
    if len(missing) > 2:
        raise RefreshError(f"{len(missing)} stocks missing: {missing[:5]}")
    stale = [s for s, o in new_stk.items() if o["d"][-1] != last]
    if len(stale) > 5:
        raise RefreshError(f"{len(stale)} stocks not updated to {last}: {stale[:5]}")
    flat = [s for s, o in new_stk.items() if len(o["c"]) > 1 and o["c"][-1] == o["c"][-2] and o["d"][-1] != o["d"][-2]]
    if len(flat) > len(new_stk) * 0.6:
        raise RefreshError(f"{len(flat)} stocks show an unchanged close; feed looks stale")
    for s, o in new_stk.items():
        if len(o["c"]) < 200:
            raise RefreshError(f"{s}: only {len(o['c'])} bars")
        jump = abs(o["c"][-1] / o["c"][-2] - 1)
        if jump > 0.25:
            raise RefreshError(f"{s}: {jump:.0%} one-day move; check for a split before publishing")
        if min(o["c"][-5:]) <= 0:
            raise RefreshError(f"{s}: non-positive price")
    return last


# ---------------------------------------------------------------- merge
def merge(nset: dict, new_idx: dict, new_stk: dict, fund: dict, last: str, now: dt.datetime) -> dict:
    nifty_c = new_idx["Nifty 50"]["c"]
    for name, o in new_idx.items():
        nset["idx"][name] = {k: o[k] for k in ("d", "o", "h", "l", "c")}
    for sym, o in new_stk.items():
        x = nset["stocks"][sym]
        x["ohlc"] = o
        x["prev"] = o["c"][-2]
        x["vol"] = o["v"][-1] if o.get("v") else x.get("vol")
        if o.get("v"):
            x["avgvol3m"] = st.mean(o["v"][-63:])
        x["hi52"], x["lo52"] = max(o["h"][-250:]), min(o["l"][-250:])
        x["tech"].update({k: v for k, v in tech(o, nifty_c).items() if v is not None})
        if sym in fund:
            x["dhan_fund"] = fund[sym]
    # sector strip uses ltp/prev
    for sec in nset.get("sectors", []):
        o = nset["idx"].get(sec.get("name"))
        if o and len(o["c"]) > 1:
            sec["ltp"], sec["prev"] = o["c"][-1], o["c"][-2]
    nset["asof"] = now.strftime("%Y-%m-%d %H:%M")
    nset["bar_today"] = last
    nset["partial_today"] = False
    nset["refreshed_by"] = "dhan-nightly"
    return nset


LATEST_BARS = 25  # bars per series in the small file the page loads from GitHub


def latest_payload(nset: dict) -> dict:
    """A small file (well under GitHub's 1 MB contents limit) holding what changes nightly."""
    cut = lambda o, keys: {k: o[k][-LATEST_BARS:] for k in keys if k in o}
    stk = {}
    for sym, x in nset["stocks"].items():
        stk[sym] = {"ohlc": cut(x["ohlc"], ("d", "o", "h", "l", "c", "v")),
                    **{k: x[k] for k in ("prev", "vol", "avgvol3m", "hi52", "lo52", "tech", "dhan_fund") if k in x}}
    return {"schema": 1, "asof": nset.get("asof"), "bar_today": nset.get("bar_today"),
            "partial_today": nset.get("partial_today", False),
            "idx": {n: cut(o, ("d", "o", "h", "l", "c")) for n, o in nset["idx"].items()},
            "sectors": [{"name": s.get("name"), "ltp": s.get("ltp"), "prev": s.get("prev")} for s in nset.get("sectors", [])],
            "stocks": stk}


def write_latest(path: Path, nset: dict) -> int:
    blob = json.dumps(latest_payload(nset), separators=(",", ":"), ensure_ascii=False)
    path.write_text(blob, encoding="utf-8")
    return len(blob.encode())


def read_nset(html: str) -> dict:
    m = DATA_RE.search(html)
    if not m:
        raise RefreshError("could not find window.NSET in the page")
    return json.loads(m.group(2))


def write_nset(html: str, nset: dict) -> str:
    blob = json.dumps(nset, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    return DATA_RE.sub(lambda m: m.group(1) + blob + m.group(3), html, count=1)


# ---------------------------------------------------------------- main
def run(page: Path, dhan, scrip_csv: str, now: dt.datetime, with_fund: bool = True) -> str:
    html = page.read_text(encoding="utf-8")
    nset = read_nset(html)
    old_last = max(o["d"][-1] for o in nset["idx"].values())
    symbols, indices = list(nset["stocks"]), list(nset["idx"])
    eq, ix = build_maps(scrip_csv, symbols, indices)
    for name in indices:
        if name not in ix:
            print(f"  warning: index '{name}' not found in scrip master; keeping old data")
    start = now.date() - dt.timedelta(days=LOOKBACK_DAYS)

    new_idx, new_stk, fund = {}, {}, {}
    for name, sid in ix.items():
        new_idx[name] = drop_partial(to_series(dhan.daily(sid, "IDX_I", "INDEX", start, now.date())), now)
    for sym, sid in eq.items():
        try:
            new_stk[sym] = drop_partial(to_series(dhan.daily(sid, "NSE_EQ", "EQUITY", start, now.date())), now)
        except RefreshError as e:
            print(f"  warning: {sym}: {e}")
        if with_fund:
            try:
                fund[sym] = dhan.company(sid)
            except RefreshError as e:
                print(f"  warning: company info {sym}: {e}")

    try:
        qs = quotes(dhan, [eq[s] for s in new_stk], [ix[n] for n in new_idx])
        added = sum(append_today(new_idx[n], qs.get(("IDX_I", str(ix[n]))), now) for n in new_idx) + \
            sum(append_today(new_stk[s], qs.get(("NSE_EQ", str(eq[s]))), now) for s in new_stk)
        if added:
            print(f"  added today's bar from live quotes to {added} series")
    except Exception as e:
        print(f"  warning: could not add today's bar from quotes: {str(e)[:120]}")
    last = check(new_idx, new_stk, nset, now.date())
    if last <= old_last and nset.get("partial_today") is False:
        return f"no new session (latest bar {last}); page unchanged"
    merged = merge(nset, new_idx, new_stk, fund, last, now)
    page.write_text(write_nset(html, merged), encoding="utf-8")
    size = write_latest(page.with_name("radesk-latest.json"), merged)
    return (f"updated to {last}: {len(new_stk)} stocks, {len(new_idx)} indices, {len(fund)} fundamentals; "
            f"latest file {size // 1024} KB")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default="docs/ra-desk.html")
    ap.add_argument("--no-fund", action="store_true", help="skip company info calls")
    ap.add_argument("--with-n500", action="store_true", help="also rank the Nifty 500 and update the terminal page")
    ap.add_argument("--with-options", action="store_true", help="also save the options snapshot (same login)")
    ap.add_argument("--with-tech", action="store_true", help="also compute today's technical signals (same login)")
    a = ap.parse_args(argv)
    try:
        cid, pin, sec = (os.environ[k] for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"))
    except KeyError as e:
        print(f"missing secret {e}", file=sys.stderr)
        return 2
    import requests
    now = dt.datetime.now(IST)
    if now.weekday() >= 5:
        print("weekend; nothing to do")
        return 0
    try:
        token = login(cid, pin, sec)
        scrip = requests.get(SCRIP_MASTER, timeout=60).text
        client = Dhan(cid, token)
        print(run(Path(a.page), client, scrip, now, with_fund=not a.no_fund))
        if a.with_options:
            try:
                import options_snapshot
                print(options_snapshot.save_snapshot(client, scrip, Path(a.page).resolve().parents[1]))
            except Exception as e:  # options must never block the price refresh
                print(f"  warning: options snapshot failed: {e}")
        if a.with_n500:
            try:
                import n500
                print(n500.run(client, scrip, Path(a.page).resolve().parents[1], now))
            except Exception as e:
                print(f"  warning: Nifty 500 board failed: {e}")
        if a.with_tech:
            try:
                import tech_model
                tech_model.run_today(client, Path(a.page).resolve().parents[1])
            except Exception as e:
                print(f"  warning: technical signals failed: {e}")
        return 0
    except RefreshError as e:
        print(f"REFRESH FAILED, page left unchanged: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
