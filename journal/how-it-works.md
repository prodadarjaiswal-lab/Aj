## How the desk works

**One run a day.** A single Claude scheduled task runs at 8:43 AM IST on weekdays. It starts the live price feed
(`live-feed.yml`), then the daily refresh (`dhan-refresh.yml`), then republishes the Evidence Desk and the Trading
Terminal. There are no GitHub timers: GitHub's own scheduler started jobs 5 to 10 hours late, so it was removed.
Because the refresh runs in the morning, the desk shows the previous trading day's close until the next morning run;
during market hours the prices tick from the live feed. (An evening close update is being added separately.)

**What the daily refresh does, in order** (`scripts/dhan_refresh/refresh.py --with-tech`):
1. Logs in to Dhan fresh with TOTP and checks the data (Nifty present, no future bars, no 25%+ one-day jumps).
2. Pulls 11 years of daily bars for the Nifty 500 (`tech_model.fetch`).
3. Re-runs the technical model's back-test of 30 desk signals (`tech_model.py`): each signal must beat the average stock
   in the first years and again in the last 2 years, in rising and weak markets separately. Signals are promoted or
   dropped automatically.
4. Value model, portfolio fit, research screener, risk lab (GARCH volatility, conformal ranges, and the joint
   many-signals test), then the trade plan (`tradeplan.py`): entry at the close, stop from the stock's volatility over
   21 sessions, target 1.5x the risk, size from Rs 1,00,000 capital and Rs 1,000 maximum loss per trade, charges
   included, 10,000 replays for the odds.
5. A trade plan is a real call only if every check passes: reward to risk, expected value after charges, turnover,
   position cap, daily loss limit, the many-signals test, and no results meeting while held.
6. The live track record (`track.py`) logs the day's picks before the outcome is known and scores them 10 and 21
   sessions later.
7. This journal (`journal.py`): adds the day's plans to the ledger, scores every past plan on the new bars, re-runs
   the indicator back-test (`indicator_lab.py`), and rebuilds this file.

**Why "no trade" is the usual answer.** With dozens of signals tested at once, some look good by luck. The
many-signals test (and Holm's correction in the indicator lab) asks whether a result is still convincing after
allowing for that. When nothing survives, the honest output is no call.

**Where things live.** Desk: https://claude.ai/artifact/QHCtbgKuHA17eSSS4zbd9h. Code: `scripts/dhan_refresh/`.
Journal: `journal/` in the repo, copied to the project's files as `journal/JOURNAL.md` by the daily task.
