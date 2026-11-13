import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bot as B  # noqa: E402
import telegram as T  # noqa: E402

ROWS = [
    {"s": "AAA", "name": "Alpha Ltd.", "sid": 1, "setup": "volbreak", "status": "lead", "score": 90, "rank": 1, "last": 104.0, "trig": 102.0, "fail": 95.0},
    {"s": "BBB", "name": "Beta Ltd.", "sid": 2, "setup": None, "status": "weak", "score": 10, "rank": 2, "last": 50.0},
]
NSET = {"stocks": {"AAA": {"val": {"gap": -0.05, "g_impl": 0.02, "g3": 0.07, "pe": 15, "pe_med": 20, "beta": 1.2}, "signal": "Value"}}}
OPTS = {"date": "2026-11-13", "rows": {"AAA": {"spot": 104, "expiry": "2026-11-23", "straddle": 4.0, "exp_move": 0.04, "iv_put": 30,
                                                "pcr_oi": 0.8, "call_wall": 110, "put_wall": 100}}}


def bot(market="NSE"):
    return B.Bot(market, B.Data({"asof": "2026-11-13", "rows": ROWS}, NSET, OPTS), state={})


def test_verdicts_and_top():
    b = bot()
    assert "Buy candidate" in b.handle("AAA") and "Stop below ₹95.0" in b.handle("/aaa")
    assert "Avoid for a trade" in b.handle("trade BBB")
    assert "Reasonable to accumulate" in b.handle("value AAA")
    assert "covers the Nifty 50" in b.handle("value BBB")
    assert "1. <b>AAA</b>" in b.handle("top")
    h = b.handle("hedge AAA")
    assert "exit below ₹95.0" in h and "₹120,000" in h and "1.9%" in h
    assert "didn't understand" in b.handle("what is life")


def test_price_uses_live_quote():
    b = bot()
    assert "at the 2026-11-13 close" in b.handle("price AAA")
    b.quotes["AAA"] = (105.5, 104.0)
    assert "₹105.50 (+1.44%)" in b.handle("price aaa")


def test_alerts_add_list_fire_once_remove():
    b = bot()
    assert "Done" in b.handle("alert AAA above 106")
    assert "I don't know" in b.handle("alert ZZZ above 5")
    assert "US session" in b.handle("alert NVDA below 150 us")
    assert "1. AAA above ₹106.00" in b.handle("my alerts") and "2. NVDA below $150.00" in b.handle("my alerts")
    b.quotes["AAA"] = (105.0, 104.0)
    assert b.check("10:00") == []
    b.quotes["AAA"] = (106.5, 104.0)
    m = b.check("10:05")
    assert len(m) == 1 and "AAA" in m[0] and b.check("10:06") == []
    assert [a["sym"] for a in b.state["alerts"]] == ["NVDA"]          # US alert waits for the US job
    assert "Removed: NVDA" in b.handle("remove 1")


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
    monkeypatch.setattr(B, "save_state", lambda st: None)
    b = bot()
    assert b.poll() == 1 and len(sent) == 1 and b.state["offset"] == 7
    assert b.poll() == 0
