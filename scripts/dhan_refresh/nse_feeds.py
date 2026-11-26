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



def news_cat(title: str) -> str:
    """Kind of announcement: NSE's own subject, with the catch-all subjects split by what the text says."""
    head, _, rest = (title or "").partition(":")
    h, t = head.strip(), (title or "").lower()
    for k, words in (("Order win", ("order", "contract", "bagging")), ("Acquisition or merger", ("acqui", "merger", "amalgamation")),
                     ("Results", ("financial result", "quarterly result", "results for")), ("Fund raising", ("fund rais", "qip", "preferential", "rights issue")),
                     ("Rating change", ("credit rating", "rating")), ("Dividend or buyback", ("dividend", "buyback", "buy-back")),
                     ("Management change", ("resignation", "appointment", "change in management", "change in director")),
                     ("Regulatory action", ("action(s)", "penalty", "show cause", "order passed"))):
        if any(w in t for w in words):
            return k
    if h in ("Analysts/Institutional Investor Meet/Con. Call Updates", "Investor Presentation"):
        return "Analyst meet or presentation"
    if h in ("Copy of Newspaper Publication", "Trading Window", "Shareholders meeting", "ESOP/ESOS/ESPS", "Allotment of Securities", "Record Date"):
        return "Routine filing"
    return "Other update"


def archive_filings(rows, symbols: set, arch: dict) -> int:
    """Add raw NSE announcement rows to the archive {symbol: [[time, title], ...]}; returns how many were new."""
    new = 0
    for s, items in parse_filings(rows, symbols, keep=10 ** 6).items():
        have = {tuple(x) for x in arch.get(s, [])}
        for x in items:
            k = (x["t"], x["title"])
            if k not in have:
                arch.setdefault(s, []).append(list(k))
                new += 1
    return new


def news_effects(arch: dict, chart: dict, recent: dict) -> dict:
    """How the price moved after each kind of announcement, on the last year of Dhan closes: return from the close before
    the announcement's trading day to that day (1 day) and four sessions later (5 days), minus the Nifty's over the same days.
    An announcement after 15:30 IST counts on the next session."""
    d = chart.get("d") or []
    S = chart.get("s") or {}
    nc = (S.get("NIFTY") or {}).get("c") or []
    if len(nc) < 30:
        return {}
    pos = {x: i for i, x in enumerate(d)}
    off = len(d) - len(nc)

    def day0(t):
        day, hm = t[:10], t[11:16]
        i = next((k for k in range(len(d)) if d[k] >= day), None)
        if i is not None and d[i] == day and hm > "15:30":
            i += 1
        return i if i is not None and i < len(d) else None

    acc = {}
    for s, items in arch.items():
        c = (S.get(s) or {}).get("c")
        if not c:
            continue
        o = len(d) - len(c)
        seen = set()
        for t, title in items:
            i = day0(t)
            if i is None or i - 1 - o < 0 or i - 1 - off < 0:
                continue
            cat = news_cat(title)
            if (cat, i) in seen:                         # one count per kind of news per stock per day
                continue
            seen.add((cat, i))
            a0, n0 = c[i - 1 - o], nc[i - 1 - off]
            if not a0 or not n0:
                continue
            r = {}
            for h, j in (("d1", i), ("d5", i + 4)):
                if j < len(d) and c[j - o] and nc[j - off]:
                    r[h] = (c[j - o] / a0 - 1) - (nc[j - off] / n0 - 1)
            if "d1" in r:
                r["i"] = i
                acc.setdefault(cat, []).append(r)
    out = {}
    for cat, rs in acc.items():
        row = {"n": len(rs)}
        for h in ("d1", "d5"):
            xs = [r[h] for r in rs if h in r]
            byday = {}
            for r in rs:                              # t-stat on daily averages: same-day news shares the market's moves
                if h in r:
                    byday.setdefault(r["i"], []).append(r[h])
            ds = [sum(v) / len(v) for v in byday.values()]
            row["days"] = len(byday) if h == "d1" else row.get("days")
            if len(xs) >= 5 and len(ds) >= 3:
                m = sum(xs) / len(xs)
                md = sum(ds) / len(ds)
                sd = (sum((x - md) ** 2 for x in ds) / (len(ds) - 1)) ** 0.5
                row[h] = round(m, 4)
                row[h + "_up"] = round(sum(x > 0 for x in xs) / len(xs), 3)
                row[h + "_t"] = round(md / (sd / len(ds) ** 0.5), 2) if sd else 0
                row[h + "_abs"] = round(sum(abs(x) for x in xs) / len(xs), 4)   # typical size of the move either way
        row["moves"] = bool((row.get("days") or 0) >= 30 and abs(row.get("d1_t", 0)) >= 2)
        out[cat] = row
    items = sorted(([s, t, title, news_cat(title)] for s, v in recent.items() for t, title in
                    ((x["t"], x["title"]) for x in v)), key=lambda z: z[1], reverse=True)[:80]
    return {"cats": out, "items": items, "from": d[0], "to": d[-1]}


def run_news(root: Path, today: dt.date, symbols: set, recent_rows) -> str:
    """Keep a growing archive of NSE announcements (docs/news-archive.json, first run back-fills a year a month at a time)
    and write docs/news.json: the price effect of each kind of announcement and the latest items."""
    ap = root / "docs/news-archive.json"
    try:
        arch = json.loads(ap.read_text(encoding="utf-8"))
    except Exception:
        arch = {}
    added = archive_filings(recent_rows, symbols, arch) if recent_rows else 0
    first = min((t for v in arch.values() for t, _ in v), default=today.isoformat())
    if first > (today - dt.timedelta(days=300)).isoformat():                # back-fill up to a year, 3 months per night
        end = dt.date.fromisoformat(first[:10]) - dt.timedelta(days=1)
        for _ in range(3):
            st = end - dt.timedelta(days=29)
            if st < today - dt.timedelta(days=370):
                break
            try:
                added += archive_filings(nse_json(f"corporate-announcements?index=equities&from_date={st.strftime('%d-%m-%Y')}&to_date={end.strftime('%d-%m-%Y')}"), symbols, arch)
            except Exception as e:
                print(f"  news back-fill {st}..{end}: {e}")
                break
            end = st - dt.timedelta(days=1)
            time.sleep(2)
    cut = (today - dt.timedelta(days=400)).isoformat()
    arch = {s: sorted([x for x in v if x[0] >= cut])[-400:] for s, v in arch.items()}
    ap.write_text(json.dumps(arch, separators=(",", ":")), encoding="utf-8")
    try:
        chart = json.loads((root / "docs/chart-data.json").read_text(encoding="utf-8"))
    except Exception:
        chart = {}
    recent = parse_filings(recent_rows, symbols, keep=6) if recent_rows else {}
    res = news_effects(arch, chart, recent)
    res["asof"] = dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M")
    res["archived"] = sum(len(v) for v in arch.values())
    (root / "docs/news.json").write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
    return f"news: {added} new announcements archived ({res['archived']} total), {len(res.get('cats', {}))} kinds measured"


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
        rows = None
        out["errors"].append(str(e))
    try:
        print("  " + run_news(root, today, symbols, rows))
    except Exception as e:
        out["errors"].append("news: " + str(e)[:120])
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
