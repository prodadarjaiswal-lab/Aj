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
        assert r["12m_up"]["dates"] + r["12m_weak"]["dates"] > 0 or k in ("fallen_leader", "recovered", "dd30", "near_lo52", "accum", "near_hi", "stack")
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


def test_swing_flags_and_backtest():
    import random as _r
    import auction_bt as AB
    rnd = _r.Random(5)

    def session(start, drift):
        rows, px = [], start
        for k in range(75):
            o = px
            px = px * (1 + drift + rnd.gauss(0, 0.0008))
            rows.append((555 + 5 * k, o, max(o, px) * 1.0004, min(o, px) * 0.9996, px, 1000 + rnd.randint(0, 500)))
        return rows
    prev = session(100, 0)
    up = session(prev[-1][4] * 1.01, 0.0004)
    f = AB.day_flags(up, prev)
    assert "sw_va_up" in f and "sw_va_dn" not in f
    assert AB.day_flags(up[:10], prev) == set()
    days = [f"2026-01-{d:02d}" for d in range(1, 29)] + [f"2026-02-{d:02d}" for d in range(1, 29)] + [f"2026-03-{d:02d}" for d in range(1, 29)]
    nifty, stocks = {}, {f"S{i}": {} for i in range(12)}
    px = 100
    for d in days:
        nifty[d] = session(px, 0)
        px = nifty[d][-1][4]
    for s in stocks:
        p = 100
        for d in days:
            stocks[s][d] = session(p, rnd.choice([-0.0003, 0, 0.0003]))
            p = stocks[s][d][-1][4]
    res = AB.swing_backtest(stocks, nifty)
    assert set(res["signals"]) == set(AB.SWING)
    assert all("tested" in r for r in res["signals"].values())


def test_desk_page_is_light_and_split(tmp_path):
    import desk_page as DP
    r = DP.build(tmp_path / "desk.html")
    files = list((tmp_path / "d").glob("*.json"))
    assert r["bytes"] < 1_500_000, "the page must stay light for phones; per-stock detail belongs in d/*.json"
    assert len(files) == r["detail_files"] > 0
    html = (tmp_path / "desk.html").read_text()
    assert '"chunks":[' in html and "function loadDetail" in html


def test_research_why_move_and_fund():
    import research as RS
    f = RS.compact_fund({"data": {"CO": {"EPS": 10, "SECTOR": "IT"}, "RATIOS": {"PE_RATIO": 20, "PE_TO_SECTOR_PE": 0.7, "ROCE": 25},
                                  "SHP": {"FII_HOLDING": 20, "CHANGE_IN_FII_HOLDING": -1.2}}})
    assert f["pe"] == 20 and f["pe_sec"] == 0.7 and f["d_fii"] == -1.2
    nifty = [100.0] * 100 + [100 * (1 - 0.001 * k) for k in range(64)]          # market down ~6%
    stock = [100.0] * 100 + [100 * (1 - 0.004 * k) for k in range(64)]          # stock down ~25%
    w = RS.why_move("X", stock, nifty, [-0.07, -0.06, -0.05], 1.0, f, [["2026-08-01", 25, 12, 20, 0, 50, 21, 10], ["2026-11-01", 20, 10, 20, 0, 50, 20, 10]])
    assert w["driver"] == "stock" and w["total"] < -0.2
    assert any("FIIs cut" in n for n in w["notes"]) and any("EPS down" in n for n in w["notes"])
    assert RS.why_move("X", stock[:10], nifty, [], 1.0, {}, None) == {}


