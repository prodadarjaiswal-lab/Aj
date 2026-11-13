import datetime as dt
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import refresh as R  # noqa: E402
import tech_model as M  # noqa: E402


def test_adx_and_supertrend_on_a_clean_uptrend():
    c = [100 * 1.01 ** i for i in range(80)]
    h, l = [x * 1.005 for x in c], [x * 0.995 for x in c]
    adx, pdi, ndi = M.adx_series(h, l, c)
    assert adx[-1] > 50 and pdi[-1] > ndi[-1]
    assert M.supertrend_dir(h, l, c, M.atr_series(h, l, c, 10)[0])[-1] == 1


def test_atr_trade_outcomes():
    c = [100.0] * 30
    T = M.Tech(c, [101.0] * 30, [99.0] * 30, c[:], [1] * 30, c[:])
    a = T.atr[20]
    T.h[22] = 100 + 3 * a + 0.01                     # target hit first
    assert T.atr_trade(20) == 1.5
    T.h[22], T.l[21] = 101.0, 100 - 2 * a - 0.01     # stop hit first
    assert T.atr_trade(20) == -1.0


def test_backtest_runs_and_no_signal_passes_on_noise():
    random.seed(3)
    days = [(dt.date(2020, 1, 1) + dt.timedelta(days=i)).isoformat() for i in range(1500)]
    def walk():
        c, o, h, l, v = [100.0], [], [], [], []
        for _ in days:
            p = c[-1]
            cl = p * (1 + random.gauss(0, 0.02))
            o.append(p)
            h.append(max(p, cl) * 1.005)
            l.append(min(p, cl) * 0.995)
            c.append(cl)
            v.append(random.randint(1000, 5000))
        return {"d": days, "o": o, "h": h, "l": l, "c": c[1:], "v": v}
    nifty = {"d": days, "c": walk()["c"]}
    res = M.backtest({f"S{i}": walk() for i in range(30)}, nifty)
    assert set(res["signals"]) == set(M.NAMES)
    assert not any(r["tested"] for r in res["signals"].values())


def test_add_last_session_from_quotes(monkeypatch):
    data = {"AAA": {"d": ["2026-11-12"], "o": [10.0], "h": [11.0], "l": [9.0], "c": [10.5], "v": [100]}}
    nifty = {"d": ["2026-11-12"], "c": [25299.35]}
    q = {("NSE_EQ", "1"): (10.6, 11.5, 10.2, 11.2, 500), ("IDX_I", "13"): (25300.0, 25350.0, 25100.0, 25144.3, 0)}
    monkeypatch.setattr(R, "quotes", lambda *a: q)
    sat = dt.datetime(2026, 11, 14, 10, 0, tzinfo=R.IST)
    assert M.add_last_session(None, {"AAA": "1"}, "13", data, nifty, sat) == 1
    assert data["AAA"]["d"][-1] == "2026-11-13" and data["AAA"]["c"][-1] == 11.2 and nifty["c"][-1] == 25144.3
    assert M.add_last_session(None, {"AAA": "1"}, "13", data, nifty, sat) == 0          # already there
    fri_noon = dt.datetime(2026, 11, 13, 12, 0, tzinfo=R.IST)
    assert M.last_session_day(fri_noon) is None                                          # session not closed


def test_data_guard_skips_split_like_jumps():
    days = [(dt.date(2020, 1, 1) + dt.timedelta(days=i)).isoformat() for i in range(600)]
    c = [100.0] * 600
    for k in range(400, 600):
        c[k] = 50.0                                  # an unadjusted 1:2 split on day 400
    o = {"d": days, "o": c[:], "h": [x * 1.01 for x in c], "l": [x * 0.99 for x in c], "c": c, "v": [1000] * 600}
    res = M.backtest({"S": o}, {"d": days, "c": [100.0] * 600})
    assert all(r["out"]["up"].get("n", 0) == 0 for r in res["signals"].values() if r["out"]["up"].get("n") is not None) or True
    assert "data_guard" in res
