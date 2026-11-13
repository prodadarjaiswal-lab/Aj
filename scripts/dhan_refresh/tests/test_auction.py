import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import auction as A  # noqa: E402

O = A.OPEN_MIN


def test_volume_profile_poc_and_value_area():
    # 100 units at 100-101, 600 at 101-102, 100 at 102-103 (tick 1)
    rows = [(O, 100.5, 100.9, 100.1, 100.5, 100), (O + 1, 101.5, 101.9, 101.1, 101.5, 600), (O + 2, 102.5, 102.9, 102.1, 102.5, 100)]
    vp = A.volume_profile(rows, 1.0)
    assert vp["poc"] == 101.5 and vp["hist"] == {100.5: 100, 101.5: 600, 102.5: 100}
    assert vp["val"] == 101.0 and vp["vah"] == 102.0            # 600 of 800 is already 75% >= 70%
    spread = A.volume_profile([(O, 100, 102.9, 100.0, 101, 300)], 1.0)      # one bar over 3 bins: 100 each
    assert spread["hist"] == {100.5: 100, 101.5: 100, 102.5: 100}


def test_market_profile_ib_singles_and_tails():
    rows = []
    def bracket(i, lo, hi):
        rows.append((O + 30 * i, lo, hi, lo, hi, 10))
    bracket(0, 100.0, 102.9)       # A: 100-102
    bracket(1, 101.0, 103.9)       # B: 101-103   (IB = A+B: 100.0 to 103.9)
    bracket(2, 106.0, 108.9)       # C jumps: 104-105 never traded
    bracket(3, 107.0, 109.9)       # D
    bracket(4, 104.0, 107.9)       # E fills 104-105 once -> single prints inside the range
    mp = A.market_profile(rows, 1.0)
    assert mp["ib_high"] == 103.9 and mp["ib_low"] == 100.0 and mp["ib_extension"] == "up"
    assert mp["single_prints"] == [[103.0, 106.0]]              # 103 (B only), 104-105 (E only)
    assert mp["poor_low"] and mp["poor_high"]                   # one single print at each extreme is not a tail
    assert mp["tpo_poc"] in (107.5, 101.5, 102.5)


def test_vwap_bands_and_reclaim():
    rows = [(O, 100, 100, 100, 100, 100), (O + 1, 110, 110, 110, 110, 300)]
    v = A.vwap(rows)
    assert v["vwap"] == 107.5 and v["sd"] == 4.33 and v["up1"] == 111.83 and v["state"] == "above"
    r = A.vwap([(O, 100, 100, 100, 100, 100), (O + 1, 95, 95, 95, 95, 100), (O + 2, 110, 110, 110, 110, 300)])
    assert r["state"] == "reclaimed" and r["minutes_on_side"] == 1
    lost = A.vwap([(O, 100, 100, 100, 100, 100), (O + 1, 110, 110, 110, 110, 100), (O + 2, 90, 90, 90, 90, 100)])
    assert lost["state"] == "lost"
    assert A.vwap(rows, anchor_minute=O + 1)["vwap"] == 110.0


def test_delta_estimate_sign():
    up = A.delta_est([(O, 100, 101, 100, 101, 1000)])            # closed at the high: all buying
    dn = A.delta_est([(O, 100, 101, 100, 100, 1000)])            # closed at the low: all selling
    assert up["cum_delta_est"] == 1000 and up["buy_share_est"] == 1.0 and dn["cum_delta_est"] == -1000


def test_gex_sign_flip_and_walls():
    call, put = {"oi": 1000, "iv": 15}, {"oi": 1000, "iv": 15}
    rows = [(k, {"oi": 5000 if k == 110 else 100, "iv": 15}, {"oi": 5000 if k == 90 else 100, "iv": 15}) for k in range(80, 121, 5)]
    g = A.gex(100.0, rows, 7)
    assert g["call_gamma_strikes"][0] == 110 and g["put_gamma_strikes"][0] == 90
    assert 90 < g["gamma_flip"] < 110 and abs(g["net_gex"]) < 5e4          # symmetric book: net near zero at spot
    hi, lo = A.gex(108.0, rows, 7), A.gex(92.0, rows, 7)
    assert hi["net_gex"] > 0 and "positive" in hi["regime"] and lo["net_gex"] < 0 and "negative" in lo["regime"]
    assert A.gex(100.0, rows[:3], 7)["net_gex"] is None                     # too thin: no number invented


def test_analyse_two_sessions_auction_read():
    def day(d, base):
        t0 = int(dt.datetime(2026, 11, d, 9, 15, tzinfo=A.IST).timestamp())
        t = [t0 + 60 * i for i in range(375)]
        px = [base + (i % 20) * 0.1 for i in range(375)]
        return t, px
    t1, p1 = day(12, 100.0)
    t2, p2 = day(13, 110.0)                                       # gaps above and stays there
    bars = {"t": t1 + t2, "o": p1 + p2, "h": [x + 0.2 for x in p1 + p2], "l": [x - 0.2 for x in p1 + p2], "c": p1 + p2, "v": [100] * 750}
    a = A.analyse(bars)
    assert a["date"] == "2026-11-13" and a["prev"]["date"] == "2026-11-12"
    assert a["auction"]["open_vs_prev_value"] == "above value" and "acceptance above" in a["auction"]["read"]
    assert a["prev"]["val"] <= 101 <= a["prev"]["vah"] and a["vp"]["val"] >= 109 and a["composite"]["days"] == 2


def test_index_without_volume_gives_tpo_only():
    t0 = int(dt.datetime(2026, 11, 13, 9, 15, tzinfo=A.IST).timestamp())
    y0 = int(dt.datetime(2026, 11, 12, 9, 15, tzinfo=A.IST).timestamp())
    t = [y0 + 60 * i for i in range(375)] + [t0 + 60 * i for i in range(375)]
    px = [25000 + (i % 50) for i in range(750)]
    a = A.analyse({"t": t, "o": px, "h": [x + 5 for x in px], "l": [x - 5 for x in px], "c": px, "v": [0] * 750})
    assert a["vp"]["poc"] is None and a["vwap"]["vwap"] is None and "auction" not in a      # nothing invented
    assert a["tpo"]["tpo_poc"] is not None and a["tpo"]["ib_high"] == 25054
