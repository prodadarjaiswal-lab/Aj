"""Coordination between the jobs that share one Dhan login.

Dhan keeps one valid token per account: a new login cancels the previous one.
Jobs use these checks (GitHub Actions run list, via the gh CLI) to avoid
cancelling each other, and to tell a planned hand-over from an accidental clash.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DHAN_JOBS = ("dhan-refresh.yml", "tech-model.yml", "setup-backtest.yml", "auction-backtest.yml", "markets.yml")


def _runs(workflow: str) -> list:
    try:
        r = subprocess.run(["gh", "run", "list", "--workflow", workflow, "--status", "in_progress",
                            "--json", "databaseId,createdAt"], capture_output=True, text=True, timeout=30, cwd=ROOT)
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else []
    except Exception:
        return []


def batch_job_running() -> bool:
    """True while the nightly refresh or a back-test is running."""
    return any(_runs(wf) for wf in DHAN_JOBS)


def newer_run(workflow: str) -> bool:
    """True if a later run of this same workflow is in progress (a planned hand-over)."""
    me = int(os.environ.get("GITHUB_RUN_ID") or 0)
    return any(int(r["databaseId"]) > me for r in _runs(workflow)) if me else False


def wait_for_batch_jobs(max_minutes: int = 25) -> None:
    for _ in range(max_minutes * 2):
        if not batch_job_running():
            return
        print("  another Dhan job is running; waiting before logging in")
        time.sleep(30)
