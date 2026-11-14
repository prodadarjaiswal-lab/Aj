import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import track as K  # noqa: E402


def test_picks_logged_once_then_scored():
    log = {"picks": []}
    picks = [{"kind": "rising", "sym": "AAA", "sig": "hi52v"}]
    log = K.update(log, "d0", picks, {"AAA": 100.0}, {"AAA": 2.0}, 1000.0)
    log = K.update(log, "d0", picks, {"AAA": 100.0}, {"AAA": 2.0}, 1000.0)       # same day again: no duplicate
    assert len(log["picks"]) == 1 and log["picks"][0]["path"] == []
    for i in range(1, 22):
        log = K.update(log, f"d{i}", [], {"AAA": 100.0 + i}, {}, 1000.0)
    p = log["picks"][0]
    assert p["x10"] == 0.1 and p["x21"] == 0.21 and p["exit"] == "target" and len(p["path"]) == 21
    s = K.summary(log)["rising"]
    assert s["n21"] == 1 and s["beat21"] == 1.0 and s["target_first"] == 1.0 and s["open"] == 0


def test_todays_picks_use_only_tested_signals():
    tech = {"stocks": {"AAA": {"new": ["hi52v"]}, "BBB": {"new": ["st_up"]}, "CCC": {"new": ["qdrop"]}}}
    board = {"rows": [{"s": "AAA", "status": "lead"}, {"s": "BBB", "status": "lead"}, {"s": "CCC", "status": "weak"}]}
    model = {"signals": {"hi52v": {"tested": True}, "st_up": {"tested": False}, "qdrop": {"tested": True}}}
    got = K.todays_picks(tech, board, model, True)
    assert {(p["kind"], p["sym"]) for p in got} == {("rising", "AAA"), ("dips", "CCC")}
