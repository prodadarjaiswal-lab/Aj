"""Nifty 500 board: nightly rank, status and setups for about 500 stocks.

Writes docs/n500.json and injects it (plus the latest Nifty 50 data and the
back-test results) into docs/nse-terminal.html. Never blocks the price refresh.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import re
import sys
from pathlib import Path

import refresh as R
import setups as SU

LIST_URLS = ("https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
             "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
             "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
      "Accept": "text/csv,*/*"}
N500_RE = re.compile(r'(<script id="n500-data">window\.N500=)(.*?)(;</script>)', re.S)
BT_RE = re.compile(r"/\*BT\*/.*?/\*BT\*/", re.S)


def parse_list(text: str) -> list[dict]:
    out = []
    for r in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        sym = (r.get("Symbol") or "").strip()
        if sym and (r.get("Series") or "EQ").strip() in ("EQ", "BE", ""):
            out.append({"s": sym, "name": (r.get("Company Name") or sym).strip(), "ind": (r.get("Industry") or "").strip()})
    return out


def get_universe(dhan, root: Path) -> list[dict]:
    """NSE list, else the cached copy, else Dhan's market-movers universes."""
    import requests
    cache = root / "data/nifty500.csv"
    for u in LIST_URLS:
        try:
            t = requests.get(u, headers=UA, timeout=25).text
            rows = parse_list(t)
            if len(rows) >= 400:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(t, encoding="utf-8")
                print(f"  Nifty 500 list from {u.split('/')[2]}: {len(rows)}")
                return rows
        except Exception as e:
            print(f"  list fetch failed ({u.split('/')[2]}): {str(e)[:80]}")
    if cache.exists():
        rows = parse_list(cache.read_text(encoding="utf-8"))
        if len(rows) >= 400:
            print(f"  Nifty 500 list from cache: {len(rows)}")
            return rows
    seen = {}
    for uni in ("NIFTY_100", "NIFTY_MIDCAP_150", "NIFTY_SMALLCAP_250", "NIFTY_500"):
        for cat in ("PRICE_GAINERS", "PRICE_LOSERS"):
            try:
                r = dhan.post("/data/marketmovers", {"exchangeSegment": "NSE_EQ", "instrument": ["EQUITY"], "category": cat, "universe": uni, "limit": 100})
            except Exception as e:
                print(f"  movers {uni}/{cat} failed: {str(e)[:80]}")
                continue
            stack = [r]
            while stack:
                x = stack.pop()
                if isinstance(x, dict):
                    sym = x.get("tradingSymbol") or x.get("symbol") or x.get("SYMBOL") or x.get("displayName")
                    if isinstance(sym, str) and sym.isupper() and len(sym) <= 20:
                        seen[sym] = {"s": sym, "name": x.get("companyName") or x.get("name") or sym, "ind": ""}
                    stack.extend(x.values())
                elif isinstance(x, list):
                    stack.extend(x)
    print(f"  Nifty 500 list from Dhan market movers (partial): {len(seen)}")
    if len(seen) < 150:
        raise R.RefreshError("could not get a Nifty 500 list")
    return list(seen.values())


def build(universe: list[dict], series: dict, nifty: dict) -> dict:
    """series: {sym: {"d","c","h","l","v"}}. Returns the board payload."""
    nmap = dict(zip(nifty["d"], nifty["c"]))
    M, extra = {}, {}
    last_day = nifty["d"][-1]
    for u in universe:
        o = series.get(u["s"])
        if not o:
            continue
        keep = [i for i, d in enumerate(o["d"]) if d in nmap]
        if len(keep) < 230 or o["d"][keep[-1]] != last_day:
            continue
        c, h, l = ([o[k][i] for i in keep] for k in ("c", "h", "l"))
        v = [o["v"][i] for i in keep] if o.get("v") else None
        S = SU.Series(c, h, l, [nmap[o["d"][i]] for i in keep], v)
        m = SU.metrics(S, len(c) - 1)
        if not m:
            continue
        if v and len(v) > 51 and sum(v[-51:-1]) > 0:
            m["volr"] = v[-1] / (sum(v[-51:-1]) / 50)
            m["turn_cr"] = round(sum(a * b for a, b in zip(c[-20:], v[-20:])) / 20 / 1e7, 1)
        M[u["s"]] = m
        extra[u["s"]] = {"name": u["name"], "ind": u["ind"], "sp": [round(x, 2) for x in c[-40:]], "prev": c[-2]}
    SU.rank_universe(M)
    rnd = lambda x: round(x, 4) if isinstance(x, float) else x
    rows = []
    for s in sorted(M, key=lambda k: M[k]["rank"]):
        m = M[s]
        row = {"s": s, **extra[s], **{k: rnd(m.get(k)) for k in ("r1", "r5", "r21", "r63", "r126", "rs1", "rs3", "rs6", "vs20", "vs50", "vs200", "hi52", "volr")},
               "last": round(m["last"], 2), "rsi": round(m["rsi"]) if m.get("rsi") is not None else None,
               "score": m["score"], "rank": m["rank"], "status": m["status"], "turn_cr": m.get("turn_cr")}
        if m.get("setup"):
            row.update({"setup": m["setup"], "trig": round(m["trig"], 2), "fail": round(m["fail"], 2)})
        rows.append(row)
    return {"asof": last_day, "n": len(rows), "rows": rows}


