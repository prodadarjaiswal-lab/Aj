import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "dhan_refresh"))
import refresh as R  # noqa: E402
import setups as SU  # noqa: E402


def test_breakout_and_no_lookahead():
    n = 300
    c = [100 + 0.05 * i for i in range(n)]
    c[-1] = c[-2] * 1.05
    h = [x * 1.002 for x in c]
    l = [x * 0.998 for x in c]
    nc = [100.0] * n
    S = SU.Series(c, h, l, nc)
    assert S.tag(n - 1) == "breakout"
    c2 = c[:-1] + [c[-2] * 0.5]            # changing the future bar must not change yesterday's tag
    assert SU.Series(c2, h, l, nc).tag(n - 2) == S.tag(n - 2)


def test_backtest_runs_on_page_data():
    nset = R.read_nset((ROOT / "docs" / "ra-desk.html").read_text())
    stocks = {s: x["ohlc"] for s, x in nset["stocks"].items()}
    res = SU.backtest(stocks, nset["idx"]["Nifty 50"])
    assert set(res["setups"]) == set(SU.TAGS) and res["base"]["n"] > 100


def test_n500_build_ranks_and_matches_universe():
    import n500
    nset = R.read_nset((ROOT / "docs" / "ra-desk.html").read_text())
    uni = [{"s": s, "name": x["name"], "ind": x["sector"]} for s, x in nset["stocks"].items()]
    series = {s: x["ohlc"] for s, x in nset["stocks"].items()}
    out = n500.build(uni, series, nset["idx"]["Nifty 50"])
    assert out["n"] >= 45 and out["rows"][0]["rank"] == 1 and len(out["rows"][0]["sp"]) == 40
    assert {r["status"] for r in out["rows"]} <= {"lead", "improve", "neutral", "fade", "weak"}
    assert all(("trig" in r) == ("setup" in r) for r in out["rows"])


def test_parse_list():
    import n500
    rows = n500.parse_list("Company Name,Industry,Symbol,Series,ISIN Code\nA Ltd,IT,AAA,EQ,X\nB Ltd,Banks,BBB,EQ,Y\n")
    assert [r["s"] for r in rows] == ["AAA", "BBB"] and rows[0]["ind"] == "IT"
