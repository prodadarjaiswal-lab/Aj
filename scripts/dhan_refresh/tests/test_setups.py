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