def inject(root: Path, payload: dict | None) -> str:
    """Put the Nifty 500 board, the Nifty 50 data and back-tests into the terminal page."""
    page = root / "docs/nse-terminal.html"
    if not page.exists():
        return "terminal page not found"
    html = page.read_text(encoding="utf-8")
    src = root / "docs/ra-desk.html"
    if src.exists():
        html = R.write_nset(html, R.read_nset(src.read_text(encoding="utf-8")))
    bt = root / "docs/setup-backtest.json"
    if bt.exists() and BT_RE.search(html):
        html = BT_RE.sub(lambda m: "/*BT*/" + json.dumps(json.loads(bt.read_text()), separators=(",", ":")) + "/*BT*/", html, count=1)
    if payload is None and (root / "docs/n500.json").exists():
        payload = json.loads((root / "docs/n500.json").read_text())
    if payload is not None and N500_RE.search(html):
        b5 = root / "docs/setup-backtest-n500.json"
        payload = dict(payload, bt=json.loads(b5.read_text()) if b5.exists() else None)
        blob = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
        html = N500_RE.sub(lambda m: m.group(1) + blob + m.group(3), html, count=1)
    page.write_text(html, encoding="utf-8")
    return "terminal page updated"


def run(dhan, scrip_csv: str, root: Path, now: dt.datetime) -> str:
    uni = get_universe(dhan, root)
    eq, ix = R.build_maps(scrip_csv, [u["s"] for u in uni], ["Nifty 50"])
    start = now.date() - dt.timedelta(days=R.LOOKBACK_DAYS)

    def ser(resp):
        o = R.drop_partial(R.to_series(resp), now)
        return o
    nifty = ser(dhan.daily(ix["Nifty 50"], "IDX_I", "INDEX", start, now.date()))
    series, miss = {}, 0
    for s, sid in eq.items():
        try:
            series[s] = ser(dhan.daily(sid, "NSE_EQ", "EQUITY", start, now.date()))
        except Exception:
            miss += 1
    try:
        qs = R.quotes(dhan, [eq[s] for s in series], [ix["Nifty 50"]])
        R.append_today(nifty, qs.get(("IDX_I", str(ix["Nifty 50"]))), now)
        added = sum(R.append_today(o, qs.get(("NSE_EQ", str(eq[s]))), now) for s, o in series.items())
        if added:
            print(f"  Nifty 500: added today's bar from live quotes to {added} stocks")
    except Exception as e:
        print(f"  Nifty 500: could not add today's bar: {str(e)[:120]}")
    payload = build(uni, series, nifty)
    if payload["n"] < 150:
        raise R.RefreshError(f"only {payload['n']} Nifty 500 stocks had usable data")
    sid_of = {s: sid for s, sid in eq.items()}
    for r in payload["rows"]:
        r["sid"] = int(sid_of[r["s"]])
    (root / "docs/n500.json").write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    setups = sum(1 for r in payload["rows"] if r.get("setup"))
    return f"Nifty 500 board {payload['asof']}: {payload['n']} stocks ranked, {setups} in a setup, {miss} failed; " + inject(root, payload)


if __name__ == "__main__":
    print(inject(Path(sys.argv[1] if len(sys.argv) > 1 else "."), None))
