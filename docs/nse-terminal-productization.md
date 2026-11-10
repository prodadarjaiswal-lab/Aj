# NSE Terminal: from personal tool to product

Date: 2026-11-10 · Source artifact: NSE Terminal (data as of 2026-11-10 12:55 IST)
Council verdict: `sessions/2026-11-10-productize-nse-terminal/verdict.md`

## 1. Re-run check

All 9 sections were rendered in headless Chromium with **0 JavaScript errors**.

| Section | Renders | Note |
|---|---|---|
| MARKET | 11 panels | brief, sectors today, headlines, events, flows |
| SECTORS | 3 panels | heatmap, all sectoral indices, what changed |
| SCREENER | 6 panels | includes "PICKS" and "AVOID" panels (a compliance risk, see §4) |
| CHART | 6 panels | chart, quote, signal, news, technicals, results |
| RESEARCH | **0 panels** | renders almost empty without input; needs checking |
| VALUATION | 10 panels | five models: the strongest asset |
| NEWS | 1 panel | stock, market and NSE filings |
| MACRO | 6 panels | USDINR, G-sec, UST, Brent, CPI |
| METHOD & SOURCES | 13 panels | ready-made compliance appendix |

The data was **not** refreshed. Yahoo is blocked by this environment's network, and the Dhan connector needs an interactive login. The page still shows the 12:55 IST intraday snapshot, not today's close.

## 2. What the council decided

Don't build the ₹299 retail app. Run two lanes:

1. **Front door (free):** an education-only daily Nifty brief made from the MARKET, SECTORS and MACRO sections.
2. **Paid product:** a white-label terminal and research-report generator for **SEBI-registered Research Analysts**, starting with a ₹10k refundable 30-day pilot and moving to a ₹10k / ₹25k / ₹50k ladder.

A lawyer's written opinion comes before the first rupee.

## 3. Competitors

