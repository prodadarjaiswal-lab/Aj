"""Offline tests for the indicator lab and the desk journal (synthetic data, no Dhan)."""
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import indicator_lab as L  # noqa: E402
import journal as J  # noqa: E402


def _days(n, start=dt.date(2018, 1, 1)):
    out, x = [], start
    while len(out) < n:
        if x.weekday() < 5:
            out.append(x.isoformat())
        x += dt.timedelta(1)
    return out


def _panel(S, N, seed, plant=False):
    rng = np.random.default_rng(seed)
    dates = _days(N)
    nc = 20000 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, N)))
    data = {}
    for s in range(S):
        r = rng.normal(0, 0.02, N)
        c = 100 * np.exp(np.cumsum(r))
        if plant:                       # after a 10%+ five-day drop, add +0.4% a day for 21 days
            i = 10
            while i < N:
                if c[i] / c[i - 5] - 1 <= -0.10:
                    r[i + 1:i + 22] += 0.004
                    c = 100 * np.exp(np.cumsum(r))
                    i += 22
                else:
                    i += 1
        data[f"S{s}"] = {"d": dates, "o": c.tolist(), "h": (c * 1.01).tolist(), "l": (c * 0.99).tolist(),
                         "c": c.tolist(), "v": [1e6] * N}
    return data, {"d": dates, "c": nc.tolist()}


def test_lab_keeps_nothing_on_noise():
    data, nifty = _panel(40, 1600, 1)
    res = L.run(data, nifty)
    assert res["keep"] == []
    assert res["tested"] == len(L.NAMES)
    json.dumps(res)


def test_lab_finds_a_planted_edge():
    data, nifty = _panel(60, 1600, 3, plant=True)
    res = L.run(data, nifty)
    assert "drop5d_10" in res["keep"]


def test_score_stop_target_time():
    d = _days(30)
    o = {"d": d, "c": [100.0] * 30, "h": [101.0] * 30, "l": [99.0] * 30}
    nmap = {x: 1.0 for x in d}
    base = {"d": d[0], "sym": "X", "entry": 100.0, "stop": 95.0, "target": 110.0, "qty": 10}
    assert J.score(base, o, nmap)["status"] == "time"
    o2 = dict(o, l=[99.0] * 3 + [94.0] + [99.0] * 26)
    r = J.score(base, o2, nmap)
    assert r["status"] == "stop" and r["days"] == 3 and r["pnl_rs"] < -50
    o3 = dict(o, h=[101.0] * 2 + [111.0] + [101.0] * 27)
    assert J.score(base, o3, nmap)["status"] == "target"
    o4 = {k: v[:5] for k, v in o.items()}
    assert J.score(base, o4, nmap)["status"] == "open"


def test_add_plans_marks_calls():
    led = {"recs": []}
    tp = {"asof": "2026-11-25", "plans": {
        "A": {"signal": "don55", "entry": 10, "stop": 9, "target": 11.5, "qty": 5, "checks": [{"rule": "x", "ok": True}]},
        "B": {"signal": "flag", "entry": 10, "stop": 9, "target": 11.5, "qty": 5, "checks": [{"rule": "many", "ok": False}]}}}
    assert J.add_plans(led, tp) == 2
    assert J.add_plans(led, tp) == 0
    called = {r["sym"]: r["called"] for r in led["recs"]}
    assert called == {"A": True, "B": False}


def test_market_types_and_playbook():
    up = np.linspace(100, 200, 400)
    mt = L.market_types(np.concatenate([up, up[::-1]]))
    assert mt[399] == "rising" and mt[-1] == "falling"
    lab = {"asof": "2026-11-26", "market": {"type": "rising", "since": "2026-01-01"}, "indicators": {
        "a": {"name": "A", "verdict": "drop", "out_rising": {"n": 200, "months": 20, "abn": 0.01, "t_abn": 2.0, "net": 0.004},
              "in_rising": {"n": 500, "abn": 0.008, "t_abn": 2.5}},
        "b": {"name": "B", "verdict": "drop", "out_rising": {"n": 200, "months": 20, "abn": -0.02, "t_abn": -2.5, "net": -0.02},
              "in_rising": {"n": 500, "abn": -0.01, "t_abn": -3}},
        "c": {"name": "C", "verdict": "drop", "out_rising": {"n": 200, "months": 20, "abn": 0.02, "t_abn": 3.0, "net": 0.01},
              "in_rising": {"n": 500, "abn": -0.01, "t_abn": -1}}}}
    pb = L.playbook(lab)
    assert [x["k"] for x in pb["use"]] == ["a"] and pb["use"][0]["grade"] == "leaning"
    assert [x["k"] for x in pb["avoid"]] == ["b"]


def test_tradeplan_skips_warned_signal():
    import tradeplan as T
    sig = {"dip3": {"tested": True, "out": {"up": {"x21": 0.02}}}, "don55": {"tested": True, "out": {"up": {"x21": 0.01}}}}
    play = {"type": "rising", "use": [], "avoid": [{"k": "dip3", "abn": -0.02}]}
    assert T.best_signal(["dip3", "don55"], sig, True, 21)[0] == "dip3"
    assert T.best_signal(["dip3", "don55"], sig, True, 21, play)[0] == "don55"
    assert T.playbook_check("dip3", play)["ok"] is False


def test_journal_writes_playbook(tmp_path):
    data, nifty = _panel(60, 1600, 3, plant=True)
    out = J.run(tmp_path, data, nifty, {})
    pb = json.loads((tmp_path / "journal/playbook.json").read_text())
    assert pb["type"] in ("rising", "falling", "choppy") and "fired" in pb
    assert "Today's playbook" in (tmp_path / "journal/JOURNAL.md").read_text()
    assert "playbook:" in out
