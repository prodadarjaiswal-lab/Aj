# Owner's requests: status log (updated 14 Nov 2026)

Each line is something the owner asked for in chat, with its status.
✅ = done and tested · 🟡 = partly done · ⬜ = not started · ⛔ = not possible, with the reason.

## A. Telegram bot
- ✅ Two-way bot answers in Telegram (`bot.py`).
- ✅ Six commands only: price, SYMBOL (trade), value, hedge, top, alert. Examples live only in the bot description; replies carry no command hints.
- 🟡 The Telegram description and menu update when a price job starts. The new text applies on Mon 16 Nov at 09:07 IST.
- ✅ A symbol alone gets the technical (trade) verdict; `value` gives the investing verdict.
- ✅ Every stock asked about is journalled. The journal is copied nightly to `docs/journal.md`.

## B. Technical model
- ✅ 20 indicators back-tested on 6 years of Dhan data, separately for rising and weak markets.
- ✅ An indicator counts only if it passes in both periods (`tech_model.py`).
- ✅ The back-test reruns every trading night. Indicators are added or dropped automatically, with a Telegram notice.
- 🟡 "Keep adding new measures": the candidate list is fixed at 20. Next: a candidates file, so new ideas are tested without code changes.
- ✅ Full indicator readout for every stock (`docs/technical-desk.md`).
- ✅ Technical Desk page: verdicts, readouts, auction levels, gamma chart and both scoreboards. https://claude.ai/artifact/QHCtbgKuHA17eSSS4zbd9h, republished every weeknight at 22:37 IST.

## C. Order flow and auction
- ✅ VWAP and anchored VWAP with bands, reclaim and loss (exact, from Dhan 1-minute bars).
- ✅ Volume profile: session and 5-day composite, POC, VAH, VAL, HVN and LVN (derived).
- ✅ Market Profile / TPO: value area, Initial Balance and its extension, single prints, excess and poor highs and lows (exact).
- ✅ Auction read against yesterday's value: acceptance or rejection.
- ✅ Gamma exposure, gamma flip and strike concentrations (derived from the option chain).
- 🟡 Delta and absorption: an estimate from 1-minute bars. Next: tick-level data from Dhan's WebSocket "full" packets, which carry last traded quantity, total buy and sell quantity, and 5-level depth.
- ⬜ Live order flow from the Dhan WebSocket: trade tape built from tick changes, aggressor side from price against bid/ask, depth imbalance, large prints, buying and selling pressure. Alerts to Telegram.
- ⛔ True footprint and exchange time-and-sales: Dhan sends snapshots, not every trade with its side, so these can only be approximated. Every such output is labelled as an estimate.
- ✅ Auction signals back-tested (`auction_bt.py`, weekly): 12 months of Dhan 5-minute bars, Nifty 50, same-day trades net of costs. None passed. Initial Balance breakouts and VWAP reclaims lost money, so these levels stay context only.
- 🟡 Visualisations: volume profile and gamma by strike are on the desk page. Replay of past sessions is not built yet.

## D. Hedging
- ✅ Order: asset classes → market/sector vs company risk → stop-loss. Built on Damodaran (Drive notes and blog) and NSE/SEBI rules (`docs/hedging-research.md`).
- ✅ The hedge reply checks the last week's news and filings (Nifty 50) and flags possibly adverse company news.

## E. Pinned Claude chats
- ✅ Instructions for "Stock Query" and "Stock Journal" Projects, with setup steps (`docs/claude-project/`).
- ⛔ I cannot create Claude Projects for the owner. The owner sets them up once, about 5 minutes.

## F. Dhan reliability ("must not collapse")
- ✅ Every Dhan job messages Telegram when it fails.
- ✅ The US tracker waits for other Dhan jobs and logs back in after a conflict.
- ✅ The NSE live feed logs back in after an accidental clash and stops only for a planned hand-over (tested).

## G. Earlier requests, still standing
- ✅ Nvidia tracked via Dhan's US feed, with alerts.
- ✅ NSE alerts, morning brief and close summary.
- ✅ Hourly and nightly terminal republish (scheduled tasks).

## Owner's requests of 14 Nov (plan)
Rules:
- All prices come from Dhan. If Dhan fails, report it; never substitute another source.
- Every advanced check runs before the bot answers.
- Replies work even when the market is closed, using the last close.

