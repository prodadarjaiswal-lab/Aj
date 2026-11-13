import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import alerts as AL  # noqa: E402
import telegram as T  # noqa: E402

ROWS = [
    {"s": "AAA", "sid": 1, "setup": "volbreak", "status": "lead", "score": 90, "last": 100.0, "trig": 102.0, "fail": 95.0, "r1": 0.01},
    {"s": "BBB", "sid": 2, "setup": "pullback", "status": "improve", "score": 80, "last": 50.0, "trig": 51.0, "fail": 48.0, "r1": -0.01},
    {"s": "CCC", "sid": 3, "setup": "turn", "status": "lead", "score": 95, "last": 10.0, "trig": 11.0, "fail": 9.0, "r1": 0.02},
    {"s": "DDD", "sid": 4, "setup": "volbreak", "status": "weak", "score": 99, "last": 20.0, "trig": 21.0, "fail": 19.0, "r1": 0.0},
]
BOARD = {"asof": "2026-11-13", "rows": ROWS}
IDX = {"13": "Nifty 50"}


def q(prices, nifty=(25000, 25000)):
    return {"NSE_EQ": {str(s): [p, p, p, p, c] for s, (p, c) in prices.items()},
            "IDX_I": {"13": [nifty[0], nifty[1], nifty[0], nifty[0], nifty[1]]}}


def test_picks_only_tested_edge_on_leaders():
    assert [r["s"] for r in AL.picks(ROWS)] == ["AAA", "BBB"]
    assert [r["s"] for r in AL.watching(ROWS)] == ["CCC"]


def test_trigger_fires_once_and_fail_level():
    a = AL.Alerts(IDX, [], BOARD)
    assert a.check(q({1: (101, 100)}), "09:20") == []
    m = a.check(q({1: (103, 100)}), "09:25")
    assert len(m) == 1 and "AAA" in m[0] and "trigger" in m[0]
    assert a.check(q({1: (104, 100)}), "09:30") == []          # no repeat
    m = a.check(q({2: (47, 50)}), "10:00")
    assert len(m) == 1 and "fail level" in m[0]          # one message per stock per check


def test_restart_does_not_repeat():
    a = AL.Alerts(IDX, ["trig:1"], BOARD)
    assert a.check(q({1: (102.5, 100)}), "11:00") == []


def test_nifty_move_and_after_close_base():
    a = AL.Alerts(IDX, [], BOARD)
    assert a.check(q({}, (25300, 25000)), "10:00")[0].startswith("📈 Nifty 50 +1.2%")
    # after 15:30 Dhan's close field becomes today's close; the summary must still use yesterday's
    s = AL.close_summary(q({1: (103, 103)}, (25300, 25300)), IDX, a.prev | {"NSE_EQ:1": 100.0}, BOARD)
    assert "Nifty 50 25,300 (+1.20%)" in s and "AAA +3.0%" in s and "triggered" in s


def test_already_broken_out_alerts_on_retest_not_open():
    b = {"rows": [dict(ROWS[0], last=104.0)]}
    a = AL.Alerts(IDX, [], b)
    assert a.check(q({1: (105, 104)}), "09:16") == []
    m = a.check(q({1: (102.5, 104)}), "10:00")
    assert len(m) == 1 and "back at its breakout level" in m[0]


def test_brief_text():
    nset = {"idx": {"Nifty 50": {"c": [24000.0] * 49 + [25000.0, 25144.3]}, "India VIX": {"c": [12.3]}}}
    t = AL.morning_brief(nset, BOARD)
    assert "Nifty 50 25,144 (+0.6%)" in t and "<b>AAA</b> Volume breakout: ₹100.0, alert above ₹102.0" in t and "CCC" in t
    assert "<b>DDD</b>" not in t       # weak stocks are not picks


def test_send_splits_long_messages(monkeypatch):
    sent = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setattr(T, "call", lambda m, **p: sent.append(p["text"]))
    assert T.send("\n".join(["line " * 20] * 100))
    assert len(sent) == 3 and all(len(s) <= 4096 for s in sent)


def test_send_never_raises(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(T, "call", boom)
    assert T.send("hi") is False
