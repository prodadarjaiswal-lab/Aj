# How to hedge a stock position (research note, 13 Nov 2026)

Used by the Telegram bot's `hedge` reply. Order follows the owner's brief: asset classes first, then market/sector versus company risk, then the stop-loss.

## Framework (Damodaran)
- Equity risk splits into market risk, which diversification cannot remove, and company-specific risk, which it can (Investment Philosophies, Session 4 "Equity Risk", in the owner's Drive).
- Decide which risks to hold, which to hedge and which to seek. Hedge at the portfolio level, and don't hedge away the exposure you bought the stock for: "An oil company that hedges against oil price risk is undercutting that bet." ([Corporate Hedging: The Down Side](https://aswathdamodaran.blogspot.com/2008/11/corporate-hedging-down-side.html))
- Think about currency risk across the whole portfolio rather than stock by stock: "As an investor with stakes in both Coca Cola and Boeing, I think about exchange rate risk in my overall portfolio (which I can choose to hedge if I want to) rather than in individual companies." (same post)
- Hedging is never free. The question is what it costs against what it protects.

## 1. Across asset classes and countries (first)
- **Gold** is a collectible: it "cannot be valued … but it can be priced" ([Damodaran, 2017](https://aswathdamodaran.blogspot.com/2017/10/the-bitcoin-boom-asset-currency.html)). Treat it as insurance, not as a source of return.
  - In the 2025 tariff selloff, gold "held [its] own" ([2025](https://aswathdamodaran.blogspot.com/2025/04/anatomy-of-market-crisis-tariffs-rock.html)).
  - In 2008 the Nifty fell about 52% while gold in rupees rose about 28% ([JAAFR](https://rjwave.org/jaafr/papers/JAAFR2606427.pdf)).
  - Other studies find only a weak inverse correlation, so gold does not offset every fall.
- **Rupee and US exposure:** foreign-investor selling tends to push the rupee down while Indian stocks fall, so US holdings (for example Nvidia) gain in rupee terms. That works as a partial hedge, but only if the US holdings are diversified.
- **Liquid or government bond funds** cut drawdowns simply by being outside equities.

## 2. Within equities: market and sector risk versus company risk
- **Whole market or sector falling:** a stock-level put or stop protects only part of the loss. Use an index or sector hedge.
  - Size: hedge notional = beta × position value.
  - NSE lot sizes: Nifty 65 and Bank Nifty 30 (from January 2026, [NSE circular](https://nsearchives.nseindia.com/content/circulars/FAOP70616.pdf)).
  - Each index contract is worth ₹15–20 lakh ([SEBI](https://www.sebi.gov.in/sebi_data/commondocs/dec-2024/RE_Chapter%205%20-%20Exchange%20Traded%20Derivatives%20FINAL_1_p.pdf)), so it fits only larger portfolios.
- **Company-only bad news** (results, scandal, regulation): an index hedge does nothing.
  - Use a protective put on the stock, a collar (buy a put, sell a call above to fund it, which caps the upside), or exit.
  - Only stocks in NSE's F&O list have options.
- **Put cost** rises with implied volatility, which is highest before results and in panics.

## 3. Stop-loss (last line, always)
- **Types:**
  - ATR-based, e.g. 2 × ATR(14) below entry
  - Structure-based, below the last swing low or support
  - Time stop
  - Trailing stop
- **Gaps:** a stop does not protect against an overnight gap. The order fills at the open, below the stop. When a gap is likely (results, news), a put is better protection than a stop.
- **Sizing:** shares = (capital × 0.5–1%) ÷ (entry − stop). Set the stop from the chart or ATR first, then size the position to it.
