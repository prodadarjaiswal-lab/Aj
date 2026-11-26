# Running the terminal without Claude

## What runs where

| Part | Runs on | Started by |
|---|---|---|
| Live prices, every 5 s, 09:15 to 15:30 IST (plus Telegram alerts and bot replies) | GitHub Actions `live-feed.yml`, writes `live.json` to the public repo `aj-live` | Outside timer at 09:00 IST. Backup: GitHub's own clock, every 15 min from 08:45 to 10:15 IST, then 11:30 and 13:30 |
| Close, screens, value, journal | GitHub Actions `dhan-refresh.yml` | Outside timer at 16:20 IST. Backup: GitHub's own clock at 17:00 and 20:00 IST |
| The terminal page reading those prices | The artifact in your browser, through the GitHub connector | Opening the page |

Every start first runs `scripts/dhan_refresh/run_guard.py`, which stops spare starts: never two live feeds at once,
no backup live start after 15:25 or at weekends, and no backup refresh once today's close is saved.
So extra starts are harmless and cost about 20 seconds each.

Dhan login needs no person: the jobs log in with the PIN and TOTP secret already saved in GitHub.

## Why there is an outside timer

GitHub's own clock is free but has started jobs in this repo 5 to 10 hours late. It is kept only as a backup.
cron-job.org is a free timer that fires to the minute and emails you if a start fails.

## One-time setup (about 10 minutes)

1. **GitHub token.** Open https://github.com/settings/personal-access-tokens/new
   - Name: `aj timer`. Expiration: 1 year.
   - Repository access: Only select repositories, then `prodadarjaiswal-lab/Aj`.
   - Permissions, Repository: **Actions: Read and write**. Nothing else.
   - Generate, and copy the token (starts with `github_pat_`).
2. **cron-job.org.** Sign up free at https://console.cron-job.org/signup, then Create cronjob, twice:

   | Field | Job 1 | Job 2 |
   |---|---|---|
   | Title | Aj live feed | Aj nightly refresh |
   | URL | `https://api.github.com/repos/prodadarjaiswal-lab/aj/actions/workflows/live-feed.yml/dispatches` | `https://api.github.com/repos/prodadarjaiswal-lab/aj/actions/workflows/dhan-refresh.yml/dispatches` |
   | Schedule | Custom: Mon to Fri, 09:00 | Custom: Mon to Fri, 16:20 |
   | Time zone | Asia/Kolkata | Asia/Kolkata |

   In the **Advanced** tab of each:
   - Request method: `POST`
   - Headers: `Authorization` = `Bearer <your token>`, `Accept` = `application/vnd.github+json`, `Content-Type` = `application/json`
   - Request body: `{"ref":"main"}`
   - Notifications: turn on "execution of the cronjob fails".
3. Press **Test run** on Job 1. GitHub answers `204` and a new run appears at
   https://github.com/prodadarjaiswal-lab/aj/actions/workflows/live-feed.yml (outside market hours it stops
   itself within a minute; that is expected).

## What still needs Claude

- Changing the page itself (layout, new tabs). That is the "updates" job.
- Today the screen lists, value tab and closing prices inside the page only change when the page is republished.
  Live prices tick without it. Moving the nightly lists into `aj-live` so the page reads them on open
  removes this last daily Claude step.

## Costs and limits

- GitHub Actions minutes are free and unlimited while `Aj` is public. The live feed uses about 7 runner-hours
  a trading day (about 9,000 minutes a month), far above the 2,000 free minutes of a private repo. If `Aj`
  goes private, move the live feed to the public `aj-live` repo or raise the GitHub spending limit.
- cron-job.org: free. Dhan: the Data API plan must stay active (it lapsed once, on 22 Nov).
- If your Claude usage runs out, live prices and the nightly refresh still run.
