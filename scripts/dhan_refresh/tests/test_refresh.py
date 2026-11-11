"""Offline tests: a fake Dhan built from the page's own data, plus one new trading day."""
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "dhan_refresh"))
import refresh as R  # noqa: E402

PAGE = ROOT / "docs" / "ra-desk.html"
IDX_SYMS = {"Nifty 50": "NIFTY", "Nifty Bank": "BANKNIFTY", "India VIX": "INDIA VIX", "Nifty IT": "NIFTY IT",
            "Nifty Financial Services": "FINNIFTY", "Nifty Midcap 100": "NIFTY MIDCAP 100",
            "Nifty Infrastructure": "NIFTY INFRA"}
NEWDAY = dt.date(2026, 11, 11)


def scrip_csv(nset):
    head = "SEM_EXM_EXCH_ID,SEM_SEGMENT,SEM_SMST_SECURITY_ID,SEM_INSTRUMENT_NAME,SEM_TRADING_SYMBOL,SM_SYMBOL_NAME,SEM_CUSTOM_SYMBOL,SEM_SERIES"
    rows = [head]
    for i, s in enumerate(nset["stocks"]):
        rows.append(f"NSE,E,{1000+i},EQUITY,{s},{s},{s},EQ")
        rows.append(f"BSE,E,{5000+i},EQUITY,{s},{s},{s},A")
    for i, name in enumerate(nset["idx"]):
        sym = IDX_SYMS.get(name, name.upper())
        rows.append(f"NSE,I,{i+1},INDEX,{sym},{name.upper()},{name},")
    return "\n".join(rows)


class FakeDhan:
    def __init__(self, nset, mutate=None):
        self.by_id = {}
        for i, (s, x) in enumerate(nset["stocks"].items()):
            self.by_id[str(1000 + i)] = x["ohlc"]
        for i, (n, o) in enumerate(nset["idx"].items()):
            self.by_id[str(i + 1)] = o
        self.mutate = mutate or (lambda sid, o: o)

    def daily(self, sid, seg, inst, start, end):
        o = self.by_id[str(sid)]
        n = len(o["c"]) - 1  # drop the duplicated partial bar, then add a real new day
        d, op, hi, lo, c = o["d"][:n], o["o"][:n], o["h"][:n], o["l"][:n], o["c"][:n]
        nc = c[-1] * 1.01
        ts = [int(dt.datetime.fromisoformat(x).replace(hour=0, tzinfo=R.IST).timestamp()) for x in d]
        ts.append(int(dt.datetime(2026, 11, 11, tzinfo=R.IST).timestamp()))
        out = {"timestamp": ts, "open": op + [c[-1]], "high": hi + [nc * 1.005], "low": lo + [c[-1] * 0.995], "close": c + [nc]}
        if "v" in o:
            out["volume"] = o["v"][:n] + [o["v"][n - 1]]
        return self.mutate(str(sid), out)

    def company(self, sid):
        return {"data": {"CO": {"MARKET_CAP": "1"}}}


@pytest.fixture
def page(tmp_path):
    p = tmp_path / "ra-desk.html"
    shutil.copy(PAGE, p)
    return p


def now():
    return dt.datetime(2026, 11, 11, 16, 20, tzinfo=R.IST)


def test_full_refresh_updates_page(page):
    nset = R.read_nset(page.read_text())
    msg = R.run(page, FakeDhan(nset), scrip_csv(nset), now())
    assert msg.startswith("updated to 2026-11-11"), msg
    new = R.read_nset(page.read_text())
    assert new["bar_today"] == "2026-11-11" and new["partial_today"] is False
    t = new["stocks"]["TCS"]
    assert t["ohlc"]["d"][-1] == "2026-11-11" and len(t["ohlc"]["c"]) == R.BARS
    assert abs(t["tech"]["r1"] - 0.01) < 1e-9
    assert "dhan_fund" in t
    assert new["idx"]["Nifty 50"]["d"][-1] == "2026-11-11"
    # every other field is kept
    assert new["fund"] == nset["fund"] and new["stocks"]["TCS"]["val"] == nset["stocks"]["TCS"]["val"]


def test_second_run_same_day_is_noop(page):
    nset = R.read_nset(page.read_text())
    R.run(page, FakeDhan(nset), scrip_csv(nset), now())
    before = page.read_text()
    nset2 = R.read_nset(before)

    class Same(FakeDhan):  # replays the already-stored series
        def daily(self, sid, seg, inst, start, end):
            o = self.by_id[str(sid)]
            ts = [int(dt.datetime.fromisoformat(x).replace(tzinfo=R.IST).timestamp()) for x in o["d"]]
            r = {"timestamp": ts, "open": o["o"], "high": o["h"], "low": o["l"], "close": o["c"]}
            if "v" in o:
                r["volume"] = o["v"]
            return r
    msg = R.run(page, Same(nset2), scrip_csv(nset2), now())
    assert msg.startswith("no new session")
    assert page.read_text() == before