1. ✅ **Bot answers in market hours** (owner's choice, 14 Nov; the repo stays private). The live Dhan job polls Telegram every loop, with live prices, live order flow and US quotes. `bot-listener.yml` is manual only, for an out-of-hours session.
2. ✅ **The 8 order-flow modules on live Dhan data.** (First live run: Mon 16 Nov.) The live job also polls Dhan `/marketfeed/quote` for the Nifty 50 and the stocks being watched. That reply carries last quantity, total buy and sell quantity, and 5-level depth. From it:
   - **Time and sales:** a tape built from changes between snapshots, with large prints flagged.
   - **Aggressor side:** the trade price against bid and ask.
   - **Delta and cumulative delta:** volume signed by aggressor side.
   - **Footprint:** signed volume at each price, with imbalances and stacked imbalances.
   - **Depth and liquidity imbalance:** buying and selling pressure.
   - **Absorption and exhaustion:** large volume with little price movement.
   - The results go to `live/flow.json`, labelled "snapshot-derived".
   - VWAP, Market Profile, Volume Profile and gamma are already built.
3. 🟡 **Every market Dhan has:** MCX futures work. Dhan news returns 401 (not enabled on the account). USD/INR has no live contract in Dhan's list.
   - MCX commodities (gold, silver, crude, natural gas futures), USDINR, indices, F&O open interest, and US stocks through Dhan's global feed.
   - Dhan news headlines, linked to the day's biggest movers to explain why they rose or fell.
4. ✅ **Technical Desk in two tabs** (rebuilt 14 Nov):
   - **Screener:** markets, rising, dips, bargains, movers, track record, Markowitz portfolio and pairs, scoreboards.
   - **Analyze** (Analyzer and Quant merged): colour-coded scorecard (verdict, trend, momentum, value, Monte Carlo chance, worst day, buyers' share, VWAP, auction, options); every price level on one scale; price with VWAP shading, cumulative delta, footprint, heaviest minutes / tape, pressure gauges, Market Profile, volume profile; Monte Carlo fan and VaR; gamma by strike and Black-Scholes on the stock's own chain; indicator bars, value and hedge, news.
   - Each item is tagged exact, derived or estimate.
   - **Why VWAP and order flow were empty, and the fix:** the 1-minute run covered only the Nifty 50; it now covers all 490 Nifty 500 stocks. Indices have no volume, so NIFTY and BANKNIFTY VWAP, volume profile and delta now come from the near-month Dhan future. Outside market hours the order-flow cards show last session's estimates from Dhan 1-minute bars; live Dhan quote snapshots replace them from 09:15.
5. ✅ **Refresh cadence:** hourly 09:25-15:25 IST (terminal and desk), 18:27 terminal, 22:37 desk. the terminal and the desk republish at the open (09:25), hourly during the session and after the close.
6. ⬜ **Self-check:** the live track record of the bot's picks (built), plus weekly re-tests. Signals that stop working are dropped automatically (built).

## Quant modules (14 Nov), built and checked on real Dhan data
- ✅ **Monte Carlo** (block bootstrap, 10,000 paths, 21 days) for 473 stocks. The 90% range held 88.5% of real outcomes over 2 years, so it is well calibrated.
- ✅ **VaR** (historical, normal, simulated; 95/99%; Expected Shortfall) for the Nifty 50. The 99% Kupiec test passed on 48 of 50 stocks.
- ✅ **Black-Scholes** price, Greeks, implied volatility and surface. Tested against textbook values; it uses the Dhan chain's IV.
- ✅ **Markowitz** (min-variance, max-Sharpe, frontier). Walk-forward over 2 years: both optimised portfolios lost to equal weight (−6.4% and −6.3% a year vs +5.9%). Weights are shown as risk information only.
- ✅ **Pairs** (Engle-Granger, z-score rules). Walk-forward: 346 trades, −0.55% per trade, t −2.28. Failed, so no pair trades are suggested.
- Everything reruns nightly inside the technical back-test, and the verdicts update themselves when results change.

## Owner's requests of 14 Nov, part 2: US, value, portfolio fit, Telegram pin
- ✅ **Desk: two tabs only.** Screener, and Analyze in three parts: 1 Technical, 2 Value (investor view), 3 Combined verdict and your portfolio. A combined-verdict strip at the top joins all three.
- ✅ **Value back-test by market condition** (`value_model.py`, nightly): 8 investor rules, 6 years of Dhan prices, Nifty 500, rising vs weak markets, 6- and 12-month horizons.
  - First run: buying cheapness (near lows, 30% falls, 2-year losers, calmest stocks) lost money.
  - "Back above the 200-day after a 30% fall" passed in rising markets (+5.2% vs the average stock over 6 months, t 2.02).
  - Weak markets have too few samples to test.
  - The terminal's fundamental test passed book/price and residual-income value (12 months); P/E vs its own median failed, so it is context only.
- ✅ **Portfolio fit** (`portfolio.py`, nightly): rules from the owner's Drive notes (`docs/portfolio-model.md`): correlation with the portfolio, two-asset volatility, beta and portfolio beta, Jensen's alpha and information ratio, ~30 holdings, utility, VaR.
  - Caps the notes do not give are ASSUMED and editable in `config/portfolio.json`.
  - Dhan holdings: India returns "No holdings available"; US returns "User not found" (no Dhan US account). Fit is measured against the Nifty 50 until holdings exist or are added under `extra`.
- 🟡 **US stocks on the desk:** prices from Dhan's US feed (30 stocks tracked quietly); history from Alpha Vantage's free split-adjusted WEEKLY series (10 years), extended with Dhan's daily US closes. Trend, Monte Carlo (4 weeks) and VaR (1 week) are computed on weekly data and labelled so.
  - 8 of 31 loaded on 14 Nov (NVDA, SPY, AAPL, MSFT, GOOGL, AMZN, META, JPM; each checked against FMP's price). The other 23 load on 15 Nov (free key: 25 calls a day); refreshed every Saturday and Sunday.
  - ⛔ Dhan has no US history API (checked DhanHQ-py v2.3.0). Daily US history is premium on Alpha Vantage, and so are US options, so there are no US option data.
- ✅ **Telegram:** the desk and terminal links are pinned in the chat; new `desk` command; trade and value replies now end with the portfolio-fit line and any tested investor rule.

## 14 Nov, part 3: screener, charts, audit
- ✅ **Screener in dropdown sections**, each with a count and a "Basis" line saying exactly which back-test it rests on. Order: Markets, Turning bullish, Order-flow setups, Dips, Investor picks, Bargains, Movers, Your portfolio, Track record, Portfolio and pairs, Scoreboards, Data freshness.
- ✅ **Bargains (India) now use only factors that passed a test** (book/price and residual-income value, Nifty 50). "P/E below its own median" failed its test and was dropped. US bargains remain an untested starting list, and say so.
- ✅ **Order-flow and auction states tested over 5 and 10 sessions** (`auction_bt.swing_backtest`, Nifty 50, 12 months of Dhan 5-minute bars): value-area acceptance, POC shift, VWAP with buyer share, first-hour range extension, absorption, delta divergence. None passed (all |t| < 1), so no stock is listed from them; the scoreboard shows the numbers.
- ✅ **Click any stock: 1-year price chart** with 50/200-day averages, weekly volume, stop and target (Dhan daily closes; US: weekly Alpha Vantage + Dhan).
- ✅ **Desk works for every stock and loads fast on a phone:** page cut from 4.2 MB to 0.8 MB; each stock's detail loads from one of 25 small files when opened. Tested on 46 symbols at phone and desktop width: no errors, no sideways scroll.
- ✅ **Data freshness check** in the screener: 20 sources with their dates.
  - Stale, found by the audit: the NSE terminal's news and filings (10 Nov), FII/DII flows (9 Nov), global markets (23 Oct, old Yahoo series) and macro. The nightly job refreshes prices, technicals and Dhan fundamentals only.
- All scheduled republish tasks now publish the page together with its detail files.

## 14 Nov, part 4: research screener
- ✅ **Research screener (first section, all Nifty 500):**
  - 10 screens: Best evidence, Tested setups, Investor rules, Value with quality, Institutions buying, Accepted higher, Down: company-specific, Down with the market, Oversold quality, Leaders.
  - Filters: industry, value, trend, and a ₹10 Cr turnover floor (from the skills).
  - Columns: evidence chips (green = passed a back-test, dashed = context), 3-month strength, last-session order flow (VWAP, buyers, value acceptance), P/E against the sector, ROCE, FII change, and **why it moved** (3 months split into market, sector and company-specific, plus ownership and earnings or P/E changes).
- ✅ **Dhan company data for all 488 stocks nightly** (`research.py`, `docs/fund500.json`): P/E, P/E against the sector, P/B, ROCE, debt, dividend yield, promoter/FII/DII holdings and changes. A weekly history builds up, to show improving ratios.
- ✅ **Setups from the owner's skills added to the 6-year back-test:**
  - Passed: bull flag (rising markets, +0.96% extra over 10 days out of sample) and oversold RSI(14) < 30 (weak markets).
  - Failed: 20-day breakout, reclaim the 20-day average, oversold bounce.
- ✅ **Research factors tested on 6 years:** 6-month relative strength, accumulation and the trend stack were positive in both halves but t 1.7–1.8 (just short of 2), so they are context. "Near the 52-week high" showed nothing.
- **Score counts only tested evidence;** everything else is a filter.

## 14 Nov, part 5: daily digest, journal review, chat cleanup
- ✅ **Daily Telegram digest** after the nightly Dhan run (once per trading day): market condition, best-evidence stocks, follow-ups on stocks you researched, strong stocks and industries you haven't looked at, a habit check, and the desk link. First one sent 14 Nov.
- ✅ **Journal review** (`daily_digest.py`), on the desk ("Your research journal") and via the bot's `review` command: what happened since you looked, follow-ups, blind spots, habits.
- ✅ **Bug fixed: the journal was being wiped.** Three jobs save the bot state, and the last writer overwrote the others' journal entries; the state had no journal at all. Saves now merge journals. Questions asked before 14 Nov are lost.
- ✅ **Telegram chat cleared** (ids 1–26; Telegram only lets bots delete messages under 48 hours old) and the desk links re-pinned. `telegram-clean.yml` does it again on demand.

## 15 Nov: live proof, longer history, NSE feeds
- ✅ **Back-tests now use 11 years of Dhan history** (2015 on, was 6).
  - Investor rules passing in rising markets at 6 months: 12-month momentum (t 2.5), 6-month relative strength (2.46), accumulation (2.65), trend stack (2.08), recovery above the 200-day (2.32).
  - Buying cheapness still fails. Weak markets still have too few samples (17 dates).
  - Technical signals passing in rising markets: 52-week high on volume, tight inside day, volume breakout, 55-day breakout, relative-strength high, bull flag, two dip rules.
- ✅ **Score cap:** investor rules overlap, so they add 2, then 1, 1 (at most 4).
- ✅ **Live proof of the score** (`track.py`): each night logs stocks by score band (6+, 4–5.5, 2–3.5) and a control group of 20 zero-score stocks; graded after 10 and 21 sessions against the Nifty. First grades about 1 Dec.
- ✅ **NSE feeds nightly** (`nse_feeds.py`, the nse-day-trader method; works from GitHub Actions): filings for all Nifty 500 stocks (5 days), results and board-meeting calendar (21 days), FII/DII flows. On the desk: filings and upcoming events in Analyze, an event flag in the screener, FII/DII tiles in Markets.
- ✅ **S&P 500 and Nasdaq ETFs** (SPY, QQQ) tracked on Dhan's US feed for the Markets tiles, replacing the old Yahoo series on the desk.
- ✅ **Quarterly results from NSE XBRL filings** (`results.py`, Wed and Sat, incremental): revenue, EBITDA margin, profit and EPS, with YoY, QoQ and margin change, for about 454 Nifty 500 stocks (Sep 2026 quarter). On the desk: "Results improving" and "Results deteriorating" screens, a results column, and a last-quarter tile in Analyze. The journal review flags new results for stocks you researched. Context only: too little filing history to back-test.

## 15 Nov, part 2: any stock
- ✅ **Search pop-up** in Analyze: type a name or symbol ("adani ent" → ADANIENT), use the arrow keys or tap. Covers every NSE equity in Dhan's list (2,986), the US list and the two indices.
- ✅ **Every NSE-listed stock analysable** (`all_stocks.py`, nightly 19:47 IST, own branch `allstocks` so the repo does not grow): 2 years of Dhan bars, the same signals and readout as the tested model, a 1-year chart, swings and Dhan company data (weekly).
- ✅ **"Last swings and why"** in Analyze: each 10%+ turning point over 2 years, the Nifty's move over the same days, the move beyond it, the industry's move, and quarterly results filed inside the swing.
- ✅ **Technical and Value are dropdowns** in Analyze.
- First run: 2,809 of 2,986 stocks profiled. The first run's company-data load hit the time limit; that data refreshes weekly, so nightly runs cover all.

## 16 Nov: Evidence Desk, trade plan (Agent A)
- New `scripts/dhan_refresh/tradeplan.py`, called from tech_model.py after research.run. Writes `docs/tradeplan.json`: one plan per stock whose new signal passed the out-of-sample test for today's market (rising or weak): entry (last Dhan close on the auction.tick_for step), stop (reworked 17 Nov: entry minus 0.75 x one day's volatility x sqrt(21), i.e. scaled to the holding period; risklab.json d1 when it exists, else ATR 14), target (1.5 x the risk; plans still open after 21 sessions close at that day's price, and the signal's tested average 21-day excess move is the drift in the replays), odds and average rupee result from 10,000 block-bootstrap replays net of charges, size within max loss, capital and the 10% stock cap, and seven checks (reward to risk, value after charges, turnover, position cap, daily loss limit, survives the risk lab's many-signals test (added 17 Nov; fails until risklab.json has signal results), results or board meeting while held). Failing plans are written too, with the reason.
- New `config/trading.json`: capital Rs 1,00,000, max loss Rs 1,000 a trade, daily limit Rs 2,000 are EXAMPLE values (`_assumed: true`): set your own. Intraday rates from the nse-day-trader skill; delivery STT, stamp, zero brokerage and the DP charge are marked assumed.
- Analyze view: a "Trade plan" card (levels, odds, size, each check pass or fail, basis tags, "Place by hand. This desk never sends orders."). Stocks without a tested new signal say "No tested setup today". Plans travel in the per-stock d/*.json files.
- First result (local build from the 250 Dhan closes in chart-data.json, 13 Nov close): 135 plans, none passes every check. The tested edge (about +1 to +3% beyond Nifty over 21 days) is small next to a 1.5-volatility stop, so reward to risk is under 1.5 and the average result after delivery charges is negative. That is the honest answer, not a bug.
- Not done here: the workflow that commits docs/*.json does not yet list docs/tradeplan.json (left to the thread fixing the scheduled runs). desk_check.js clicks the research presets on #screener, but they moved to the Research tab in 2105c73, so it times out on the current page; changing `#screener` to `#research` in it makes it pass.

## 16 Nov: Evidence Desk, formula lab (Agent C)
- tech_model.py now also writes `data/formula-sample.csv` (one try/except step after the chart data): about 20,000 rows sampled evenly over time and stocks, fixed seed. Columns: date, rsi, adx, st (1 = Supertrend up), macd (1 = above signal), vs50, vs200, hi52, rs3, volx, atr_pct, mkt (1 = Nifty above its 200-day average), score, y = 10-session return minus the Nifty's, in %. Rows from the last 10 sessions (no y yet) and rows near a 40%+ one-day jump are left out.
- `score` is the technical part of research.py's score (+2 per tested signal new in the last 3 sessions, -2 per tested warning), using today's tested list. The value, fundamental and Monte Carlo parts have no history, so they are not in it. Today's tested list was decided on the last 2 years, which overlaps the test period: this favours the baseline, so it makes the formula's test harder, not easier.
- New `scripts/dhan_refresh/formula_lab.py` and weekly `.github/workflows/quant-lab.yml` (Saturday 11:00 IST, no Dhan secrets, 45 min). Split by date: first 70% train, 10-session gap, last 30% test. PySR on at most 5,000 train rows, + - * / only, size 15, MAE loss, 20 minutes, seed 7. Every formula on the front is scored on the test period: each day the top fifth by the formula, excess = that stock's y minus the day's average y; t = t-statistic of those excesses, hit = share above the day's average. The simplest formula within 10% of the best t is chosen and compared with `score` (or, without one, the single readout that ranked best on the train period). `docs/formula.json` verdict: beats_score (t at least 2 and above the baseline), no_better, or failed. The formula never replaces the live score.
- Not done: PySR could not be installed in the build sandbox (Julia download blocked), so the real search runs only in the workflow; tests use a stub equation table. No workflow commits `data/formula-sample.csv` yet: add it to the commit lists in dhan-refresh.yml and tech-model.yml, or quant-lab.yml exits with "nothing to do".
## 16 Nov: Evidence Desk, risk lab (Agent B)
- New `scripts/dhan_refresh/risklab.py`, called from tech_model.py before tradeplan.run (in try/except). Writes `docs/risklab.json`: vol (GJR-GARCH(1,1) skew-t on the last 1,000 sessions, 1- and 5-day forecasts, persistence; EWMA fallback named in "model"), var (Nifty 50: 1-day 95% / 99% VaR from the GARCH forecast, Kupiec on the last 250 sessions with parameters fitted only on earlier data), conformal (MAPIE split conformal, 21-session return range at 90%, chronological split with a 21-session gap, measured coverage next to the target). All vol, VaR and range numbers are fractions of price (0.02 = 2%), which is what tradeplan.py reads for d1.
- Saturdays or `--full` only: signals (stationary-bootstrap interval on each signal's mean out-of-sample 10-day excess return; SPA p-value for the family and StepM at 5% decide "survives"), track (bootstrap interval per live score band once 30+ picks are graded at 21 days), pairs (Engle-Granger re-test of the pairs quant.pairs_scan considers: counts and a one-line verdict, no trades). Weekday runs carry the last full results over and say so in notes.
- tech_model.backtest takes an optional `series` dict and fills it with each signal's out-of-sample cases by date; tech-model.json is unchanged.
- Workflows install arch 9.0.0, mapie 1.6.0, scikit-learn 1.9.1 (resolve on Python 3.11 with numpy 2.1.3). Any missing library is noted and skipped; the nightly job does not fail.
- Runtime on synthetic data (11 years, this machine): 50 stocks 4.2 s nightly / 5.7 s full; 500 stocks 23.1 s nightly / 24.6 s full. Not yet run on the real Dhan history.

## 17 Nov: Evidence Desk, page integration (Agent D)
- Tabs now read Screen, Analyze, Plan, Proof. The research screener is the first section of Screen; old #screener, #research (scrolls to it) and #analyze links still work.
- Plan: a sortable table of every plan in tradeplan.json (stock, signal, entry, stop, target, chance of target, expected rupees after charges, shares, checks passed). Failing rows are greyed with the failing checks under the stock name; a line above says why no plan passes (today all 135 fail the many-signals test because risklab.json has no signal results yet). The capital / max-loss line reads config/trading.json (own values) and flags the daily loss limit as an example. Tapping a row opens the stock in Analyze.
- Proof: (a) signals with their tested 10-day excess return (tech-model.json), the risk lab's 95% interval as a bar and a "survives" badge, headline "N of M signals survive..."; (b) for the selected stock: GARCH volatility forecast, GARCH vs historical 1-day VaR with Kupiec, the 21-session conformal range with target and measured coverage (the lab stores no realised volatility, so no forecast-vs-actual line); (c) the chosen formula, its out-of-sample t and hit rate against the score, the verdict in words, the candidate formulas; (d) live record bands against the score-0 control, or "First grades due about 1 Dec 2026". risklab.json and formula.json are optional (read next to the page first, else docs/); a missing file shows "Not computed yet" in its panel only.
- desk_page.py: risk-lab per-stock numbers and the US weekly closes now travel in d/*.json; results.json is trimmed to the fields the page shows. desk_check.js also visits #plan and #proof, clicks a plan row, and exits 1 on a console error or sideways scroll at 400 and 1100 px.
- Not done: the page is 1.22 MB (was 1.32 MB before this change), still over the 1 MB target. The rest is screener data the page needs on load (research.json 379 KB, tech-today 123 KB, stock index 115 KB); getting under 1 MB means loading the screener lazily, which is a separate change.

## Order of work now
1. Monday 16 Nov: check the first live order-flow session, Telegram replies from the live job, and the nightly run (Monte Carlo and VaR for NIFTY are new).
3. Once 4+ weeks of option snapshots and live flow exist, back-test the options and order-flow signals.
