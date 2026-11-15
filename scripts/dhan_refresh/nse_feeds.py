"""Daily feeds from NSE's own public pages (the method of the owner's nse-day-trader skill): results and
board-meeting calendar, corporate announcements (filings) and FII/DII cash flows. No prices are taken from NSE.

Writes docs/nse-feeds.json. Every part is optional: if NSE does not answer (it sometimes refuses cloud servers),
the previous file is kept and the failure is recorded in "errors", so the desk can show the data's real date.
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = "https://www.nseindia.com/api/"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
_COOKIE = {}


def _get(url: str, accept="application/json", timeout=25) -> str:
    h = {"User-Agent": UA, "Accept": accept, "Accept-Encoding": "gzip", "Accept-Language": "en-US,en;q=0.9",
         "Referer": "https://www.nseindia.com/"}
    if _COOKIE.get("c"):
        h["Cookie"] = _COOKIE["c"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        ck = r.headers.get_all("Set-Cookie") or []
        if ck:
            _COOKIE["c"] = "; ".join(c.split(";")[0] for c in ck)
        data = r.read()
        return (gzip.decompress(data) if r.headers.get("Content-Encoding") == "gzip" else data).decode("utf-8", "replace")


def nse_json(endpoint: str):
    last = None
    for attempt in range(3):
        try:
            if attempt == 1:                           # a first visit to the home page sets the cookies NSE expects
                try:
                    _get("https://www.nseindia.com/", accept="text/html")
                except Exception:
                    pass
            return json.loads(_get(API + endpoint))
        except (urllib.error.URLError, OSError, ValueError) as e:
            last = e
            time.sleep(2 + 2 * attempt)
    raise RuntimeError(f"{endpoint.split('?')[0]}: {str(last)[:100]}")


def parse_events(rows, symbols: set, today: dt.date, days: int = 21) -> dict:
    out = {}
    for r in rows if isinstance(rows, list) else []:
        s = r.get("symbol")
        try:
            d = dt.datetime.strptime(r.get("date", ""), "%d-%b-%Y").date()
        except ValueError:
            continue
        if s in symbols and 0 <= (d - today).days <= days:
            out.setdefault(s, []).append({"d": d.isoformat(), "p": (r.get("purpose") or "")[:60]})
    return {s: sorted(v, key=lambda x: x["d"])[:3] for s, v in out.items()}


def parse_filings(rows, symbols: set, keep: int = 4) -> dict:
    out = {}
    for r in rows if isinstance(rows, list) else []:
        s = r.get("symbol")
        if s not in symbols:
            continue
        try:
            t = dt.datetime.strptime(r.get("an_dt") or r.get("exchdisstime"), "%d-%b-%Y %H:%M:%S")
        except (TypeError, ValueError):
            continue
        txt = (r.get("attchmntText") or "").strip()
        out.setdefault(s, []).append({"t": t.strftime("%Y-%m-%d %H:%M"), "title": ((r.get("desc") or "Announcement") + (": " + txt if txt else ""))[:170]})
    return {s: sorted(v, key=lambda x: x["t"], reverse=True)[:keep] for s, v in out.items()}


def parse_fii(rows) -> dict:
    out = {}
    for r in rows if isinstance(rows, list) else []:
        try:
            d = dt.datetime.strptime(r.get("date", ""), "%d-%b-%Y").date().isoformat()
            out.setdefault(d, {})[("FII" if "FII" in r.get("category", "") else "DII")] = {
                "buy": float(r["buyValue"]), "sell": float(r["sellValue"]), "net": float(r["netValue"])}
        except (ValueError, KeyError, TypeError):
            continue
    return out


def run(root: Path = ROOT) -> str:
    p = root / "docs/nse-feeds.json"
    try:
        old = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        old = {}
    symbols = {r["s"] for r in json.loads((root / "docs/n500.json").read_text(encoding="utf-8")).get("rows", [])}
    today = dt.datetime.now(IST).date()
    out = {"events": old.get("events", {}), "events_asof": old.get("events_asof"), "filings": old.get("filings", {}),
           "filings_asof": old.get("filings_asof"), "fiidii": old.get("fiidii", {}), "errors": []}
    stamp = dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M")
    try:
        raw = nse_json("event-calendar?index=equities")
        print(f"  event calendar: {type(raw).__name__}, {len(raw) if hasattr(raw, '__len__') else '?'} rows; sample {json.dumps(raw[:2] if isinstance(raw, list) else raw)[:400]}")
        out["events"], out["events_asof"] = parse_events(raw, symbols, today), stamp
    except Exception as e:
        out["errors"].append(str(e))
    try:
        fr = (today - dt.timedelta(days=5)).strftime("%d-%m-%Y")
        rows = nse_json(f"corporate-announcements?index=equities&from_date={fr}&to_date={today.strftime('%d-%m-%Y')}")
        out["filings"], out["filings_asof"] = parse_filings(rows, symbols), stamp
    except Exception as e:
        out["errors"].append(str(e))
    try:
        f = parse_fii(nse_json("fiidiiTradeReact"))
        if f:
            merged = {**out["fiidii"], **f}
            out["fiidii"] = {d: merged[d] for d in sorted(merged)[-60:]}
    except Exception as e:
        out["errors"].append(str(e))
    p.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    return (f"nse feeds: {len(out['events'])} stocks with events, {len(out['filings'])} with filings, "
            f"FII/DII to {max(out['fiidii']) if out['fiidii'] else None}; errors {out['errors'] or 'none'}")


if __name__ == "__main__":
    print(run())
    sys.exit(0)