def test_bad_split_like_jump_blocks_write(page):
    nset = R.read_nset(page.read_text())
    before = page.read_text()

    def jump(sid, o):
        if sid == "1000":
            o["close"][-1] = o["close"][-2] * 0.5
        return o
    with pytest.raises(R.RefreshError, match="one-day move"):
        R.run(page, FakeDhan(nset, jump), scrip_csv(nset), now())
    assert page.read_text() == before


def test_stale_feed_blocks_write(page):
    nset = R.read_nset(page.read_text())

    def flat(sid, o):
        o["close"][-1] = o["close"][-2]
        return o
    with pytest.raises(R.RefreshError, match="unchanged close"):
        R.run(page, FakeDhan(nset, flat), scrip_csv(nset), now())


def test_future_bar_rejected(page):
    nset = R.read_nset(page.read_text())
    with pytest.raises(R.RefreshError, match="future"):
        R.run(page, FakeDhan(nset), scrip_csv(nset), dt.datetime(2026, 11, 10, 16, 0, tzinfo=R.IST))


def test_symbol_map_prefers_nse_eq_and_aliases():
    nset = {"stocks": {"M&M": {}, "BAJAJ-AUTO": {}}, "idx": {"Nifty 50": {}, "Nifty Bank": {}, "Nifty Financial Services": {}}}
    eq, ix = R.build_maps(scrip_csv(nset), ["M&M", "BAJAJ-AUTO"], list(nset["idx"]))
    assert eq == {"M&M": "1000", "BAJAJ-AUTO": "1001"}
    assert set(ix) == {"Nifty 50", "Nifty Bank", "Nifty Financial Services"}


def test_secrets_cleaned_and_described_without_values():
    cid, pin, sec = R.clean_secrets(" 1100123456\n", "1234 \n", "jbsw y3dp-ehpk 3pxp\n")
    assert (cid, pin, sec) == ("1100123456", "1234", "JBSWY3DPEHPK3PXP")
    notes = " ".join(R.describe_secrets(cid, pin, sec))
    assert "valid base32" in notes and "1100123456" not in notes and "1234" not in notes.replace("4 chars", "")
    assert "NOT valid" in " ".join(R.describe_secrets(cid, pin, "NOT-BASE32-189"))


def test_latest_file_written_small_and_current(page):
    nset = R.read_nset(page.read_text())
    R.run(page, FakeDhan(nset), scrip_csv(nset), now())
    lat = json.loads(page.with_name("radesk-latest.json").read_text())
    assert lat["bar_today"] == "2026-11-11" and lat["schema"] == 1
    assert lat["stocks"]["TCS"]["ohlc"]["d"][-1] == "2026-11-11"
    assert len(lat["stocks"]["TCS"]["ohlc"]["c"]) == R.LATEST_BARS
    assert page.with_name("radesk-latest.json").stat().st_size < 600_000


def test_partial_intraday_bar_dropped():
    o = {"d": ["2026-11-10", "2026-11-11"], "c": [1, 2]}
    mid = dt.datetime(2026, 11, 11, 12, 0, tzinfo=R.IST)
    after = dt.datetime(2026, 11, 11, 16, 0, tzinfo=R.IST)
    assert R.drop_partial(o, mid)["d"] == ["2026-11-10"]
    assert R.drop_partial(o, after)["d"][-1] == "2026-11-11"


def test_append_today_from_quote():
    o = {"d": ["2026-11-09"], "o": [100.0], "h": [105.0], "l": [99.0], "c": [104.0], "v": [10.0]}
    after = dt.datetime(2026, 11, 11, 18, 0, tzinfo=R.IST)
    assert not R.append_today(dict(o), (100.0, 105.0, 99.0, 104.0, 5.0), after)      # holiday replay
    assert R.append_today(o, (104.5, 107.0, 103.0, 106.0, 7.0), after)
    assert o["d"][-1] == "2026-11-11" and o["c"][-1] == 106.0 and o["v"][-1] == 7.0
    assert not R.append_today(o, (104.5, 107.0, 103.0, 106.0, 7.0), after)          # already there
    mid = dt.datetime(2026, 11, 12, 11, 0, tzinfo=R.IST)
    assert not R.append_today(o, (110.0, 111.0, 109.0, 110.5, 1.0), mid)            # session not over
