# NSE Terminal: section and code audit, and the RA Desk build

Original: https://claude.ai/artifact/JBe9w1vLcwPQFyfmYHoRDz (restored, unchanged)
Sellable version: https://claude.ai/artifact/NozVppNYRWpA74XNktQmCE (copy: `docs/ra-desk.html`)

## What is in the file
- 2.1 MB HTML. About 1.9 MB is embedded data (`NSET`, `RES`, `TERMDATA`): 50 stocks with OHLC, technicals, valuation, quarterly fundamentals, news and filings; 15 indices; sector P/E history; return decompositions; back-tests; FII/DII flows; macro series.
- About 800 lines of JS in 9 views and 21 sub-views (`SUBF`), plus charts (Lightweight Charts from a CDN) and a live Dhan price poll through `window.claude.use("mcp")`.

## Verdict per section
| Section | Main code | Verdict | Why |
|---|---|---|---|
| VALUATION: story, five models, sustainable value, scoreboard | `vstory`, `sus`, `score` | **Hot, the moat** | Reverse valuation ("what the price assumes"), five models with back-tests and a scoreboard. Screener, Tickertape and Trendlyne do not tell this story. |
| RESEARCH: this stock / the market | `rstock`, `rmkt` | **Hot** | Rule-based plain-English "what is going right / slipping" with evidence. It reads like AI but runs with no LLM cost per view. |
| SECTORS: what changed | `chg`, `dec` data | **Hot for content** | Splits each index move into book, ROE, growth, rates and premium. Unique, and it explains the market in a way that works as content. |
| SCREENER: picks / playbook | `picks`, `regimeText`, `role` | Valuable but risky | Regime-aware lists tested on 167 stocks from 2008 to 2026. In public they read as tips; they are safe only inside an RA's signed workflow. |
| SCREENER: board, screener, technicals | `board`, `scr`, `tech` | Useful, commodity | Everyone has screeners. Keep it as plumbing. |
| MARKET: brief, global and flows, events | `brief`, `globalv`, `evt` | Useful | Raw material for the daily education-only brief. |
| CHART desk | `chart`, `dtech`, `dres` | Commodity | TradingView, Dhan and Kite do charts better. Keep it for context only. |
| NEWS and filings | `news`, `stockNews` | Useful | Tagged NSE filings and news per stock. Good for alerts. |
| MACRO | `macro` | Commodity | Context panel. |
| METHOD & SOURCES | `basis` | **Underrated** | A ready compliance and methodology appendix. |
| Live Dhan feed | `livePoll` | Useful, **currently off** | The page calls the `mcp` capability without declaring it, so live prices never connect. |

## Issues found in the original
1. **Today's bar repeats yesterday's close.** The 2026-11-10 close equals the 2026-11-09 close for every index, so "today" changes show 0.00%. RA Desk's client brief skips repeated bars and labels the real close date.
2. **The live feed cannot run** until the page declares the `mcp` capability (Dhan). The owner has to decide to enable it.
3. **Charts and Research need the CDN.** In an offline test the Research view is empty because Lightweight Charts did not load. On claude.ai it loads.

## What RA Desk adds (built on a copy; the original is untouched)
- **White-label:** firm name, SEBI RA number, analyst and disclosure text (FIRM SETUP). These brand the top bar, notes and briefs.
- **RESEARCH NOTE builder:** pick a stock and the sections to include (snapshot, right/slipping, valuation, technicals, results, filings). The RA writes the view and chooses any rating; the tool defaults to "Not rated". It then takes holdings and conflict disclosures and a sign-off. A DRAFT watermark shows until the note is signed, and Print / Save PDF uses a light letterhead layout.
- **CLIENT BRIEF:** a one-click, education-only daily text built from indices, breadth, sectors, flows and events. It has no stock calls and includes a disclaimer, with a copy button for Telegram, WhatsApp or email.
- **PLANS:** the sales page, with Pilot ₹10k, Desk ₹10k/mo, Desk+Notes ₹25k/mo, Strategy pack ₹50k/mo and setup, plus how it stays compliant.
- **Renames:** Picks to Screens, Avoid to Weak trend / Weak in falls. "RA USE ONLY" tag in the top bar.

## Next build steps (only after a pilot pays)
1. A daily refresh job after 15:30 IST, with the data split out of the HTML into JSON per day.
2. A config file per RA (logo, colours, coverage beyond the Nifty 50) and hosting per RA.
3. A server-side sign-off log (an audit trail) instead of browser storage.
4. Declare the `mcp` capability, or use a server-side Dhan key, for live prices.
