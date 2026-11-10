# Research: using options data to validate screener picks

Goal: inside the Screener (no separate options tab), check every stock pick against what the options market is pricing, so a recommendation is consistent with real positioning and realistic moves, not just a chart pattern.

Principle: **options veto and calibrate; they do not generate picks.** A pick is never upgraded on options alone. Options can lower its rank, mark it as "contradicted", or change its target, stop or horizon.

## Data we can get
- **Live, through the Dhan connector** (tested 10 Nov 2026):
  - Option chain per expiry for indices (`IDX_I`) and F&O stocks (`NSE_FNO`), with LTP, OI and IV for calls and puts at every strike.
  - Expiry lists (NIFTY weekly on Tuesdays; stocks monthly: RELIANCE 23 Nov, 29 Dec, 25 Jan).
  - The connector's text output does **not** include Greeks. Compute them from IV with Black–Scholes, or take Dhan's official end-of-day Greeks from the REST API in the nightly job.
- **Nightly, through the Dhan REST API:**
  - Option chain with Greeks, at 1 request per 3 s and 10 unique underlyings per 8 s. About 45 F&O names take about 3 minutes.
  - Futures daily candles with OI (`oi: true`).
  - **Expired-options rolling data** (5 years; IV, OI, spot; ATM ±3 strikes for stocks). This lets us **backtest** every gate below on NSE data.
- **Data quality** (seen in the live pulls):
  - ITM call IVs come back as 0.0.
  - Far strikes show IV of 0, or junk values above 150%.
  - Rule: use only out-of-the-money options on each side, with OI > 0, LTP > 0 and IV between 3% and 150%.

## The gates

### Gate 1: Is it usable?
- The stock is in F&O.
- ATM call and put both have OI above a floor (for example, the top 70% of the stock's own strikes) and a live LTP.
- Otherwise the result is "— no options check".

### Gate 2: Is the target realistic? (the strongest and simplest)
- **Expected move to expiry** = (ATM call + ATM put) price ÷ spot. This is the market's ±1-standard-deviation move, roughly.
- **Target check:**
  - target distance ≤ 1× expected move: realistic;
  - 1–1.5×: stretch;
  - above 1.5×: unrealistic for that horizon. Lengthen the horizon or cut the target.
- **Stop check:** a stop closer than about 0.5× the expected move is likely to be hit by noise.
- **Probability:** the option delta at the target strike ≈ the market's probability of *finishing* beyond it. The probability of *touching* it is roughly twice that. Both are standard risk-neutral approximations, not forecasts.
- Live example, RELIANCE on 10 Nov (spot 1,324.40, 23 Nov expiry): ATM straddle 25.00 + 20.25 = 45.25, so **±3.4% (about 1,279–1,370)** priced over about 8 sessions. A long call with a 1,400 target by 23 Nov would be marked "stretch / unrealistic". This is an illustration, not a recommendation.

### Gate 3: Does informed money agree? (academic evidence, US stocks)
| Signal | How to compute | Evidence | Direction |
|---|---|---|---|
| **Call–put IV spread** | ATM call IV − ATM put IV (or the average across matched strikes) | Cremers & Weinbaum (2010, JFQA); also a call–put IV spread arbitrage-portfolio paper (Lancaster) | Calls relatively expensive → stock tends to outperform; puts relatively expensive → tends to underperform |
| **Skew (smirk)** | OTM put IV (strike about 90% of spot) − ATM call IV | Xing, Zhang & Zhao (2010, JFQA): significantly negative coefficient; reported to persist about 6 months | Steep put skew → underperformance (fear of a crash) |
| **Option/stock volume (O/S)** | Option volume ÷ stock volume | Johnson & So (2012, JFE) | High O/S → lower future returns (informed traders who can't short use puts) |
| **IV vs realised volatility** | ATM IV − 20-day realised volatility | Variance-risk-premium literature | Very high IV relative to realised → event or fear premium; wait or size down |

Caveat: these are mainly US results. In today's quick search I confirmed Xing–Zhang–Zhao directly. Cremers–Weinbaum and Johnson–So are cited from the literature and were not re-confirmed in that search. **None has been tested on NSE stocks here yet**, and that is what the backtest below is for.

Live example, RELIANCE on 10 Nov:
- ATM call IV 19.8 vs ATM put IV 24.3 gives a call–put spread of **−4.5** (puts richer).
- The 1,190 put has IV 33.7, so skew vs the ATM call is **+13.9 points** (steep).

By the literature, both lean against a fresh long.

### Gate 4: Positioning (Indian market practice, evidence weak)
- Futures **price + OI**:
  - long build-up (price up, OI up);
  - short build-up (down, up);
  - short covering (up, down);
  - long unwinding (down, down).
- Option **OI walls** (largest call OI above spot as resistance, largest put OI below as support), **PCR** (put OI ÷ call OI), and **max pain**.
- Evidence: widely used by Indian desks and brokers, but I found **no peer-reviewed NSE study testing its forward returns**. One academic paper compares volume- vs OI-based PCR for the index (Jena, Tiwari & Mitra 2019). Show this as **context only** until our own backtest says otherwise.

### Gate 5: Event risk
- IV jumping ahead of a results date means the event is priced in.
- Compare the implied event move (straddle) with the stock's past results-day moves. If the implied move is much larger than history, a directional bet is expensive.

## How it appears in the Screener
- One new column, **Options**, showing:
  - ✅ confirms (Gate 2 realistic and Gate 3 not against),
  - ⚠ mixed,
  - ❌ contradicts (Gate 3 against, or Gate 2 unrealistic),
  - "—" when the stock has no options.
- Tapping a pick shows a small card:
  - expected move and range;
  - target realism and probability;
  - call–put spread and skew, with direction;
  - futures OI state;
  - OI walls and PCR (labelled "context, untested");
  - data time.
- The research note gets an "Options check" box with the same lines, signed off by the RA.

## How we test it (before trusting it)
1. **Start collecting daily snapshots now** (nightly job): for each Nifty 50 F&O stock, record the features above at the nearest monthly expiry.
2. **Backfill from expired-options data:** about 2 years of weekly samples, ATM ±3 strikes, CE and PE, for about 45 stocks. That is about 10k API calls, well inside the 100k/day limit, spread over 2 nights.
3. **Test each feature** with the same method the terminal already uses:
   - quintile spreads and rank IC on 5/21/63-day forward returns;
   - t-statistics;
   - hit rate.
   - Separate results for uptrend and weak markets.
4. **Test the gates on the terminal's own picks:** did ✅ picks beat ❌ picks?
5. **Keep a gate only if** its sign is stable in NSE data. Drop or reverse anything that fails. Publish the results in Method & Sources.

## Limits
- Options exist only for F&O stocks (most of the Nifty 50).
- Stock options are monthly, so the horizon is at most about 1 month.
- Implied probabilities are risk-neutral, not real-world forecasts.
- Signals can fail in strong trends or around events.
- SEBI-registered RA rules apply to any recommendation shown to clients. The RA signs, and the F&O risk disclosure goes on any derivatives note.