| Player | What they own | Gap you can use |
|---|---|---|
| Screener.in | Free fundamental screening (the default) | No narrative, no valuation story, no white-label |
| Tickertape | Beginner-friendly retail app | Retail-priced, no RA tooling |
| Trendlyne | Deepest screener and analyst data | Built for end investors, not for RAs' client reports |
| StockEdge | Scans and sector rotation | Same |
| Stoxo (StockGro), Multibagg AI, Swastika Sarthi | 2026 AI chat research for retail | Crowded ₹0 to ₹700/month retail wallet, the same fight as option B |
| Groww / Zerodha / Dhan | Distribution (Groww is now the #1 broker by active clients) | They sell execution. Their AI shows up in support, not in RA research |

In this quick search I did not find a white-label RA terminal plus report generator. Verify that before pitching it as "first".

What is selling right now: AI-branded research layers on top of public filings, with tiered question quotas (for example, 20 free questions a month and 500 on premium). After SEBI's retail algo framework (full effect April 1, 2026), compliance tooling is in demand. Black-box algo providers need RA registration and a research report per strategy. Your METHOD & SOURCES and VALUATION sections already look like that report.

## 4. Section by section: use case, connectors, skills

| Section | Product use | Connectors | Skills |
|---|---|---|---|
| MARKET | Free daily brief (lane 1) | Dhan (prices), FMP and Alpha Vantage (global markets, FX, commodities), Aiera (events, transcripts) | `nse-day-trader` (morning brief), content skills (`viral-hook-writer`, `reel-scripter`, `caption-and-hashtags`, `content-calendar`) |
| SECTORS | RA weekly sector note | MoSPI (official IIP, CPI, GDP), Dhan | `xlsx` for the RA's data pack |
| SCREENER | **Rename "PICKS/AVOID" to "rule-based screens"** in anything public. Picks appear only inside the RA's signed output | Dhan | `trader-scanner` patterns |
| CHART | Client-ready chart pack for the RA | Dhan historical data | `trader-entry`, `trader-exit`, `trader-timemachine` (paper only) |
| RESEARCH | Q&A per stock, capped with a monthly quota like the competitors | Aiera (transcripts, filings), Firecrawl (NSE pages) | `deep-research` for paid tiers |
| VALUATION | **Core of the paid product:** an RA-signed research report generator | FMP statements, Aiera financials | `docx` / `pdf` to export a signed report with the RA's letterhead |
| NEWS / filings | Alerts on the RA's coverage list | Firecrawl monitors (NSE announcements), Gmail (draft digests, never auto-send to clients) | `trader-news` pattern |
| MACRO | Macro panel in every report | MoSPI, Alpha Vantage (FX, Brent, yields) | `dataviz` |
| METHOD & SOURCES | Compliance appendix and algo "research report" pack | n/a | `docx` |
| Distribution | Reels and brief videos | Metricool (scheduling), Canva, HyperFrames, Higgsfield/Kling (video, paid credits: use last) | content skills |

## 5. Credit control: the Advisor tool pattern

The council itself ran this way. The four seats ran on a cheaper model, and the chair and verdict ran on the stronger one.

For the product's daily pipeline, use the Claude API advisor tool (beta `advisor-tool-2026-03-01`):

- **Executor:** a cheaper, faster model does the mechanical work: fetch, compute indicators, fill templates for 50 stocks and N RA clients.
- **Advisor:** the stronger model is called only for judgment: the market brief narrative and the valuation story. It is capped with `max_uses`.
- Count advisor calls on the client side and drop the tool from `tools` when today's budget is spent.
- Read `usage.iterations` (`type: advisor_message`) to log advisor spend separately, then add up a daily cost per RA client. That number decides whether ₹10k a month is profitable.

```python
tools = [{"type": "advisor_20260301", "name": "advisor",
          "model": "claude-opus-5-5", "max_tokens": 1024, "max_uses": 2}]
resp = client.beta.messages.create(
    model="claude-haiku-5-5", max_tokens=4096,
    betas=["advisor-tool-2026-03-01"], tools=tools,
    messages=[{"role": "user", "content": brief_task +
               "\n(Advisor: keep guidance under 80 words.)"}])
```

Other ways to save: cache the static METHOD text with prompt caching, and run per-stock work through the Batch API. Check current pricing in the `claude-api` skill before you set prices.

## 6. Next 7 days
1. Publish brief #1. Change "PICKS/AVOID" to neutral screen labels first.
2. Send free samples, each branded to that RA, to 20 SEBI-registered RAs. Book 5 calls and ask for the ₹10k pilot on the call.
3. Book a one-hour SEBI lawyer opinion.
4. Automate the daily refresh so it takes minutes, not an hour.

Sources: [VestAI](https://www.vestai.io/learn/best-ai-stock-analysis-tools-india), [Tapetide comparison](https://tapetide.com/compare/screener-vs-tickertape-vs-trendlyne), [Arthneeti cost survey](https://www.arthneeti.com/best/stock-research-tools-cost-india), [Multibagg pricing note](https://www.multibagg.ai/feeds/ai-stock-research-tool-cost-cmum7o0c100000agmtnznmuvf), [Stoxo launch](https://www.tribuneindia.com/news/accurate/stockgro-launches-stoxo-indias-first-stock-market-ai-research-platform-that-turns-confusion-into-conviction), [Liquide on SEBI algo rules](https://blog.liquide.life/sebi-algo-trading-regulations-2026/), [Sansa Legal](https://www.sansalegal.com/post/sebi-algorithmic-trading-framework-2026-what-retail-traders-in-india-must-know), [Groww/Dhan share](https://www.pulse.bot/fintech/news/groww-surpasses-13-cr-active-users-in-april-dhan-continues-strong-growth-e424a2c6-1e28-4fbd-946a-b06179bec8d0/). These are mostly secondary or vendor sources; verify SEBI rules against the circular itself.
