import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_guard import IST, decide  # noqa: E402

THU = dt.datetime(2026, 11, 26, tzinfo=IST)


def at(h, m, day=THU):
    return day.replace(hour=h, minute=m)


def test_manual_and_timer_always_go():
    assert decide("live", "workflow_dispatch", at(22, 0), [], 1)[0]
    assert decide("refresh", "workflow_dispatch", at(9, 0), [], 1)[0]
    assert not decide("live", "workflow_dispatch", at(9, 5), [{"id": 7, "status": "in_progress"}], 1)[0]


def test_live_backup_cron():
    assert decide("live", "schedule", at(9, 0), [], 1) == (True, "no live run is streaming")
    busy = [{"id": 7, "status": "in_progress"}]
    assert not decide("live", "schedule", at(9, 30), busy, 1)[0]
    assert decide("live", "schedule", at(9, 30), busy, 7)[0]          # itself does not count
    assert not decide("live", "schedule", at(15, 30), [], 1)[0]       # late cron after the close
    assert not decide("live", "schedule", at(9, 0, THU + dt.timedelta(days=2)), [], 1)[0]  # Saturday


def test_refresh_backup_cron():
    assert not decide("refresh", "schedule", at(15, 0), [], 1, [])[0]
    morning = [{"sha": "a", "date": "2026-11-26T03:30:00Z", "message": "Nightly Dhan refresh 2026-11-26"}]
    assert decide("refresh", "schedule", at(17, 0), [], 1, morning)[0]   # 09:00 IST commit is yesterday's close
    evening = [{"sha": "b", "date": "2026-11-26T10:45:00Z", "message": "Nightly Dhan refresh 2026-11-26"}]
    assert not decide("refresh", "schedule", at(20, 0), [], 1, evening)[0]
    other = [{"sha": "c", "date": "2026-11-26T11:00:00Z", "message": "Desk journal"}]
    assert decide("refresh", "schedule", at(20, 0), [], 1, other)[0]
