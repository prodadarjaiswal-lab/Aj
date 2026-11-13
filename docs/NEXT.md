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

## Done on 14 Nov (02:20 to 02:40 IST)
- Bot verdicts use only the signals that passed for the current market (rising or weak).
- The back-test runs every trading night inside the nightly refresh, using the same Dhan login. Signals are promoted or dropped automatically, with a Telegram notice.
- First real run of the 20-signal back-test on 497 stocks: 6 signals pass in rising markets, none in weak markets.
- New output files:
  - `docs/technical-desk.md`
  - `docs/auction.json` and `docs/auction-desk.md`: order flow and auction from 1-minute bars
  - gamma exposure fields in the options snapshot
  - `docs/journal.md`
- Pinned Claude Project instructions and setup steps are in `docs/claude-project/`.
- The Dhan jobs send a Telegram message when they fail. The US tracker waits for any other Dhan job before it logs in.

## Open
- The Telegram description and menu update the next time a price job starts (Monday 09:07 IST).
- Order-flow levels are context only until they are back-tested. Next: test VWAP reclaim, Initial Balance extension and value-area acceptance on 1-minute history.
