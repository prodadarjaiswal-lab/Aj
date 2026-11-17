import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import risklab as RL  # noqa: E402

arch = pytest.importorskip("arch")


def gjr(n, seed, w=0.05, a=0.05, g=0.08, b=0.88, df=6):
    """Simulated GJR-GARCH(1,1) percent returns with t errors; persistence a + g/2 + b = 0.97."""
    rng = np.random.default_rng(seed)
    e = rng.standard_t(df, n) / np.sqrt(df / (df - 2))
    s2, r = w / (1 - a - g / 2 - b), np.empty(n)
    for t in range(n):
        r[t] = np.sqrt(s2) * e[t]
        s2 = w + (a + g * (r[t] < 0)) * r[t] ** 2 + b * s2
    return r


def calendar(n):
    d0 = dt.date(2015, 1, 1)
    return [(d0 + dt.timedelta(days=k)).isoformat() for k in range(n)]


def synth(n_stocks=50, n=1400, seed=0):
    cal = calendar(n)
    data = {}
    for k in range(n_stocks):
        r = gjr(n - 1, seed + k) / 100
        c = 100 * np.exp(np.concatenate([[0], np.cumsum(r)]))
        data[f"S{k:02d}"] = {"d": cal, "o": list(c), "h": list(c), "l": list(c), "c": list(c), "v": [1] * n}
    return data, {"d": cal, "c": list(100 * np.ones(n))}


def test_garch_recovers_persistence():
    out, res = RL.fit_vol(gjr(3000, 1), arch.arch_model)
    assert out["model"].startswith("GJR")
    assert abs(out["persistence"] - 0.97) < 0.03
    assert out["d5"] > out["d1"] > 0 and res is not None


def test_ewma_fallback_without_arch():
    out, res = RL.fit_vol(gjr(500, 2), None)
    assert out["model"].startswith("EWMA") and res is None and out["d1"] > 0


def test_kupiec_pof_matches_quant():
    assert RL.pof(10, 1000, 0.01)["ok"] and not RL.pof(30, 1000, 0.01)["ok"]


def test_conformal_coverage_close_to_target():
    from mapie.regression import SplitConformalRegressor
    from sklearn.linear_model import LinearRegression
    data, nifty = synth(50, 1400, 10)
    cl = {s: (o["d"], o["c"]) for s, o in data.items()}
    out = RL.conformal(cl, nifty["d"], SplitConformalRegressor, LinearRegression)
    assert abs(out["coverage_measured"] - 0.90) <= 0.05
    lo, hi = out["by_sym"]["S00"]
    assert lo < 0 < hi


def test_noise_signal_fails_strong_signal_survives():
    from arch import bootstrap as B
    rng = np.random.default_rng(3)
    dates = calendar(500)
    series = {"noise": {d: [float(x)] for d, x in zip(dates, rng.normal(0, 0.03, 500))},
              "strong": {d: [float(x)] for d, x in zip(dates, rng.normal(0.012, 0.03, 500))},
              "few": {d: [0.05] for d in dates[:10]}}
    out = RL.signal_tests(series, ["noise", "strong", "few"], B)
    assert out["strong"]["survives"] and out["strong"]["ci_lo"] > 0
    assert not out["noise"]["survives"] and out["noise"]["ci_lo"] < 0 < out["noise"]["ci_hi"]
    assert out["few"] == {"ci_lo": None, "ci_hi": None, "spa_p": None, "survives": False}
    assert out["strong"]["spa_p"] < 0.05


def test_track_bands_need_30():
    from arch import bootstrap as B
    rng = np.random.default_rng(4)
    picks = [{"kind": "score6", "d": f"2026-01-{k % 28 + 1:02d}", "x21": float(x)} for k, x in enumerate(rng.normal(0.01, 0.05, 60))]
    picks += [{"kind": "score2", "d": "2026-01-01", "x21": 0.01}] * 5 + [{"kind": "score2", "d": "2026-01-02"}]
    out = RL.track_bands({"picks": picks}, B)
    assert out["score6"]["n"] == 60 and out["score6"]["ci_lo"] < out["score6"]["mean"] < out["score6"]["ci_hi"]
    assert out["score2"] == {"mean": 0.01, "ci_lo": None, "ci_hi": None, "n": 5}


def test_pairs_retest_counts():
    from arch.unitroot.cointegration import engle_granger
    rng = np.random.default_rng(5)
    x = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 900)))
    y = x * np.exp(rng.normal(0, 0.01, 900))                  # cointegrated with x
    z = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 900)))     # independent walk
    out = RL.pairs_retest({"ind": {"X": x, "Y": y, "Z": z}}, engle_granger)
    assert out["tested"] == 3 and out["cointegrated"] >= 1 and "chance" in out["verdict"]


def _root(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/tech-model.json").write_text(json.dumps({"signals": {"a": {}, "b": {}}}), encoding="utf-8")
    return tmp_path


def test_run_writes_exact_shape(tmp_path):
    data, nifty = synth(12, 1400, 20)
    rng = np.random.default_rng(6)
    ser = {"a": {d: [float(x)] for d, x in zip(nifty["d"][-400:], rng.normal(0, 0.02, 400))}}
    msg = RL.run(data, nifty, _root(tmp_path), ser, full=True, n50=["S00", "S01"], board_rows=[])
    out = json.loads((tmp_path / "docs/risklab.json").read_text(encoding="utf-8"))
    assert set(out) == {"asof", "vol", "var", "conformal", "signals", "track", "pairs", "notes"}
    assert set(out["vol"]["S00"]) == {"d1", "d5", "ann", "persistence", "model"}
    assert set(out["var"]) == {"S00", "S01"} and set(out["var"]["S00"]) == {"garch95", "garch99", "kupiec_ok"}
    assert out["var"]["S00"]["garch99"] > out["var"]["S00"]["garch95"] > 0
    assert 0.003 < out["vol"]["S00"]["d1"] < 0.1           # a fraction of price, as tradeplan reads it
    assert set(out["conformal"]) == {"coverage_target", "coverage_measured", "by_sym"}
    assert set(out["signals"]) == {"a", "b"} and set(out["signals"]["a"]) == {"ci_lo", "ci_hi", "spa_p", "survives"}
    assert set(out["pairs"]) == {"tested", "cointegrated", "verdict"}
    assert "risklab:" in msg
    # a weekday run carries the full sections over
    RL.run(data, nifty, tmp_path, None, full=False, n50=[], board_rows=[])
    again = json.loads((tmp_path / "docs/risklab.json").read_text(encoding="utf-8"))
    assert again["signals"] == out["signals"] and any(n.startswith(RL.FULL_NOTE + nifty["d"][-1]) for n in again["notes"])


def test_run_returns_normally_without_arch_or_mapie(tmp_path, monkeypatch):
    for m in ("arch", "arch.bootstrap", "arch.unitroot", "arch.unitroot.cointegration", "mapie", "mapie.regression",
              "sklearn", "sklearn.linear_model"):
        monkeypatch.setitem(sys.modules, m, None)          # import of a None entry raises ImportError
    data, nifty = synth(5, 600, 30)
    msg = RL.run(data, nifty, _root(tmp_path), {}, full=True, n50=["S00"], board_rows=[])
    out = json.loads((tmp_path / "docs/risklab.json").read_text(encoding="utf-8"))
    assert all(v["model"].startswith("EWMA") for v in out["vol"].values()) and len(out["vol"]) == 5
    assert out["var"] == {} and out["conformal"]["by_sym"] == {}
    assert any("arch unavailable" in n for n in out["notes"]) and "risklab:" in msg
