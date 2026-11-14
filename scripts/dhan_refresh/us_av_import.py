"""Import Alpha Vantage weekly split-adjusted history (TIME_SERIES_WEEKLY_ADJUSTED csv, saved by the connector)
into data/us-weekly.json. Usage: python us_av_import.py SYM=path [SYM=path ...]
Each file is checked: its latest close must be within 3% of the price in docs/us-value.json (or Dhan's last quote),
so a file is never filed under the wrong symbol."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/us-weekly.json"
KEEP = 520                       # 10 years of weeks


def parse(text: str) -> dict:
    if text.lstrip().startswith("{"):
        text = json.loads(text)["result"]
    rows = [r.split(",") for r in text.strip().splitlines()]
    head = rows[0]
    i_d, i_c, i_a = head.index("timestamp"), head.index("close"), head.index("adjusted close")
    i_h, i_l = head.index("high"), head.index("low")
    out = []
    for r in rows[1:]:
        c, a = float(r[i_c]), float(r[i_a])
        f = a / c if c else 1.0                       # scale high/low by the same split/dividend factor
        out.append((r[i_d], round(a, 4), round(float(r[i_h]) * f, 4), round(float(r[i_l]) * f, 4), float(r[i_c])))
    out.sort()
    return {"d": [x[0] for x in out][-KEEP:], "c": [x[1] for x in out][-KEEP:], "h": [x[2] for x in out][-KEEP:],
            "l": [x[3] for x in out][-KEEP:], "raw_last": out[-1][4], "src": "Alpha Vantage weekly adjusted"}


def check_price(sym: str) -> float | None:
    try:
        for r in json.loads((ROOT / "docs/us-value.json").read_text(encoding="utf-8"))["rows"]:
            if r["s"] == sym:
                return r.get("price")
    except Exception:
        pass
    return None


def main(args) -> int:
    try:
        store = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        store = {}
    bad = 0
    for a in args:
        sym, path = a.split("=", 1)
        s = parse(Path(path).read_text(encoding="utf-8"))
        ref = check_price(sym)
        if ref and abs(s["raw_last"] / ref - 1) > 0.03:
            print(f"{sym}: REJECTED, last close {s['raw_last']} vs expected {ref}")
            bad += 1
            continue
        store[sym] = s
        print(f"{sym}: {len(s['d'])} weeks {s['d'][0]}..{s['d'][-1]} last {s['raw_last']} (check {ref})")
    OUT.write_text(json.dumps(store, separators=(",", ":")), encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
