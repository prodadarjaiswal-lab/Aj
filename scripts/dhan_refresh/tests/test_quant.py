import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import quant as Q  # noqa: E402


def test_black_scholes_textbook_values():
    c = Q.black_scholes(100, 100, 1.0, 0.05, 0.2, "call")
    p = Q.black_scholes(100, 100, 1.0, 0.05, 0.2, "put")
    assert abs(c["price"] - 10.4506) < 1e-3 and abs(p["price"] - 5.5735) < 1e-3
    assert abs(c["delta"] - 0.6368) < 1e-3 and abs(c["gamma"] - 0.01876) < 1e-4
    assert abs(c["vega"] - 0.3752) < 1e-3 and abs(c["theta"] - (-6.414 / 365)) < 1e-4 and abs(c["rho"] - 0.5323) < 1e-3
    assert abs((c["price"] - p["price"]) - (100 - 100 * math.exp(-0.05))) < 1e-9          # put-call parity
    assert abs(Q.implied_vol(c["price"], 100, 100, 1.0, 0.05) - 0.2) < 1e-6
    assert Q.black_scholes(110, 100, 0, 0.05, 0.2, "call")["price"] == 10                   # expiry: intrinsic


def test_inverse_normal():
    assert abs(Q._z(0.99) - 2.326348) < 1e-5 and abs(Q._z(0.95) - 1.644854) < 1e-5 and abs(Q._z(0.5)) < 1e-9


def test_min_variance_two_assets_closed_form():
    cov = np.array([[0.04, 0.0], [0.0, 0.09]])
    w = Q._solve(np.array([0.1, 0.1]), cov, 1.0, "minvar")
    assert abs(w[0] - 0.09 / 0.13) < 1e-3 and abs(w.sum() - 1) < 1e-9
    capped = Q._solve(np.array([0.1, 0.1]), cov, 0.6, "minvar")
    assert abs(capped[0] - 0.6) < 1e-6                                                       # the cap binds


def test_monte_carlo_and_calibration_on_a_random_walk():
    rng = np.random.default_rng(1)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.015, 1600)))
    m = Q.monte_carlo(c, atr=2.0, fan=True)
    assert m["p5"] < m["p25"] < m["p50"] < m["p75"] < m["p95"] and 0 < m["p_up"] < 1
    assert m["p_target_first"] + m["p_stop_first"] <= 1 and len(m["fan"]) == 21
    cal = Q.mc_calibration({"S": c}, n=1500)
    assert cal["cases"] >= 20 and 0.8 <= cal["inside_90"] <= 1.0


def test_var_normal_returns_and_kupiec():
    rng = np.random.default_rng(2)
    r = rng.normal(0, 0.01, 1500)
    v = Q.var_report(r)
    assert abs(v["99"]["param_1d"] - 2326) < 250 and abs(v["99"]["hist_1d"] - 2326) < 400
    assert v["99"]["es_1d"] > v["99"]["hist_1d"] and v["99"]["mc_10d"] > v["99"]["mc_1d"]
    k = Q.kupiec(r)
    assert k["ok"] and k["days"] == 500


def test_pairs_finds_a_cointegrated_pair_and_not_noise():
    rng = np.random.default_rng(3)
    x = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, 1000)))
    e = np.zeros(1000)
    for t in range(1, 1000):
        e[t] = 0.85 * e[t - 1] + rng.normal(0, 0.01)
    y = np.exp(0.2 + 1.5 * np.log(x) + e)
    a, b, res = Q.ols(np.log(y), np.log(x))
    assert abs(b - 1.5) < 0.05 and Q.adf_t(res) < Q.EG_CRIT and 2 <= Q.half_life(res) <= 10
    z = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, 1000)))
    out = Q.pairs_scan({"IND": {"Y": y, "X": x, "Z": z}})
    pairs = {(p["y"], p["x"]) for p in out["current"]}
    assert ("Y", "X") in pairs and ("X", "Z") not in pairs
    assert out["strategy_oos"]["trades"] > 0
