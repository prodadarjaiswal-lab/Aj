import datetime as dt
import json
import math
import random
from pathlib import Path

import portfolio as P
import value_model as V


def _dates(n):
    d0 = dt.date(2020, 1, 1)
    return [(d0 + dt.timedelta(days=k)).isoformat() for k in range(n)]


def _walk(n, seed, drift=0.0003, vol=0.015, start=100.0):
    rnd = random.Random(seed)
    c = [start]
    for _ in range(n - 1):
        c.append(c[-1] * (1 + drift + rnd.gauss(0, vol)))
    return c


def _universe(n_stocks=80, n=1400):
    d = _dates(n)
    nifty = {"d": d, "c": _walk(n, 0)}
    data = {f"S{k}": {"d": d, "c": _walk(n, k + 1)} for k in range(n_stocks)}
    return data, nifty


def test_features_and_flags():
    c = [100.0] * 300 + [150.0] * 200 + [100.0] * 100
    f = V.features(c, 599)
    assert f is not None and abs(f["dd"] - (100 / 150 - 1)) < 1e-9
    s = V.flags(f, 0.0, {"r2y_lo": -1, "r2y_hi": 9, "vol_lo": -1, "mom_hi": 9})
    assert "dd30" in s and "near_lo52" in s


def test_backtest_shape_and_no_false_pass_on_noise():
    data, nifty = _universe()
    res = V.backtest(data, nifty)
    assert set(res["rules"]) == set(V.NAMES)
    for k, r in res["rules"].items():
        assert "tested_up" in r and "tested_weak" in r
        assert r["12m_up"]["dates"] + r["12m_weak"]["dates"] > 0 or k in ("fallen_leader", "recovered", "dd30", "near_lo52")
    assert res["rules"]["lt_winner"]["tested_up"] is False      # the control can never pass


def test_backtest_finds_planted_edge():
    """Stocks that are the calmest 20% get a planted drift; the low-volatility rule must pass in rising markets."""
    n, d = 1400, _dates(1400)
    nifty = {"d": d, "c": _walk(n, 0, drift=0.0006, vol=0.006)}
    data = {}
    for k in range(80):
        calm = k < 16
        data[f"S{k}"] = {"d": d, "c": _walk(n, k + 1, drift=0.0012 if calm else 0.0002, vol=0.006 if calm else 0.02)}
    res = V.backtest(data, nifty)
    assert res["rules"]["lowvol"]["12m_up"]["lift"] > 0
    assert res["rules"]["lowvol"]["tested_up"] is True


def test_data_guard_skips_split():
    data, nifty = _universe(60)
    c = data["S1"]["c"]
    data["S1"]["c"] = c[:700] + [x / 5 for x in c[700:]]      # a 1:5 split in the history
    res = V.backtest(data, nifty)
    assert res["stocks"] == 60


def test_fundamentals_pass_rule():
    nset = {"fund": {"asof": "2026-10", "bt_stk": {
        "B/P": {"12": {"ic": 0.07, "t": 2.05, "hit": 0.7, "n": 32, "start": "2023-03", "end": "2025-10"}},
        "E/P (trailing)": {"12": {"ic": -0.01, "t": -0.3, "n": 32}}},
        "stk": {"A": {"pb": 1.0}, "B": {"pb": 4.0}, "C": {"pb": 2.0}, "D": {"pb": 8.0}, "E": {"pb": 0.5}}}}
    f = V.fundamentals(nset)
    assert f["passed"] == ["B/P"]
    assert f["quintiles"]["E"]["B/P"] == 5 and f["quintiles"]["D"]["B/P"] == 1


def test_today_lists_rules():
    data, nifty = _universe(60)
    t = V.today(data, nifty)
    assert len(t) == 60 and all("on" in v for v in t.values())


# ---------------------------------------------------------------- portfolio fit
def test_normalise_holdings():
    h = P.normalise([{"tradingSymbol": "TCS", "securityId": "11536", "totalQty": 10, "avgCostPrice": 3000},
                     {"tradingSymbol": "ZERO", "totalQty": 0}],
                    [{"symbol": "NVDA", "quantity": "2", "averagePrice": "150"}])
    assert [x["sym"] for x in h] == ["TCS", "NVDA"] and h[1]["mkt"] == "US" and h[1]["qty"] == 2


def test_fit_correlated_vs_diversifier():
    rnd = random.Random(3)
    m = [rnd.gauss(0.0004, 0.01) for _ in range(800)]
    p = [x + rnd.gauss(0, 0.004) for x in m]
    clone = [x + rnd.gauss(0, 0.002) for x in p]                       # nearly the same as the portfolio, more volatile
    clone = [x * 1.8 for x in clone]
    other = [rnd.gauss(0.0004, 0.01) for _ in range(800)]               # uncorrelated
    cfg = dict(P.DEFAULTS)
    held = {"X": 0.5, "Y": 0.5}
    a = P.fit("C", clone, p, m, held, {}, cfg, 0.07, 0.05, 50.0, 1.0)
    b = P.fit("O", other, p, m, held, {}, cfg, 0.07, 0.05, 50.0, 1.0)
    assert a["rho"] > 0.75 and a["v"] == "no"
    assert abs(b["rho"]) < 0.3 and b["v"] in ("suits", "partly")
    assert b["sig"][1] <= b["sig"][0]


