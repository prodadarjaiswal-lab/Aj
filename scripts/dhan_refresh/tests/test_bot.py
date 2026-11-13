import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bot as B  # noqa: E402
import telegram as T  # noqa: E402

ROWS = [
    {"s": "AAA", "name": "Alpha Ltd.", "ind": "Information Technology", "sid": 1, "status": "lead", "score": 90, "rank": 1,
     "last": 104.0, "r21": -0.10, "vs50": 0.1, "vs200": 0.2, "rs3": 0.1, "rsi": 60, "fail": 95.0},
    {"s": "BBB", "name": "Beta Ltd.", "ind": "Information Technology", "sid": 2, "status": "weak", "score": 10, "rank": 2, "last": 50.0, "r21": -0.08},
    {"s": "CCC", "name": "Gamma Ltd.", "ind": "Information Technology", "sid": 3, "status": "neutral", "score": 50, "rank": 3, "last": 20.0, "r21": -0.07},
    {"s": "DDD", "name": "Delta Ltd.", "ind": "Information Technology", "sid": 4, "status": "neutral", "score": 40, "rank": 4, "last": 30.0, "r21": -0.06},
]
NIFTY = {"c": [100.0] * 199 + [110.0, 112.0], "d": ["x"] * 201}
NSET = {"stocks": {"AAA": {"val": {"gap": -0.05, "g_impl": 0.02, "g3": 0.07, "pe": 15, "pe_med": 20, "fair_at_g3": 130, "beta": 1.2}}},
        "idx": {"Nifty 50": NIFTY}}
OPTS = {"date": "2026-11-13", "rows": {"AAA": {"spot": 104, "expiry": "2026-11-23", "straddle": 4.0, "exp_move": 0.04, "iv_put": 30,
                                                "pcr_oi": 0.8, "call_wall": 110, "put_wall": 100}}}
TECH = {"stocks": {"AAA": {"d": "2026-11-13", "c": 104.0, "atr": 2.0, "on": ["hi52v"], "new": ["hi52v"]},
                   "BBB": {"d": "2026-11-13", "c": 50.0, "atr": 1.0, "on": [], "new": []}}}
MODEL = {"signals": {"hi52v": {"tested": True, "out": {"up": {"n": 1046, "hit10": 0.5468, "x10": 0.01573}}},
                     "nr7": {"tested": False}}, "base": {"out": {"up": {"x10": 0.00194}}}}


@pytest.fixture(autouse=True)
def no_git(monkeypatch):
    """Tests must never push bot state to the real repository."""
    monkeypatch.setattr(B, "save_state", lambda st: None)


def bot(market="NSE"):
    return B.Bot(market, B.Data({"asof": "2026-11-13", "rows": ROWS}, NSET, OPTS, TECH, MODEL), state={})


def test_trade_verdicts_use_only_tested_signals():
    b = bot()
    t = b.handle("AAA")
    assert "Buy candidate" in t and "52-week" in t and "1,046 cases" in t and "55%" in t
    assert "Stop ₹100.0" in t and "target ₹110.0" in t
    a = b.handle("bbb")
    assert "Avoid" in a and "Stop" not in a                     # no trade levels on an avoid
    assert "Not a command" in b.handle("what is life")


def test_top_lists_tested_signals_on_leaders():
    t = bot().handle("top")
    assert "1. <b>AAA</b>" in t and "BBB" not in t


def test_value_and_hedge_order():
    b = bot()
    assert "Reasonable to accumulate" in b.handle("value AAA") and "+25%" in b.handle("value AAA")
    assert "Nifty 50 stocks only" in b.handle("value BBB")
    h = b.handle("hedge AAA")
    i1, i2, i3 = h.index("1. Across asset classes"), h.index("2. Market, sector"), h.index("3. Stop-loss")
    assert i1 < i2 < i3
    assert "industry -7.0%" in h and "sector or market wide" in h        # stock -10%, industry -7%: not company-specific
    assert "1.20x the position" in h and "about 1.9%" in h and "Stop at ₹100.0" in h


def test_hedge_flags_adverse_company_news():
    nset = {"stocks": {"AAA": {"val": {"beta": 1.2}, "news": [{"time": "2026-11-12 10:00", "title": "Alpha CEO resigns amid probe"}],
                               "filings": [{"time": "2026-11-01 10:00", "title": "Board meeting"}]}}, "idx": {"Nifty 50": NIFTY}}
    b = B.Bot("NSE", B.Data({"asof": "2026-11-13", "rows": ROWS}, nset, OPTS, TECH, MODEL), state={})
    h = b.handle("hedge AAA")
    assert "Possibly adverse company news" in h and "CEO resigns" in h and "company-specific" in h
    h2 = bot().handle("hedge BBB")
    assert "Nifty 50 stocks only" in h2


def test_price_live_and_close():
    b = bot()
    assert "2026-11-13 close" in b.handle("price AAA")
    b.quotes["AAA"] = (105.5, 104.0)
    assert "₹105.50 (+1.44%), live from Dhan" in b.handle("price aaa")


def test_alerts_and_journal():
    b = bot()
    assert "Alert set" in b.handle("alert AAA above 106")
    assert "not a Nifty 500" in b.handle("alert ZZZ above 5")
    assert "Alert set" in b.handle("alert NVDA below 150 us")
    lst = b.handle("alert")
    assert "1. AAA above ₹106.00" in lst and "2. NVDA below $150.00" in lst
    b.quotes["AAA"] = (106.5, 104.0)
    m = b.check("10:05")
    assert len(m) == 1 and b.check("10:06") == []
    assert [a["sym"] for a in b.state["alerts"]] == ["NVDA"]
    assert "Removed: NVDA" in b.handle("alert remove 1")
    b.handle("AAA")
    b.handle("hedge AAA")
    j = b.state["journal"]
    assert [x["cmd"] for x in j] == ["trade", "hedge"] and j[0]["sym"] == "AAA" and "Buy candidate" in j[0]["said"]


def test_poll_answers_only_the_owner(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "7")
    sent = []
    ups = [{"update_id": 5, "message": {"chat": {"id": 999}, "text": "top"}},
           {"update_id": 6, "message": {"chat": {"id": 7}, "text": "top"}}]

    def call(method, **p):
        if method == "getUpdates":
            return ups if p["offset"] <= 6 else []
        sent.append(p["text"])
    monkeypatch.setattr(T, "call", call)
    b = bot()
    assert b.poll() == 1 and len(sent) == 1 and b.state["offset"] == 7
    assert b.poll() == 0
