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
- ⬜ Quarterly results growth from NSE XBRL filings (one call per stock; not built yet).

## Order of work now
1. Monday 16 Nov: check the first live order-flow session, Telegram replies from the live job, and the nightly run (Monte Carlo and VaR for NIFTY are new).
3. Once 4+ weeks of option snapshots and live flow exist, back-test the options and order-flow signals.