def test_fit_caps_and_short_history():
    rnd = random.Random(4)
    m = [rnd.gauss(0, 0.01) for _ in range(800)]
    r = [rnd.gauss(0, 0.01) for _ in range(800)]
    cfg = dict(P.DEFAULTS)
    assert P.fit("S", r[:100], m, m, {}, {}, cfg, 0.07, 0.05, 50, 1.0)["v"] == "no"
    full = P.fit("S", r, m, m, {"S": 0.10}, {}, cfg, 0.07, 0.05, 50, 1.0)          # already at the 10% cap
    assert full["w"] == 0 and full["v"] in ("partly", "no", "suits")
    sec = P.fit("S", r, m, m, {"A": 0.3}, {"S": "IT", "A": "IT"}, cfg, 0.07, 0.05, 50, 1.0)
    assert sec["v"] == "no" and any("sector" in w for w in sec["why"])
    illiq = P.fit("S", r, m, m, {}, {}, cfg, 0.07, 0.05, 0.2, 1.0)
    assert illiq["v"] == "no"


def test_run_without_holdings_uses_proxy(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "config").mkdir()
    data, nifty = _universe(20, 900)
    for o in data.values():
        o["v"] = [1e6] * len(o["c"])

    class NoBook:
        def get(self, path):
            raise RuntimeError("DH-1111 no holdings")
    msg = P.run(NoBook(), data, nifty, tmp_path, {"stocks": {}, "gsec": 7.0})
    out = json.loads((tmp_path / "docs/portfolio.json").read_text())
    assert out["summary"]["proxy"] is True and len(out["fit"]) == 20 and "proxy" in msg
    assert len(out["notes"]) == 2


def test_run_with_holdings(tmp_path):
    (tmp_path / "docs").mkdir()
    data, nifty = _universe(20, 900)

    class Book:
        def get(self, path):
            if path == "/holdings":
                return [{"tradingSymbol": "S1", "totalQty": 10, "avgCostPrice": 90}, {"tradingSymbol": "S2", "totalQty": 5, "avgCostPrice": 90}]
            return {"data": [{"symbol": "NVDA", "quantity": 1, "averagePrice": 150}]}
    P.run(Book(), data, nifty, tmp_path, {"stocks": {}, "gsec": 7.0, "fx": {"inr_now": 90}}, {"NVDA": 160})
    out = json.loads((tmp_path / "docs/portfolio.json").read_text())
    assert out["summary"]["proxy"] is False and out["summary"]["count"] == 3
    assert 0 < out["summary"]["us_share"] < 1 and "US stocks" in out["summary"]["sectors"]
    assert out["fit"]["S1"]["v"] in ("suits", "partly", "no") and out["fit"]["S1"]["c"] and out["check_src"]


def test_bot_desk_command_and_fit_line():
    import bot as B
    b = B.Bot("NSE", state={})
    assert B.DESK_URL in b.handle("desk") and len(B.DESCRIPTION) <= 512
    b.d.pf = {"fit": {"TCS": {"v": "partly", "w": 0.05, "why": ["correlation: 0.6"]}}, "summary": {"proxy": False}}
    line = B.fit_line(b.d, "TCS")
    assert "Partly suits" in line and "5%" in line
    assert B.fit_line(b.d, "NOPE") == ""


def test_pin_links_once(monkeypatch):
    import bot as B
    calls = []

    def fake(method, **kw):
        calls.append(method)
        if method == "getChat":
            return {"pinned_message": {"text": "x", "entities": [{"url": B.DESK_URL}]}} if len(calls) > 3 else {}
        if method == "sendMessage":
            return {"message_id": 7}
        return True
    monkeypatch.setattr(B.T, "call", fake)
    monkeypatch.setattr(B.T, "chat_id", lambda: "1")
    assert B.pin_links() == "links pinned" and calls == ["getChat", "sendMessage", "pinChatMessage"]
    assert B.pin_links() == "links already pinned"


def test_us_weekly_model():
    import us_model as U
    import us_av_import as AV
    csv = "timestamp,open,high,low,close,adjusted close,volume,dividend amount\n" + "\n".join(
        f"2026-{1 + k // 4:02d}-{1 + (k % 4) * 7:02d},10,{11 + k * 0.1:.2f},9,{10 + k * 0.1:.2f},{(10 + k * 0.1) / 2:.4f},100,0" for k in range(44))
    w = AV.parse(csv)
    assert w["c"][-1] == round((10 + 43 * 0.1) / 2, 4) and w["d"] == sorted(w["d"])       # split-adjusted, oldest first
    ext = U.extend_weekly({"d": ["2026-11-06"], "c": [100.0]}, {"2026-11-10": [0, 0, 101.0], "2026-11-13": [0, 0, 103.0], "2026-11-16": [0, 0, 99.0]})
    assert ext["d"] == ["2026-11-06", "2026-11-13", "2026-11-16"] and ext["c"] == [100.0, 103.0, 99.0]
    c = [100 * (1.003 ** k) for k in range(300)]
    t = U.weekly_readout(c, c)
    assert t["vs50"] > 0 and t["vs200"] > 0 and t["rs3"] == 0
    m = U.weekly_mc(c)
    assert m["p_up"] > 0.99 and len(m["fan"]) == 5
    assert U.weekly_var(c)["99"]["hist_1w"] <= 0
