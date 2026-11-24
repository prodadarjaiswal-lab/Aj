import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import live_poller as LP  # noqa: E402
import refresh as R  # noqa: E402


def run_day(monkeypatch, newer):
    monkeypatch.setenv("DHAN_CLIENT_ID", "1")
    monkeypatch.setenv("DHAN_PIN", "1")
    monkeypatch.setenv("DHAN_TOTP_SECRET", "A")
    times = iter([dt.datetime(2026, 11, 16, 10, m, tzinfo=R.IST) for m in range(0, 50)])

    class FakeDT(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return next(times)
    monkeypatch.setattr(LP.dt, "datetime", FakeDT)
    logins = []
    monkeypatch.setattr(R, "login", lambda *a: logins.append(1) or f"tok{len(logins)}")
    calls = {"n": 0}
    # /marketfeed/ohlc call 1 is the start-up probe of the Trading Terminal board extras (added in PR 17),
    # call 2 is the first poll (pushed), call 3 is the second poll: that one loses the login.
    lose_login_on = 3

    def post(self, path, body):
        if path == "/marketfeed/quote":
            return {"data": {}}
        calls["n"] += 1
        if calls["n"] == lose_login_on:
            raise R.RefreshError("Dhan error 807: token expired")
        return {"data": {"NSE_EQ": {"1": {"last_price": 100, "ohlc": {"open": 99, "high": 101, "low": 98, "close": 99}}}}}
    monkeypatch.setattr(R.Dhan, "_post", post)
    monkeypatch.setattr(LP, "universe", lambda: ([1], {"13": "Nifty 50"}))
    monkeypatch.setattr(LP, "setup_branch", lambda: None)
    pushes = []
    monkeypatch.setattr(LP, "push", lambda p, s=None, e=None: pushes.append(p))
    monkeypatch.setattr(LP, "prior_state", lambda d: {"d": d, "sent": []})
    monkeypatch.setattr(LP.time, "sleep", lambda s: None)
    monkeypatch.setattr(LP.G, "newer_run", lambda wf: newer)
    monkeypatch.setattr(LP.G, "wait_for_batch_jobs", lambda *a: None)
    monkeypatch.setattr(LP.T, "send", lambda t: True)
    monkeypatch.setattr(LP.B, "load_state", lambda: {})
    monkeypatch.setattr(LP.B, "save_state", lambda st: None)
    monkeypatch.setattr(LP.B.Bot, "poll", lambda self: 0)
    monkeypatch.setattr(sys, "argv", ["live_poller.py", "--until", "10:06", "--every", "5"])
    rc = LP.main()
    return rc, len(logins), len(pushes)


def test_accidental_clash_logs_back_in_and_keeps_pushing(monkeypatch):
    rc, logins, pushes = run_day(monkeypatch, newer=False)
    assert rc == 0 and logins == 2 and pushes >= 3


def test_planned_handover_stops(monkeypatch):
    rc, logins, pushes = run_day(monkeypatch, newer=True)
    assert rc == 0 and logins == 1 and pushes == 1


def test_handover_detected_while_healthy(monkeypatch):
    calls = {"n": 0}
    def newer(wf):
        calls["n"] += 1
        return True
    monkeypatch.setattr(LP.G, "newer_run", newer)
    rc, logins, pushes = run_day(monkeypatch, newer=True)
    assert rc == 0
