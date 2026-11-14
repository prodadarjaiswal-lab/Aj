import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import flow as F  # noqa: E402


def q(ltp, vol, bid, ask, bq=1000, aq=1000, tb=50000, ts=40000):
    return {"last_price": ltp, "volume": vol, "buy_quantity": tb, "sell_quantity": ts,
            "depth": {"buy": [{"price": bid, "quantity": bq}], "sell": [{"price": ask, "quantity": aq}]}}


def test_aggressor_side_and_delta():
    f = F.Flow()
    f.update("10:00:00", q(100.0, 1000, 99.9, 100.1))
    f.update("10:00:05", q(100.1, 1500, 100.0, 100.2))       # traded at the previous ask: buyers, +500
    f.update("10:00:10", q(100.0, 1800, 99.9, 100.1))        # at the previous bid: sellers, -300
    f.update("10:00:15", q(100.05, 1900, 99.95, 100.1))      # between: uptick -> buyers, +100
    s = f.summary()
    assert [x[3] for x in f.tape] == [1, -1, 1] and s["delta"] == 300 and s["cum_delta"] == 300
    assert s["buy_vol"] == 600 and s["sell_vol"] == 300 and s["pending_ratio"] == 1.25


def test_large_print_absorption_and_footprint_stack():
    f = F.Flow()
    f.update("10:00:00", q(100.0, 0, 99.9, 100.1))
    v = 0
    for i in range(30):                                      # small prints, alternating
        v += 100
        f.update(f"10:{i // 12:02d}:{(i * 5) % 60:02d}", q(100.0 + (0.1 if i % 2 else 0), v, 99.9, 100.1))
    v += 2000
    f.update("10:03:00", q(100.1, v, 99.9, 100.1))           # 2,000 at the same price as the last print: absorption
    assert any("absorption" in e[1] for e in f.events)
    g = F.Flow()
    g.update("10:00:00", q(100.0, 0, 99.9, 100.1))
    vol = 0
    for p in (100.1, 100.2, 100.3, 100.4):                   # buyers lift the ask at four rising levels
        for _ in range(3):
            vol += 500
            g.update("10:00:05", q(p, vol, p - 0.1, p))
    st_ = g.summary()
    assert st_["stacked"] and st_["stacked"][0][2] == "buyers"


def test_state_roundtrip():
    f = F.Flow()
    f.update("10:00:00", q(100.0, 1000, 99.9, 100.1))
    f.update("10:00:05", q(100.1, 1500, 100.0, 100.2))
    g = F.Flow(f.state())
    g.update("10:00:10", q(100.2, 1700, 100.1, 100.3))
    assert g.summary()["cum_delta"] == 700
