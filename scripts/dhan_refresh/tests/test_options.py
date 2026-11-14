import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "dhan_refresh"))
import options_snapshot as O  # noqa: E402

TODAY = dt.date(2026, 11, 11)


def leg(ltp, oi, iv, vol=100, poi=None, delta=None):
    return {"last_price": ltp, "oi": oi, "implied_volatility": iv, "volume": vol,
            "previous_oi": oi if poi is None else poi, "greeks": {"delta": delta} if delta else {}}


def chain():
    oc = {}
    spot = 1324.4
    for k in range(1100, 1560, 20):
        c = leg(max(spot - k, 0) + 20, 1000 + (5000 if k == 1400 else 0), 0 if k < 1320 else 20 + (k - 1320) / 50, delta=0.5 if k == 1320 else None)
        p = leg(max(k - spot, 0) + 18, 1000 + (8000 if k == 1200 else 0), 24 + (1320 - k) / 20 if k <= 1320 else 200)
        oc[f"{k}.000000"] = {"ce": c, "pe": p}
    return {"data": {"last_price": spot, "oc": oc}}


class Fake:
    def expiries(self, sid, seg):
        if sid == "bad":
            raise RuntimeError("not in F&O")
        return ["2026-11-12", "2026-11-23", "2026-12-29"]

    def chain(self, sid, seg, exp):
        assert exp == "2026-11-23"   # skips the expiry 1 day away
        return chain()


def test_features_from_chain():
    snap = O.snapshot(Fake(), {"RELIANCE": ("2885", "NSE_FNO"), "X": ("bad", "NSE_FNO")}, TODAY)
    f = snap["rows"]["RELIANCE"]
    assert f["expiry"] == "2026-11-23" and f["days"] == 12 and f["atm"] == 1320
    assert abs(f["exp_move"] - (f["straddle"] / f["spot"])) < 1e-5
    assert f["iv_call"] > 0 and f["iv_put"] > 0 and f["cp_spread"] < 0   # puts richer
    assert f["skew"] > 0 and f["skew_strike"] <= 1324.4 * 0.95
    assert f["call_wall"] == 1400 and f["put_wall"] == 1200
    assert "X" in snap["errors"]


def test_junk_iv_filtered():
    L = O.clean_leg(leg(5, 10, 198))
    assert L["iv"] is None
    assert O.clean_leg(leg(0, 0, 0))["iv"] is None


def test_save_snapshot_uses_given_client(tmp_path, monkeypatch):
    import shutil
    (tmp_path / "docs").mkdir()
    shutil.copy(ROOT / "docs" / "ra-desk.html", tmp_path / "docs" / "ra-desk.html")
    nset = O.R.read_nset((tmp_path / "docs" / "ra-desk.html").read_text())
    rows = ["SEM_EXM_EXCH_ID,SEM_SEGMENT,SEM_SMST_SECURITY_ID,SEM_INSTRUMENT_NAME,SEM_TRADING_SYMBOL,SM_SYMBOL_NAME,SEM_CUSTOM_SYMBOL,SEM_SERIES",
            "NSE,E,2885,EQUITY,RELIANCE,RELIANCE,RELIANCE,EQ"]

    class Client(Fake):
        def __init__(self):
            pass
    O.OptionsClient = lambda d: d          # no 3-second spacing in tests
    real_dt = O.dt.datetime

    class Monday(real_dt):                             # a weekday, so the run is not skipped
        @classmethod
        def now(cls, tz=None):
            return real_dt(2026, 11, 16, 18, 0, tzinfo=tz)
    monkeypatch.setattr(O.dt, "datetime", Monday)
    nset_day = "2026-11-16"
    O.TODAY_OVERRIDE = None
    msg = O.save_snapshot(Client(), "\n".join(rows), tmp_path)
    assert "options snapshot" in msg or "already saved" in msg
    assert (tmp_path / "data" / "options" / f"{nset_day}.json").exists()


def test_chain_with_a_wrong_spot_is_dropped(tmp_path, monkeypatch):
    import shutil
    (tmp_path / "docs").mkdir()
    shutil.copy(ROOT / "docs" / "ra-desk.html", tmp_path / "docs" / "ra-desk.html")
    real_dt = O.dt.datetime

    class Monday(real_dt):
        @classmethod
        def now(cls, tz=None):
            return real_dt(2026, 11, 16, 18, 0, tzinfo=tz)
    monkeypatch.setattr(O.dt, "datetime", Monday)
    nset = O.R.read_nset((tmp_path / "docs" / "ra-desk.html").read_text())
    close = nset["idx"]["Nifty 50"]["c"][-1]
    monkeypatch.setattr(O, "snapshot", lambda c, u, d: {"date": d.isoformat(), "errors": {},
                        "rows": {"NIFTY": {"spot": close * 1.03}, "BANKNIFTY": {"spot": nset["idx"]["Nifty Bank"]["c"][-1]}}})
    monkeypatch.setattr(O.R, "build_maps", lambda *a: ({}, {}))
    O.save_snapshot(object(), "", tmp_path)
    saved = O.json.loads((tmp_path / "data/options/2026-11-16.json").read_text())
    assert "NIFTY" not in saved["rows"] and "disagrees" in saved["errors"]["NIFTY"] and "BANKNIFTY" in saved["rows"]


def test_weekend_is_skipped(monkeypatch):
    real_dt = O.dt.datetime

    class Saturday(real_dt):
        @classmethod
        def now(cls, tz=None):
            return real_dt(2026, 11, 14, 12, 0, tzinfo=tz)
    monkeypatch.setattr(O.dt, "datetime", Saturday)
    assert "skipped" in O.save_snapshot(object(), "", ROOT)
