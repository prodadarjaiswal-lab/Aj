import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import auction as A  # noqa: E402
import auction_bt as BT  # noqa: E402

O = A.OPEN_MIN


def flat_day(base, n=75, step=0.0):
    return [(O + 5 * i, base + step * i, base + step * i + 0.5, base + step * i - 0.5, base + step * i, 1000) for i in range(n)]


def test_ib_breakout_and_value_acceptance():
    prev = flat_day(100)                                   # value around 99.5-100.5
    rows = [(O + 5 * i, 102 + 0.01 * i, 102.5 + 0.01 * i, 101.5 + 0.01 * i, 102 + 0.01 * i, 1000) for i in range(12)]
    rows += [(O + 60 + 5 * i, 104, 104.5, 103.5, 104, 1000) for i in range(63)]   # breaks above the first hour at 10:15
    sig = BT.session_signals(rows, prev)
    assert sig["ibx_up"] == 12 and "ibx_dn" not in sig
    assert sig["va_accept_up"] == 11                       # opened above value, still above at 10:15


def test_value_rejection_and_vwap_reclaim():
    prev = flat_day(100)
    rows = [(O, 101.5, 101.6, 100.0, 100.2, 1000)] + [(O + 5 * i, 100, 100.4, 99.6, 100, 1000) for i in range(1, 12)]
    rows += [(O + 60 + 5 * i, 99.0, 99.2, 98.8, 99.0, 1000) for i in range(10)]      # below VWAP for 50 minutes
    rows += [(O + 110 + 5 * i, 101.0, 101.2, 100.8, 101.0, 1000) for i in range(53)]  # back above
    sig = BT.session_signals(rows, prev)
    assert "va_reject_up" in sig and sig["vwap_reclaim"] == 22


def test_noise_passes_nothing():
    random.seed(7)
    days = [f"2026-{m:02d}-{d:02d}" for m in range(1, 13) for d in range(1, 21)]
    def ses(seed):
        random.seed(seed)
        out, p = {}, 100.0
        for d in days:
            rows = []
            for i in range(75):
                q = p * (1 + random.gauss(0, 0.002))
                rows.append((O + 5 * i, p, max(p, q) * 1.0005, min(p, q) * 0.9995, q, random.randint(100, 900)))
                p = q
            out[d] = rows
        return out
    res = BT.backtest({f"S{i}": ses(i) for i in range(6)}, ses(99))
    assert set(res["signals"]) == set(BT.NAMES) and not any(r["tested"] for r in res["signals"].values())
    assert res["signals"]["ibx_up"]["out"]["n"] > 30
