"""Should this run go ahead? Lets the jobs start themselves without a Claude task.

Two clocks start the jobs: an outside timer (cron-job.org, to the minute) and GitHub's own
`schedule:` as a backup (often late, sometimes by hours). Either may fire several times, so
each run first asks this guard and quietly stops when it is not needed.

  python run_guard.py live      -> live price feed: go on a weekday before 15:25 IST,
                                   unless another live run is already streaming
  python run_guard.py refresh   -> nightly refresh: go on a weekday after 15:40 IST,
                                   unless a "Nightly Dhan refresh" commit landed since then

A live run never starts while another live run is streaming; other than that, a manual
"Run workflow" click or the outside timer always goes ahead. Prints "go" or "skip: why" and writes go=true/false
to $GITHUB_OUTPUT. Needs GH_TOKEN, GITHUB_REPOSITORY, GITHUB_RUN_ID, GITHUB_EVENT_NAME.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.request

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
WORKFLOW = {"live": "live-feed.yml", "refresh": "dhan-refresh.yml"}


def decide(kind: str, event: str, now: dt.datetime, runs: list[dict], own_id: int,
           commits: list[dict] | None = None) -> tuple[bool, str]:
    """Pure decision. `runs`: this workflow's recent runs; `commits`: recent main commits {sha, date, message}."""
    others = [r for r in runs if int(r.get("id", 0)) != own_id]
    busy = [r for r in others if r.get("status") == "in_progress"]
    if kind == "live" and busy:                       # never two feeds at once, however started
        return False, f"live run {busy[0]['id']} is already streaming"
    if event == "workflow_dispatch":
        return True, "started by hand or by the outside timer"
    now = now.astimezone(IST)
    if now.weekday() >= 5:
        return False, "weekend"
    if kind == "live":
        if now.time() >= dt.time(15, 25):
            return False, "market about to close or closed"
        return True, "no live run is streaming"
    if now.time() < dt.time(15, 40):
        return False, "before today's close"
    close = now.replace(hour=15, minute=40, second=0, microsecond=0)
    for c in commits or []:
        t = dt.datetime.fromisoformat(str(c.get("date", "")).replace("Z", "+00:00"))
        if t >= close and str(c.get("message", "")).startswith("Nightly Dhan refresh"):
            return False, f"today's close is already saved ({str(c.get('sha', ''))[:7]})"
    return True, "today's close not saved yet"


def _get(repo: str, path: str, token: str):
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/{path}",
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def recent_commits(repo: str, token: str) -> list[dict]:
    return [{"sha": c["sha"], "date": c["commit"]["committer"]["date"], "message": c["commit"]["message"]}
            for c in _get(repo, "commits?sha=main&per_page=15", token)]


def main() -> int:
    kind = sys.argv[1] if len(sys.argv) > 1 else ""
    if kind not in WORKFLOW:
        print(__doc__)
        return 2
    event = os.environ.get("GITHUB_EVENT_NAME", "workflow_dispatch")
    try:
        runs, commits = [], []
        repo, tok = os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GH_TOKEN", "")
        if kind == "live":
            runs = _get(repo, f"actions/workflows/{WORKFLOW[kind]}/runs?status=in_progress&per_page=20", tok).get("workflow_runs", [])
        elif event != "workflow_dispatch":
            commits = recent_commits(repo, tok)
        go, why = decide(kind, event, dt.datetime.now(IST), runs, int(os.environ.get("GITHUB_RUN_ID", "0")), commits)
    except Exception as e:  # cannot ask GitHub: better a spare run than a missed day
        go, why = True, f"could not check other runs ({str(e)[:60]}), going ahead"
    print(("go: " if go else "skip: ") + why)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"go={'true' if go else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
