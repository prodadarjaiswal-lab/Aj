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

1. ✅ **Always-on bot.** The repo goes public, so Actions minutes are free. `bot-listener.yml` runs 24/7 as back-to-back runs, queued by a 30-minute schedule.
   - It long-polls Telegram and answers from the latest data, with live Dhan prices taken from the `live` and `us-watch` branches.
   - The price jobs stop polling Telegram, so updates are not consumed twice, and reload alerts every minute.
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
4. ✅ **Technical Desk in two parts:**
   - **Screener:** rising, dips, bargains, the tested signals and the original terminal's screens.
   - **Analyzer:** for one stock, the technical verdict, auction and order flow, options, news, value and hedge.
   - Better charts throughout.
5. ✅ **Refresh cadence:** hourly 09:25-15:25 IST (terminal and desk), 18:27 terminal, 22:37 desk. the terminal and the desk republish at the open (09:25), hourly during the session and after the close.
6. ⬜ **Self-check:** the live track record of the bot's picks (built), plus weekly re-tests. Signals that stop working are dropped automatically (built).

## Order of work now
1. The owner switches the repo to public (only they can).
2. Monday 16 Nov: check the first live order-flow session, the listener, and the nightly run with markets, auction and track record.
3. Once 4+ weeks of option snapshots and live flow exist, back-test the options and order-flow signals.
