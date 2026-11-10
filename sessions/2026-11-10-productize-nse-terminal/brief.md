# Brief: what to build out of the NSE Terminal

**Decision:** how to turn the NSE Terminal (a single-page research tool, already built) into software people pay for, on a budget.

**What exists today:** one HTML page, about 2 MB, rebuilt by Claude with live data. It has 9 sections. MARKET has the brief, global markets, FII/DII flows and events. SECTORS has a heatmap, valuations and what changed. SCREENER covers Nifty 50 picks and technicals. CHART is a trading desk with results. RESEARCH holds Q&A on each stock and the market. VALUATION runs five models with backtests. NEWS covers each stock, the market and NSE filings. MACRO tracks USDINR, yields, Brent and CPI. METHOD & SOURCES explains the data. Prices come from Dhan, news from Google News RSS, and filings from NSE. The page covers 50 stocks and 15 indices. A daily refresh costs Claude credits plus about 1 hour of founder time (assumed).

**Options**
- **A. Don't productize.** Keep it a personal and portfolio tool. Spend nothing.
- **B. B2C "AI research terminal"** for Indian retail investors and traders at ₹299 to ₹499 a month, with education and research only, no buy/sell tips. It would compete with Tickertape, Trendlyne, Screener.in, StockEdge, and new AI entrants (StockGro Stoxo, Multibagg AI, Swastika Sarthi). Typical retail spend on research tools is ₹0 to ₹700 a month.
- **C. B2B white-label for SEBI-registered Research Analysts, sub-brokers and finfluencers.** Their branded daily terminal, a client research-report generator and an algo "research report" pack would cost ₹8,000 to ₹25,000 a month per firm. SEBI's retail algo framework (full effect from Apr 1, 2026) requires black-box algo providers to hold RA registration and keep a research report per strategy, so RAs have a compliance-shaped need.
- **D. Smallest version first.** Ship a free public daily "Nifty brief" page with the Telegram/WhatsApp/X distribution the existing skills automate (reels, captions, calendar, Metricool scheduling). Build an audience for 60 days, then sell B or C to whoever shows up.

**The business (assumed):** solo founder, pre-revenue, India-based, technical enough to work with Claude Code. Connectors already in place: Dhan, FMP, Alpha Vantage, Aiera, Firecrawl, Apify, Gmail, Drive, Canva, Higgsfield/Kling (video), Metricool (social scheduling), GitHub. Skills already in place: nse-day-trader, trader-* suite, content skills, Roast Room.

**Resources (assumed):** under ₹50,000 cash to spend in 90 days, about 15 founder hours a week, and an AI-credit budget capped at 20% of the daily allowance.

**Success (assumed):** ₹1 lakh MRR or 10 paying B2B accounts within 6 months, with no SEBI violation.

**Founder lean (assumed):** B. "Everyone wants an AI stock app." The council should test that lean.

**Constraint the council must respect:** giving buy/sell recommendations to the public for a fee requires SEBI RA registration. The founder is not registered (assumed).

## Weights (quick mode, 4 seats)
| Seat | Weight | Why |
|---|---|---|
| Graham | 3 | The core question is real demand in a crowded category |
| Hormozi | 3 | Pricing and who pays decide B vs C |
| Gary V | 2 | Option D is a distribution bet |
| Buffett | 2 | Downside: regulatory risk and cash burn |
