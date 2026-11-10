# DhanHQ API: notes for RA Desk
Source: DhanHQ API documentation full export (generated 2026-10-27, 159 docs, about 10.9k lines). API v2.6 (Aug 10, 2026).

## The parts RA Desk needs (all Data APIs; need an active Dhan Data Plan)
| Need | Endpoint | Notes |
|---|---|---|
| Daily history | POST /v2/charts/historical | OHLCV back to inception; `toDate` is non-inclusive; epoch timestamps |
| Intraday history | POST /v2/charts/intraday | 1/5/15/25/60 min, last 5 years, OI optional |
| Snapshot prices | POST /v2/marketfeed/ltp, /ohlc, /quote | ≤1,000 instruments per call, 1 call/sec across all quote endpoints |
| Fundamentals | POST /v2/data/companyinfo | metrics `CO` (mcap, EPS, EBITDA, book value, 52w), `RATIOS` (PE, PB, D/E, ROE, ROCE, PE vs sector, industry averages), `SHP` (promoter/FII/DII/public and quarter-on-quarter change) |
| Indicators | POST /v2/data/technical | SMA/EMA 5–200, RSI, MACD hist, Stoch, StochRSI, ATR, ADX, UO, ROC, W%R, pivots; timeframe 1/5/15/D; EQUITY or INDEX |
| Movers | POST /v2/data/marketmovers | equity PRICE_GAINERS/LOSERS, universe e.g. NIFTY_50, limit ≤100; F&O OI/volume rankings |
| News | POST /v2/data/newsheadline | ≤50 items, 19 categories, filter by stockList or PORTFOLIO/WATCHLIST |
| Live stream | wss://api-feed.dhan.co?version=2&token=…&clientId=…&authType=2 | binary, little-endian; ticker/quote/full packets; 5 sockets × 5,000 instruments; ≤100 per subscribe message; ping every 10s, drops after 40s silence |
| Security IDs | https://images.dhan.co/api-data/api-scrip-master.csv (or -detailed) | map NSE symbols to securityId; detailed CSV has ISIN, ASM/GSM flag, lot size, tick size |
| Token check | GET /v2/profile | validates token, segments and Data API subscription |

## Auth facts that shape the design
- Access token lasts **24 hours** (a SEBI-driven change in v2.4). Options:
  - Manual: generate on web.dhan.co. Renew while still active: GET /v2/RenewToken.
  - Automated: TOTP (POST auth.dhan.co/app/generateAccessToken with client ID, PIN and TOTP).
  - API key + secret (valid 12 months): consent, browser login, consume consent.
- Static IP is required **only for order placement/modify/cancel**. Data APIs do not need it. RA Desk is research-only, so no static IP is needed.
- Partner program (partner_id/secret, the user logs in through your app) is how a platform serves *other people's* accounts. Apply via a form on dhanhq.co.

## Limits and errors
- Data APIs: 5 req/s, 100,000/day. Orders: 10/s, 7,000/day. Option chain: 1 per 3s per underlying, 10 unique per 8s.
- Data errors 800–814 (807 token expired, 806 not subscribed, 804 too many instruments). Trading errors DH-901…910. Rate limit RL001 means back off.

## Other things in the docs (not needed for RA Desk)
- **Trading:** orders, super orders (entry + target + trailing SL), conditional/multi orders on indicator triggers, slice orders, kill switch, P&L-based exit, exit-all, eDIS, postback webhooks, live order-update WebSocket.
- **Market data extras:** option chain with Greeks, expired options (5y rolling with IV/OI), 20/200-level depth, Closing Auction Session feed (Pro Traders plan).
- **Global (US) stocks:** trading API and live feed.
- **Sandbox** at sandbox.dhan.co/v2 (orders, portfolio and history endpoints only; separate token from cloud.dhanhq.co).
- **Dhan Cloud:** hosted Python strategy runner (1 vCPU/3 GB, credits, 100 free; `{{VAR}}` secrets; no files or env vars; outbound HTTP allowed; AI code scanner; no static IP needed).
- **DhanHQ Agent Skills** (`npx skills add dhan-oss/dhanhq-skills --skill dhanhq`): order guardrails, backtesting, ScanX scanner.
- **Dhan MCP** at https://mcp.dhan.co/mcp (OAuth): portfolio, orders, market data, historical, margin, alerts, search. This is the same tool family as the connected DHAN connector.

## Caveats
- The Python SDK (`dhanhq`) shown in the docs has no wrappers for the v2.6 Market Analytics endpoints (companyinfo, technical, marketmovers, newsheadline). Call them with plain HTTP.
- The docs do not cover **redistributing Dhan data to third parties**. Selling RA Desk built on your personal Data Plan may need Dhan's partner agreement. Ask Dhan before charging.