def test_journal_review_finds_followups_and_blind_spots():
    import datetime as _dt
    import daily_digest as DD
    d = (_dt.date.today() - _dt.timedelta(days=5)).isoformat()
    journal = [{"t": d + " 10:00", "cmd": "trade", "sym": "AAA", "price": 100.0, "said": ""},
               {"t": d + " 11:00", "cmd": "value", "sym": "BBB", "price": 50.0, "said": ""}]
    rs = {"asof": "2026-11-13", "side": "up", "tested": {"tech": ["flag"], "inv": ["recovered"]},
          "stocks": {"AAA": {"last": 88.0, "setups": ["flag"], "inv": [], "warn": [], "score": 2, "r3m": -0.2, "rs3": -0.1, "ind": "IT"},
                     "BBB": {"last": 50.5, "setups": [], "inv": [], "warn": [], "score": 0, "r3m": -0.15, "rs3": -0.05, "ind": "IT"},
                     "CCC": {"last": 10.0, "setups": ["flag"], "inv": ["recovered"], "warn": [], "score": 6, "ind": "Metals",
                             "ev": [["tech", "flag"], ["inv", "recovered"]]},
                     "DDD": {"last": 10.0, "setups": [], "inv": [], "warn": [], "score": 5, "ind": "Metals", "ev": [["inv", "recovered"]]}}}
    rv = DD.review(journal, rs, {"rows": []})
    assert rv["stocks"] == 2 and rv["looked"][0]["s"] in ("AAA", "BBB")
    f = {x["s"]: x["why"] for x in rv["follow"]}
    assert "AAA" in f and any("tested signal" in w for w in f["AAA"]) and any("-12%" in w for w in f["AAA"])
    assert [b["s"] for b in rv["blind"]] == ["CCC", "DDD"] and rv["blind_ind"][0][0] == "Metals"
    assert rv["habit"]
    import telegram as T
    txt = DD.digest_text(rv, rs, "https://x")
    assert "Follow up" in txt and "CCC" in txt and T.esc("<") == "&lt;"


def test_merge_journal_keeps_both_writers():
    import bot as B
    a = {"alerts": [1], "journal": [{"t": "2026-11-14 10:00", "cmd": "trade", "sym": "TCS"}]}
    b = {"alerts": [], "journal": [{"t": "2026-11-13 09:00", "cmd": "value", "sym": "INFY"}, {"t": "2026-11-14 10:00", "cmd": "trade", "sym": "TCS"}]}
    m = B.merge_journal(a, b)
    assert [x["sym"] for x in m["journal"]] == ["INFY", "TCS"] and m["alerts"] == [1]
    assert B.merge_journal(a, {}) is a


def test_score_band_tracking():
    import track as TR
    rs = {"asof": "2026-11-16", "stocks": {"A": {"score": 6.5, "turnover_cr": 50}, "B": {"score": 4, "turnover_cr": 50},
                                           "C": {"score": 2, "turnover_cr": 50}, "D": {"score": 0, "turnover_cr": 50},
                                           "E": {"score": 8, "turnover_cr": 1}}}
    log = {"picks": []}
    picks = TR.score_picks(rs, log)
    kinds = {(p["kind"], p["sym"]) for p in picks}
    assert kinds == {("score6", "A"), ("score4", "B"), ("score2", "C"), ("score0", "D")}          # E is too illiquid
    log = TR.update(log, "2026-11-16", picks, {"A": 100, "B": 100, "C": 100, "D": 100}, {}, 1000)
    assert TR.score_picks(rs, log) == []                                                            # still open: not logged twice
    for k in range(21):
        log = TR.update(log, f"d{k}", [], {"A": 100 + k, "B": 100, "C": 100, "D": 100 - k}, {}, 1000)
    sm = TR.summary(log)
    assert sm["score6"]["avg21"] > 0 > sm["score0"]["avg21"] and sm["score6"]["beat10"] == 1.0
    assert len(TR.score_picks(rs, log)) == 4                                                        # closed: eligible again


def test_nse_feed_parsers():
    import datetime as _dt
    import nse_feeds as NF
    today = _dt.date(2026, 11, 16)
    ev = NF.parse_events([{"symbol": "TCS", "date": "20-Nov-2026", "purpose": "Financial Results"},
                          {"symbol": "TCS", "date": "20-Jan-2027", "purpose": "far"}, {"symbol": "ZZ", "date": "18-Nov-2026", "purpose": "x"},
                          {"symbol": "TCS", "date": "bad"}], {"TCS"}, today)
    assert ev == {"TCS": [{"d": "2026-11-20", "p": "Financial Results"}]}
    fl = NF.parse_filings([{"symbol": "TCS", "an_dt": "14-Nov-2026 17:12:00", "desc": "Updates", "attchmntText": "Call schedule"},
                           {"symbol": "TCS", "an_dt": None, "exchdisstime": None}], {"TCS"})
    assert fl["TCS"][0]["t"] == "2026-11-14 17:12" and "Call schedule" in fl["TCS"][0]["title"]
    fi = NF.parse_fii([{"category": "FII/FPI *", "date": "13-Nov-2026", "buyValue": "100.5", "sellValue": "90", "netValue": "10.5"},
                       {"category": "DII **", "date": "13-Nov-2026", "buyValue": "50", "sellValue": "60", "netValue": "-10"}])
    assert fi["2026-11-13"]["FII"]["net"] == 10.5 and fi["2026-11-13"]["DII"]["net"] == -10
