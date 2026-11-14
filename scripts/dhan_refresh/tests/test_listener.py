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


def test_flow_uses_live_order_flow(monkeypatch):
    now = dt.datetime(2026, 11, 16, 11, 0, 30, tzinfo=IST)
    f = {"prints": 40, "buy_vol": 6000, "sell_vol": 4000, "delta": 2000, "cum_delta": 2000, "buy_share": 0.6,
         "large_prints": [["10:58:05", 101.0, 900.0, 1]], "stacked": [[100.5, 100.8, "buyers"]], "pending_ratio": 1.3,
         "events": [["10:59:00", "absorption: sellers absorbed", 100.9, 800, -1]], "trapped": "buyers trapped above 101.2"}
    data = {("live", "live.json"): {"t": "2026-11-16 11:00:00", "q": {"NSE_EQ": {"1": [101.0, 100, 102, 99, 100.0]}}},
            ("live", "flow.json"): {"d": "2026-11-16", "t": "11:00:00", "s": {"AAA": f}}}
    monkeypatch.setattr(L, "_show", lambda br, p: data.get((br, p)))
    b = mk()
    L.live_quotes(b, now)
    r = b.handle("flow AAA")
    assert "Live order flow" in r and "Delta 2,000" in r and "buyers 100.5 to 100.8" in r and "sellers absorbed at 100.9" in r and "Trapped" in r
