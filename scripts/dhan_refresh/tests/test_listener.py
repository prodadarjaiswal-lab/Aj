import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bot as B  # noqa: E402
import listener as L  # noqa: E402

IST = L.IST
ROWS = [{"s": "AAA", "name": "Alpha", "sid": 1, "last": 100.0, "status": "lead"}]


def mk():
    return B.Bot("ANY", B.Data({"asof": "2026-11-13", "rows": ROWS}, {"idx": {}}, {"rows": {}}, {"stocks": {}}, {"signals": {}}), state={})


def test_closed_market_reply_says_why(monkeypatch):
    monkeypatch.setattr(L, "_show", lambda br, p: None)
    b = mk()
    L.live_quotes(b, dt.datetime(2026, 11, 14, 11, 0, tzinfo=IST))        # Saturday
    r = b.handle("price AAA")
    assert "Dhan close of 2026-11-13" in r and "weekend" in r


def test_fresh_live_and_us_quotes(monkeypatch):
    now = dt.datetime(2026, 11, 16, 11, 0, 30, tzinfo=IST)
    us_t = dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
    data = {("live", "live.json"): {"t": "2026-11-16 11:00:00", "q": {"NSE_EQ": {"1": [101.0, 100, 102, 99, 100.0]}}},
            ("us-watch", "state.json"): {"quotes": {"NVDA": {"price": 165.0, "prev": 160.0, "t": us_t}}}}
    monkeypatch.setattr(L, "_show", lambda br, p: data.get((br, p)))
    b = mk()
    L.live_quotes(b, now)
    assert "₹101.00 (+1.00%), live from Dhan" in b.handle("price AAA")
    assert "$165.00 (+3.12%), live from Dhan" in b.handle("price NVDA")


def test_stale_live_file_is_not_used(monkeypatch):
    data = {("live", "live.json"): {"t": "2026-11-16 10:00:00", "q": {"NSE_EQ": {"1": [101.0, 100, 102, 99, 100.0]}}}}
    monkeypatch.setattr(L, "_show", lambda br, p: data.get((br, p)))
    b = mk()
    L.live_quotes(b, dt.datetime(2026, 11, 16, 11, 0, tzinfo=IST))
    r = b.handle("price AAA")
    assert "Dhan close" in r and "feed not running" in r
