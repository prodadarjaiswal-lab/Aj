# Work queue (resume here)

The owner's brief (13-14 Nov 2026): a strong, tested technical model; a curated Telegram bot with six commands; a hedge reply ordered as asset classes, then market/sector vs company risk, then stop-loss; pinned Claude chats (query and journal); a Dhan setup that does not fall over; a TCS example.

## Done
- `scripts/dhan_refresh/tech_model.py`:
  - 20 candidate signals.
  - 6-year out-of-sample back-test on Dhan data, run separately for rising and weak markets.
  - Signals are promoted or dropped automatically, with a Telegram notice.
  - Today's signals plus a full indicator readout are written to `docs/tech-today.json`.
  - Runs weekly (`.github/workflows/tech-model.yml`); the nightly refresh runs it with `--with-tech`.
- First back-test (13 signals): the tested ones in rising markets were `hi52v` (strongest, +1.4% vs Nifty over 10 days out-of-sample), `volbreak` and `nr7`. The 7 newer candidates have not been back-tested yet.
- `scripts/dhan_refresh/bot.py` now has six commands: price, SYMBOL (trade), value, hedge, top, alert. Replies are curated and the hedge reply follows the agreed order. Every stock asked about is journalled.
- `docs/hedging-research.md`: Damodaran, the owner's Drive notes, NSE and SEBI sources.

## To do
1. Make the bot's verdicts use the signal set for the current market: `tested` in rising markets, `tested_weak` in weak ones (`technical()` and `top()`).
2. Dispatch `tech-model.yml`; check the new candidates and the Telegram re-test notice.
3. Write `docs/technical-desk.md` for the pinned chat:
   - a model scoreboard;
   - one line per stock with the indicator readout and its tested signals.
   - Regenerate it nightly and weekly.
4. Journal: nightly, copy the bot journal (branch `bot`, `bot.json`) to `docs/journal.md` on main.
5. Two pinned Claude Project chats, "Stock Query" and "Journal". Write `docs/claude-project/*.md` (instructions, and which repo files to sync) plus setup steps for the owner.
6. Dhan robustness:
   - Telegram alert when the live feed, the US tracker or the nightly refresh fails.
   - Test a login conflict and recovery.
7. Confirm the Telegram description and menu updated: `bot.py menu` runs at job start.
8. Show the owner the TCS example (price, trade, value, hedge) and summarise.
