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
- ⬜ **Technical terminal (web page).** The terminal split into a Value part and a Technical part, with charts.

## C. Order flow and auction
- ✅ VWAP and anchored VWAP with bands, reclaim and loss (exact, from Dhan 1-minute bars).
- ✅ Volume profile: session and 5-day composite, POC, VAH, VAL, HVN and LVN (derived).
- ✅ Market Profile / TPO: value area, Initial Balance and its extension, single prints, excess and poor highs and lows (exact).
- ✅ Auction read against yesterday's value: acceptance or rejection.
- ✅ Gamma exposure, gamma flip and strike concentrations (derived from the option chain).
- 🟡 Delta and absorption: an estimate from 1-minute bars. Next: tick-level data from Dhan's WebSocket "full" packets, which carry last traded quantity, total buy and sell quantity, and 5-level depth.
- ⬜ Live order flow from the Dhan WebSocket: trade tape built from tick changes, aggressor side from price against bid/ask, depth imbalance, large prints, buying and selling pressure. Alerts to Telegram.
- ⛔ True footprint and exchange time-and-sales: Dhan sends snapshots, not every trade with its side, so these can only be approximated. Every such output is labelled as an estimate.
- ⬜ Back-test of the auction signals (VWAP reclaim, Initial Balance breakout, value-area acceptance) on Dhan 1-minute history. Until then they are context only.
- ⬜ Visualisations (profile, VWAP bands, gamma by strike) and a replay of past sessions.

## D. Hedging
- ✅ Order: asset classes → market/sector vs company risk → stop-loss. Built on Damodaran (Drive notes and blog) and NSE/SEBI rules (`docs/hedging-research.md`).
- ⬜ Company risk should also check recent news and filings. If there is adverse company news, the reply should say so and lean towards a stock put or an exit.

## E. Pinned Claude chats
- ✅ Instructions for "Stock Query" and "Stock Journal" Projects, with setup steps (`docs/claude-project/`).
- ⛔ I cannot create Claude Projects for the owner. The owner sets them up once, about 5 minutes.

## F. Dhan reliability ("must not collapse")
- ✅ Every Dhan job messages Telegram when it fails.
- ✅ The US tracker waits for other Dhan jobs and logs back in after a conflict.
- ⬜ The NSE live feed currently **stops for the rest of the day** if anything else logs in to Dhan. It must log back in unless a newer live job has taken over.

## G. Earlier requests, still standing
- ✅ Nvidia tracked via Dhan's US feed, with alerts.
- ✅ NSE alerts, morning brief and close summary.
- ✅ Hourly and nightly terminal republish (scheduled tasks).

## Order of work now
1. F: NSE live feed recovers from a login conflict.
2. D: news and filings check in the hedge reply.
3. C: back-test the auction signals on 1-minute history.
4. B: Technical terminal page.
5. C: live WebSocket order flow with alerts.
6. C: visualisations and replay.
7. B: candidates file for new measures.
