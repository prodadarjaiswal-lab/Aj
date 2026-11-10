# Dhan nightly refresh

Updates the prices, candles, price-based technicals and Dhan fundamentals embedded in `docs/ra-desk.html` every weekday at 16:15 IST.

## One-time setup
1. In GitHub: **Settings → Secrets and variables → Actions → New repository secret**. Add:
   - `DHAN_CLIENT_ID`: your Dhan client ID
   - `DHAN_PIN`: your Dhan PIN
   - `DHAN_TOTP_SECRET`: the TOTP **secret key** (the text behind the QR code), not a 6-digit code
2. Make sure your Dhan Data Plan is active. The data APIs need it.
3. Merge this branch into the default branch. GitHub only runs scheduled workflows from the default branch.
4. **Actions → Dhan nightly refresh → Run workflow** once to test.

## How it avoids failures
- Logs in fresh every run with TOTP, so there is no 24-hour token to keep alive.
- Retries rate limits, server errors and TOTP-boundary rejections (3 tries, growing waits).
- Checks before writing: Nifty fetched, at most 2 stocks missing, no bar dated in the future, no one-day move over 25% (a possible split), and the feed not stale (unchanged closes). If any check fails, the page is **not** written and GitHub emails you that the run failed.
- Holidays: if Dhan has no new session, the page is left as is and the run still passes.

## What it does not update
These come from the monthly research pipeline and are kept as they are:
- valuation models and back-tests (`fund`, `val`)
- the news set (Google News)
- macro series

Fundamentals from Dhan's Company Info are stored per stock as `dhan_fund` for later use.

## Run locally
```
pip install requests pyotp
DHAN_CLIENT_ID=... DHAN_PIN=... DHAN_TOTP_SECRET=... python scripts/dhan_refresh/refresh.py
python -m pytest -q scripts/dhan_refresh/tests   # offline, no secrets needed
```
