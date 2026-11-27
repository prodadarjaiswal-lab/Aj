# Evidence Desk journal

Last updated by the daily run: **27 Nov 2026 16:55 IST**, market data as of the close of **2026-11-27**. This file is rebuilt automatically every run. Research software, not advice.

## Today in one paragraph

Nifty 50 closed at 25,607.2 (above its 200-day average, so the desk used its rising-market rules). 497 stocks loaded from Dhan. Desk signals passing its own back-test: 7 for rising markets, 0 for weak markets. Trade plans printed: 50, real calls (every check passed): 0. Indicator lab: 0 kept of 78. All plans so far: 684 (31 closed, 653 open).

## Today's playbook (feeds the Trading Terminal)

**Market type: rising** since 2026-11-11. Rising market: Nifty above its 200-day average and up 3%+ over 63 sessions. The terminal's at-a-glance cards, its screen order and the back-test picks all follow this section, and the trade plans skip any signal the back-test warns against in this market type. Rebuilt every run, so it changes when the market type changes or the evidence moves.

Grades: **proven** passed every check including the many-ideas correction; **leaning** was positive before and after the cut-off in this market type (t 1.5+ both times) and beat the Nifty after charges, but has not survived the many-ideas correction, so it is a lead; **avoid** was reliably worse than the average stock in this market type.

### Favoured in a rising market

| Indicator | grade | vs average stock after | t | vs Nifty after charges | cases | before cut-off | fired today |
|---|---|---|---|---|---|---|---|
| New 52-week closing high on 1.5x average volume | leaning | +1.5% | 2.75 | +2.1% | 4475 | +0.9% (t 1.6) | ACE, ANGELONE, BEML |
| Relative strength line vs Nifty at a 1-year high | leaning | +1.1% | 2.26 | +1.7% | 2958 | +1.0% (t 1.89) | BEML, DLF, GLENMARK, MCX, NAVINFLUOR, WELSPUNLIV |
| Up 10%+ in 10 days | leaning | +0.9% | 3.17 | +1.4% | 4021 | +0.5% (t 2.07) | ANGELONE, BEML, WELSPUNLIV |
| Up day on 2x the 50-day average volume | leaning | +0.4% | 1.59 | +1.1% | 8556 | +0.6% (t 2.59) | ACE, ANGELONE, APLAPOLLO, BANKINDIA, BDL, BEML, CDSL, CHOICEIN, DATAPATTNS, ENRIN, ESCORTS, HAL +10 |

### Warnings in a rising market

| Indicator | grade | vs average stock after | t | vs Nifty after charges | cases | before cut-off | fired today |
|---|---|---|---|---|---|---|---|
| Close back inside the lower Bollinger band | avoid | -1.4% | -2.3 | -0.1% | 2496 | -0.2% (t -0.47) | BHARTIHEXA, HFCL, JSWENERGY, NIACL, PCBL, TORNTPOWER |
| Factor: bottom 10% by 12-1 month return (losers) | avoid | -1.4% | -2.19 | -0.4% | 705 | -0.5% (t -0.87) | ABREL, ACC, AFCONS, AMBUJACEM, AWL, BATAINDIA, BDL, BLS, COCHINSHIP, EIDPARRY, FIRSTCRY, GODFRYPHLP +37 |
| Factor: bottom 10% by last month's return (short-term reversal) | avoid | -1.1% | -1.84 | -0.1% | 705 | -0.1% (t -0.4) | AIAENG, APARINDS, APLAPOLLO, ASTRAL, AZAD, BATAINDIA, BHARTIHEXA, CAPLIPOINT, CARBORUNIV, CHENNPETRO, CLEAN, CONCORDBIO +37 |
| Close above a rising 200-day average, first day | avoid | -0.8% | -1.87 | +0.2% | 1231 | -0.1% (t -0.26) | 360ONE, CDSL, HFCL, PARADEEP, POWERINDIA, TATACOMM |

### Market type history (from this journal)

- 2026-11-26 to 2026-11-27: rising (4 indicators favoured at the start)

## Which indicators work (back-test)

Tested **78 indicators** on 473 Nifty 500 stocks, Dhan daily data 2015-11-02 to 2026-11-27. In-sample: before 2023-11-28. Out-of-sample: 2023-11-28 onwards. Outcome: the next 21 trading days, bought at the signal day's close, after 0.25% round-trip charges.

Yardstick: the average stock in this universe did +0.56% vs the Nifty per 21 days after charges out-of-sample. An indicator has to beat the average stock, not just the Nifty.

**Kept: 0.** None passed every check, so the desk adds no new buy rule from this test.

**Warnings (reliably worse than the average stock): 0.** None.

**Near misses (positive in both periods, p under 0.05 on its own, but not after the many-ideas correction or the charges): 4.** These are watched, not traded.

### All indicators, best out-of-sample first

| Indicator | cases before | vs average stock before | cases after | vs average stock after | vs Nifty after charges | share beating Nifty | p-value | verdict |
|---|---|---|---|---|---|---|---|---|
| Gap up 3%+ that holds into the close | 3141 | +0.1% (t 0.17) | 1586 | +1.0% (t 2.3) | +2.0% | 0.607 | 0.010724 | **near** |
| MACD crosses below its signal line | 24305 | +0.1% (t 0.87) | 13298 | +0.2% (t 2.04) | +0.9% | 0.476 | 0.020675 | **near** |
| Factor: top 10% by 12-month return skipping the last month (momentum) | 3075 | +1.7% (t 4.12) | 1533 | +1.1% (t 1.99) | +1.7% | 0.517 | 0.023295 | **near** |
| Down 10%+ in 5 days | 7472 | +0.4% (t 1.11) | 3299 | +0.7% (t 1.67) | +1.8% | 0.538 | 0.04746 | **near** |
| Close 15%+ below the 50-day average (stretched down) | 3839 | +0.0% (t 0.04) | 1767 | +1.4% (t 1.55) | +2.5% | 0.555 | 0.060571 | **drop** |
| Relative strength line vs Nifty at a 1-year high | 10779 | +0.5% (t 2.0) | 6666 | +0.5% (t 1.53) | +1.0% | 0.52 | 0.063008 | **drop** |
| Down day on 3x the 50-day average volume | 7999 | -0.1% (t -0.34) | 3719 | +0.3% (t 1.3) | +1.0% | 0.48 | 0.0968 | **drop** |
| Factor: highest 10% 60-day volatility | 3076 | +0.9% (t 1.93) | 1533 | +0.8% (t 1.23) | +1.4% | 0.477 | 0.109349 | **drop** |
| ATR(14) under 60% of ATR(100), above the 50-day average | 303 | -2.2% (t -1.51) | 53 | +4.7% (t 1.2) | +4.2% | 0.34 | 0.11507 | **drop** |
| Beats the Nifty by 10%+ over 3 months, first day | 14369 | -0.2% (t -1.41) | 6877 | +0.3% (t 1.18) | +0.8% | 0.487 | 0.119 | **drop** |
| New 52-week closing high | 15276 | -0.0% (t -0.06) | 8154 | +0.4% (t 1.11) | +0.8% | 0.52 | 0.1335 | **drop** |
| Up day on 2x the 50-day average volume | 40986 | +0.1% (t 0.91) | 18463 | +0.2% (t 1.09) | +0.7% | 0.478 | 0.137857 | **drop** |
| Factor: top 10% by 6-month return skipping the last month | 3074 | +1.2% (t 3.02) | 1533 | +0.6% (t 1.02) | +1.2% | 0.5 | 0.153864 | **drop** |
| Close 40%+ above the 200-day average (overextended) | 3647 | +0.3% (t 0.47) | 1795 | +0.7% (t 0.93) | +1.3% | 0.542 | 0.176186 | **drop** |
| Within 3% of the 52-week high, first day | 14224 | +0.2% (t 0.66) | 7807 | +0.3% (t 0.88) | +0.8% | 0.525 | 0.18943 | **drop** |
| MACD(12,26,9) crosses above its signal line | 24502 | +0.1% (t 1.48) | 13149 | +0.1% (t 0.81) | +0.9% | 0.483 | 0.20897 | **drop** |
| Factor: top 10% by closeness to the 52-week high | 3253 | +0.5% (t 1.43) | 1555 | +0.3% (t 0.79) | +0.9% | 0.511 | 0.214764 | **drop** |
| Up 10%+ in 10 days | 17006 | +0.0% (t 0.27) | 8113 | +0.2% (t 0.76) | +0.6% | 0.498 | 0.223627 | **drop** |
| 20 > 50 > 200-day averages all lined up, first day | 4973 | -0.1% (t -0.4) | 2369 | +0.2% (t 0.7) | +0.5% | 0.488 | 0.241964 | **drop** |
| New 52-week closing high on 1.5x average volume | 14522 | +0.3% (t 1.07) | 6845 | +0.3% (t 0.66) | +0.7% | 0.531 | 0.254627 | **drop** |
| Close above the prior 100-day high | 12146 | +0.1% (t 0.3) | 6296 | +0.2% (t 0.59) | +0.5% | 0.509 | 0.277595 | **drop** |
| Bollinger width in its lowest 20% of 6 months, then close above the upper band | 8907 | +0.3% (t 1.53) | 3920 | +0.1% (t 0.54) | +0.5% | 0.469 | 0.294599 | **drop** |
| Narrowest range in 7 days | 82034 | +0.0% (t 1.12) | 40818 | +0.0% (t 0.54) | +0.6% | 0.478 | 0.294599 | **drop** |
| New 52-week closing low | 6034 | -0.1% (t -0.26) | 2935 | +0.3% (t 0.51) | +1.3% | 0.52 | 0.305026 | **drop** |
| Closes in the bottom 20% of the day's range above the 200-day average | 61064 | +0.3% (t 2.24) | 31957 | +0.1% (t 0.51) | +0.5% | 0.477 | 0.305026 | **drop** |
| 50-day average crosses above the 200-day average (golden cross) | 1766 | -0.5% (t -1.05) | 846 | +0.2% (t 0.41) | +0.8% | 0.5 | 0.340903 | **drop** |
| Aroon up crosses above 70 with Aroon down under 30 | 8415 | +0.3% (t 1.25) | 3690 | +0.1% (t 0.4) | +0.5% | 0.481 | 0.344578 | **drop** |
| Three down closes in a row above the 200-day average | 21514 | +0.5% (t 2.97) | 11042 | +0.1% (t 0.39) | +0.6% | 0.477 | 0.348268 | **drop** |
| +DI crosses above -DI with ADX above 25 | 4639 | -0.2% (t -1.01) | 2174 | +0.1% (t 0.33) | +0.9% | 0.476 | 0.3707 | **drop** |
| Close above the prior 55-day high | 15446 | -0.1% (t -0.27) | 7865 | +0.1% (t 0.29) | +0.4% | 0.503 | 0.385908 | **drop** |
| CCI(20) crosses above +100 | 32005 | +0.1% (t 0.81) | 15632 | +0.0% (t 0.19) | +0.5% | 0.487 | 0.424655 | **drop** |
| ADX(14) crosses above 20 with +DI above -DI | 6697 | +0.0% (t 0.16) | 3261 | +0.0% (t 0.19) | +0.2% | 0.469 | 0.424655 | **drop** |
| Close above the upper Keltner channel (EMA 20 + 2 ATR) | 15651 | -0.0% (t -0.03) | 7584 | +0.0% (t 0.17) | +0.3% | 0.49 | 0.432505 | **drop** |
| Up 10%+ over 10 days, then 5 days inside a 5% range | 13507 | +0.3% (t 1.06) | 6477 | +0.0% (t 0.1) | +0.3% | 0.492 | 0.460172 | **drop** |
| Close above the upper Bollinger band (20, 2) | 22270 | -0.0% (t -0.03) | 10291 | -0.0% (t -0.01) | +0.4% | 0.491 | 0.503989 | **drop** |
| Stochastic(14,3) %K crosses above %D below 20 | 19619 | -0.2% (t -1.18) | 11002 | -0.0% (t -0.02) | +1.1% | 0.469 | 0.507978 | **drop** |
| Close above the prior 20-day high | 24522 | -0.2% (t -1.24) | 12393 | -0.0% (t -0.04) | +0.3% | 0.492 | 0.515953 | **drop** |
| 20-day rate of change turns positive | 30698 | +0.1% (t 1.21) | 15853 | -0.0% (t -0.05) | +0.7% | 0.479 | 0.519939 | **drop** |
| MACD crosses above zero | 10427 | -0.0% (t -0.08) | 5347 | -0.0% (t -0.16) | +0.4% | 0.472 | 0.563559 | **drop** |
| Stochastic(14,3) %K crosses below %D above 80 | 18972 | -0.1% (t -0.58) | 10221 | -0.0% (t -0.19) | +0.1% | 0.489 | 0.575345 | **drop** |
| Factor: bottom 10% by last month's return (short-term reversal) | 3075 | -0.2% (t -0.57) | 1533 | -0.1% (t -0.3) | +0.5% | 0.475 | 0.617911 | **drop** |
| Money Flow Index(14) under 20 | 6244 | -0.2% (t -0.97) | 3244 | -0.1% (t -0.35) | +0.7% | 0.482 | 0.636831 | **drop** |
| Chaikin Money Flow(20) crosses above +0.10 | 18660 | +0.0% (t 0.15) | 11081 | -0.0% (t -0.39) | +0.5% | 0.488 | 0.651732 | **drop** |
| RSI(14) falls back below 70 | 13263 | +0.2% (t 0.97) | 5734 | -0.1% (t -0.45) | +0.2% | 0.498 | 0.673645 | **drop** |
| Close crosses above the 20-day average | 36176 | -0.0% (t -0.02) | 18939 | -0.0% (t -0.49) | +0.7% | 0.481 | 0.687933 | **drop** |
| RSI(14) crosses back above 30 | 7241 | -0.3% (t -1.03) | 4167 | -0.2% (t -0.5) | +0.9% | 0.474 | 0.691462 | **drop** |
| TRIX(15) turns positive | 7421 | -0.0% (t -0.04) | 3651 | -0.1% (t -0.57) | +0.1% | 0.469 | 0.715661 | **drop** |
| RSI(14) crosses above 70 (momentum) | 13299 | +0.1% (t 0.45) | 5693 | -0.2% (t -0.6) | +0.1% | 0.5 | 0.725747 | **drop** |
| Williams %R(14) crosses back above -80 | 38801 | -0.1% (t -0.64) | 21997 | -0.1% (t -0.63) | +0.9% | 0.477 | 0.735653 | **drop** |
| RSI(2) under 10 while above the 200-day average | 19903 | +0.4% (t 2.55) | 10576 | -0.1% (t -0.65) | +0.5% | 0.473 | 0.742154 | **drop** |
| Ichimoku Tenkan crosses above Kijun | 15613 | +0.0% (t 0.34) | 7730 | -0.1% (t -0.67) | +0.4% | 0.467 | 0.748571 | **drop** |
| MACD crosses above its signal line below zero | 13647 | +0.0% (t 0.29) | 7726 | -0.2% (t -0.74) | +0.7% | 0.466 | 0.77035 | **drop** |
| 50-day average crosses below the 200-day average (death cross) | 1705 | -0.5% (t -1.51) | 1039 | -0.3% (t -0.76) | +0.5% | 0.446 | 0.776373 | **drop** |
| Parabolic SAR flips below price | 26748 | -0.1% (t -1.17) | 14422 | -0.1% (t -0.78) | +0.6% | 0.478 | 0.782305 | **drop** |
| Close crosses below the 200-day average | 9593 | -0.3% (t -1.88) | 5360 | -0.2% (t -0.79) | +0.5% | 0.443 | 0.785236 | **drop** |
| 9-day EMA crosses above the 21-day EMA | 13478 | -0.1% (t -0.46) | 7011 | -0.1% (t -0.81) | +0.4% | 0.474 | 0.79103 | **drop** |
| RSI(2) under 5 | 23140 | +0.2% (t 1.87) | 12526 | -0.2% (t -0.95) | +0.7% | 0.468 | 0.828944 | **drop** |
| Narrowest range in 4 days and an inside bar | 67513 | +0.1% (t 1.44) | 29085 | -0.1% (t -1.02) | +0.5% | 0.469 | 0.846136 | **drop** |
| Money Flow Index(14) crosses above 80 | 15235 | -0.1% (t -0.62) | 7231 | -0.2% (t -1.08) | +0.1% | 0.474 | 0.859929 | **drop** |
| Factor: lowest 10% 60-day volatility | 3076 | -0.7% (t -2.11) | 1533 | -0.5% (t -1.18) | +0.1% | 0.466 | 0.881 | **drop** |
| Gap down 3%+ | 8166 | -0.5% (t -1.17) | 2887 | -0.6% (t -1.28) | +0.2% | 0.512 | 0.899727 | **drop** |
| 20-day EMA crosses above the 50-day EMA | 5814 | -0.6% (t -2.44) | 2895 | -0.4% (t -1.31) | -0.1% | 0.476 | 0.904902 | **drop** |
| OBV crosses above its 20-day EMA | 35761 | -0.2% (t -3.17) | 18423 | -0.2% (t -1.44) | +0.6% | 0.474 | 0.925066 | **drop** |
| Bullish engulfing candle after a down day | 22225 | -0.0% (t -0.48) | 12360 | -0.2% (t -1.53) | +0.5% | 0.469 | 0.936992 | **drop** |
| Close above the Ichimoku cloud, first day | 15973 | -0.2% (t -1.58) | 8208 | -0.2% (t -1.56) | +0.4% | 0.47 | 0.94062 | **drop** |
| OBV at a 50-day high while price is not | 21796 | +0.1% (t 0.43) | 10947 | -0.2% (t -1.57) | +0.3% | 0.463 | 0.941792 | **drop** |
| Close below the lower Bollinger band (20, 2) | 15925 | -0.0% (t -0.13) | 9315 | -0.5% (t -1.59) | +0.6% | 0.482 | 0.944083 | **drop** |
| Hammer after a 5-day decline | 9454 | -0.0% (t -0.27) | 6047 | -0.2% (t -1.59) | +0.8% | 0.482 | 0.944083 | **drop** |
| Close crosses above the 50-day average | 21272 | -0.2% (t -1.76) | 11338 | -0.2% (t -1.62) | +0.5% | 0.469 | 0.947384 | **drop** |
| Close crosses above the 200-day average | 9696 | -0.5% (t -3.32) | 5102 | -0.4% (t -1.65) | +0.3% | 0.464 | 0.950529 | **drop** |
| Up-day volume 1.5x down-day volume over 50 days, above the 50-day average | 16942 | -0.0% (t -0.28) | 8400 | -0.3% (t -1.67) | +0.3% | 0.468 | 0.95254 | **drop** |
| Close back inside the lower Bollinger band | 16004 | -0.0% (t -0.07) | 9304 | -0.4% (t -1.71) | +0.7% | 0.472 | 0.956367 | **drop** |
| CCI(20) crosses back above -100 | 27241 | -0.1% (t -0.98) | 15928 | -0.3% (t -1.78) | +0.6% | 0.475 | 0.962462 | **drop** |
| Close above a rising 200-day average, first day | 6427 | -0.1% (t -0.26) | 3489 | -0.5% (t -2.04) | +0.2% | 0.464 | 0.979325 | **drop** |
| RSI(14) crosses above 50 | 34123 | -0.1% (t -0.92) | 17830 | -0.2% (t -2.21) | +0.5% | 0.473 | 0.986447 | **drop** |
| Factor: bottom 10% by 12-1 month return (losers) | 3075 | -0.5% (t -1.23) | 1533 | -0.9% (t -2.22) | -0.3% | 0.419 | 0.986791 | **drop** |
| Relative strength line crosses above its 50-day average | 23735 | -0.3% (t -2.62) | 11735 | -0.3% (t -2.55) | +0.3% | 0.467 | 0.994614 | **drop** |
| Supertrend(10, 3) turns up | 7573 | -0.4% (t -2.12) | 4155 | -0.5% (t -2.56) | -0.0% | 0.463 | 0.994766 | **drop** |

How to read: *vs average stock* is the extra 21-day return over the average Nifty 500 stock on the same days, with a t-statistic clustered by month (2 or more is the usual bar for one idea; with 78 ideas the bar is higher, which is what the p-value column and Holm's correction handle). Rules, fixed before the results:

> (written before the results were seen, 26 Nov 2026; do not loosen them after a bad run):
>   * Event: the first day a condition becomes true (not every day it stays true). Cross-sectional factors
>     (momentum, low volatility, short-term reversal, 52-week-high proximity) are formed every 21 trading days.
>   * Outcome: the stock's return over the next 21 trading days, bought at the signal day's close:
>       - abnormal = stock return minus the equal-weighted average of all stocks over the same 21 days
>         (the "average stock" baseline, so a rising market or the universe's small-cap tilt does not count as skill)
>       - net vs Nifty = stock return minus the Nifty 50's return minus 0.25% round-trip delivery charges
>         (STT 0.1% each side, stamp, exchange, GST; config/trading.json)
>   * Split: in-sample = everything before the last 3 years; out-of-sample = the last 3 years.
>   * Statistics are clustered by calendar month: cases on the same days move together, so counting each stock as an
>     independent case would overstate the evidence by 10x or more. t = mean of monthly averages / standard error.
>   * KEEP (buy-side) only if: in-sample abnormal > 0 with t >= 2, out-of-sample abnormal > 0 with a one-sided p-value
>     that survives Holm's correction across EVERY indicator tested (the many-ideas test), out-of-sample net vs Nifty
>     > 0 after charges, and at least 100 out-of-sample cases in 12 or more months.
>   * AVOID (warning) is the mirror image: significantly worse than the average stock in both periods.
>   * Everything else is DROPPED. Survivorship bias: the universe is today's Nifty 500, which flatters every
>     indicator; the abnormal-return baseline uses the same universe, which cancels part of it.

### Fired on the last session

- near: Factor: top 10% by 12-month return skipping the last month (momentum): ACMESOLAR, ACUTAAS, AEGISLOG, AETHER, ANANDRATHI, APARINDS, ATHERENERG, AZAD, BBOX, BHEL, CEMPRO, CHENNPETRO, CPPLUS, CRAFTSMAN, CUPID, DIVISLAB, FEDERALBNK, FINCABLES, GESHIP, GLAND, GRANULES, HFCL, HONASA, INOXINDIA, JINDALSAW, KARURVYSYA, KIRLOSENG, LAURUSLABS, LENSKART, MCX and 19 more
- near: MACD crosses below its signal line: ADANIENT, ADANIPOWER, ARE&M, ASIANPAINT, BAJAJ-AUTO, BAJFINANCE, BANDHANBNK, BANKBARODA, CHOLAFIN, ELECON, FIRSTCRY, GMRAIRPORT, GPIL, HDFCAMC, HYUNDAI, ICICIBANK, IDBI, JSWCEMENT, KOTAKBANK, LTFOODS, MINDACORP, MOTHERSON, MPHASIS, NCC, PHOENIXLTD, SHRIRAMFIN, TVSMOTOR, UCOBANK, UNOMINDA, VBL and 1 more
- near: Gap up 3%+ that holds into the close: NATIONALUM

## Every recommendation and what happened

The desk printed **684 trade plans** since 2026-11-13. **0** passed every check (a real call); the rest failed at least one check, most often the many-signals test, and were shown as plans only. Each plan is scored on Dhan daily bars: stop first if the stop and target are touched the same day, otherwise target, otherwise sold at the 21st close. Rupee results use the plan's own share count and 0.25% charges.

- Closed so far: 31 (target 12, stop 19, time exit 0); open: 653.
- All plans, including open ones marked to the last close: average -0.2%, -0.6% vs the Nifty, 0.426 beat the Nifty, Rs -30,636 if every plan had been taken.
- Closed plans only: average -0.4%, Rs -3,503.
- Real calls (all checks passed): 0.

| Signal | plans | closed | target / stop / time | average so far | vs Nifty so far | Rs if all taken |
|---|---|---|---|---|---|---|
| flag | 389 | 22 | 8 / 14 / 0 | -0.2% | -0.9% | -20,490 |
| don55 | 88 | 2 | 0 / 2 / 0 | -0.9% | -0.6% | -7,527 |
| nr7 | 71 | 1 | 1 / 0 / 0 | +0.1% | +0.4% | -1,625 |
| qdrop10 | 39 | 0 | 0 / 0 / 0 | +1.0% | +1.1% | 2,815 |
| hi52v | 29 | 1 | 0 / 1 / 0 | -1.1% | -1.2% | -3,514 |
| volbreak | 27 | 1 | 1 / 0 / 0 | -1.3% | -1.2% | -3,031 |
| downtrend | 24 | 3 | 2 / 1 / 0 | +0.9% | -0.3% | 1,308 |
| qdrop | 17 | 1 | 0 / 1 / 0 | +1.0% | +1.2% | 1,429 |

### The live track record (picks logged before the outcome)

| Kind | picks | vs Nifty so far | share ahead of Nifty |
|---|---|---|---|
| dips | 55 | +1.4% | 0.636 |
| rising | 258 | -0.4% | 0.372 |
| score0 | 120 | +0.2% | 0.475 |
| score2 | 330 | -0.8% | 0.415 |
| score4 | 201 | -0.1% | 0.423 |
| score6 | 86 | +0.1% | 0.465 |

Kinds: *rising* = tested breakout signals on leading stocks, *dips* = tested dip signals, *score0/2/4/6* = the research screener's score bands (score0 is a random control group). These are days old, so they say very little yet; they become meaningful after 21 trading days.

### Latest plans, newest first

| Day | Stock | Signal | Entry | Stop | Target | Qty | Called? | Status | Days | Return | vs Nifty | Rs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-27 | WELSPUNLIV | don55 | 285.5 | 259.5 | 324.5 | 175 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | VOLTAS | flag | 1186 | 1082 | 1342 | 42 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | VMM | nr7 | 96.2 | 89.8 | 105.8 | 519 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | TRENT | nr7 | 3275 | 3045 | 3620 | 15 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | TORNTPHARM | don55 | 5030 | 4780 | 5410 | 9 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | TATACHEM | nr7 | 662 | 625 | 718 | 75 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | SUNTV | nr7 | 641 | 566 | 754 | 66 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | STARHEALTH | nr7 | 570 | 534 | 624 | 87 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | SIGNATURE | flag | 846 | 785 | 938 | 59 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | SBIN | flag | 1124 | 1068 | 1208 | 44 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | PAYTM | qdrop10 | 1742 | 1570 | 2000 | 28 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | NHPC | nr7 | 75.6 | 71.5 | 81.8 | 661 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | NAVINFLUOR | don55 | 10450 | 9725 | 11550 | 4 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | MGL | nr7 | 1078 | 1010 | 1180 | 46 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | MCX | don55 | 3900 | 3515 | 4480 | 12 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | MAXHEALTH | flag | 1072 | 996 | 1186 | 46 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | M&M | flag | 3450 | 3215 | 3805 | 14 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | LTTS | nr7 | 4225 | 3930 | 4670 | 11 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | LT | nr7 | 4110 | 3905 | 4420 | 12 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | LLOYDSME | qdrop10 | 1556 | 1394 | 1800 | 30 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | LINDEINDIA | nr7 | 6980 | 6340 | 7940 | 7 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | KALYANKJIL | flag | 660 | 594 | 759 | 75 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | J&KBANK | don55 | 166.5 | 149.0 | 192.75 | 285 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | INDIGO | nr7 | 5660 | 5300 | 6200 | 8 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | IDFCFIRSTB | flag | 86.8 | 81.7 | 94.5 | 576 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | IDEA | qdrop10 | 11.55 | 10.2 | 13.6 | 3703 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | HDFCBANK | nr7 | 857 | 801 | 941 | 58 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | GLENMARK | don55 | 2835 | 2650 | 3115 | 17 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | GILLETTE | nr7 | 7240 | 6850 | 7830 | 6 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | GABRIEL | flag | 1546 | 1408 | 1754 | 32 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | FORCEMOT | flag | 20175 | 18475 | 22725 | 2 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | EIHOTEL | nr7 | 338.0 | 311.0 | 378.5 | 147 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | DIVISLAB | flag | 11550 | 10825 | 12650 | 4 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | DEEPAKFERT | flag | 1446 | 1316 | 1642 | 34 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | CRAFTSMAN | flag | 12000 | 11075 | 13400 | 4 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | COROMANDEL | nr7 | 1960 | 1848 | 2128 | 25 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | CIPLA | nr7 | 1440 | 1374 | 1540 | 34 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | CAPLIPOINT | qdrop10 | 2065 | 1875 | 2350 | 24 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | BLUESTARCO | flag | 1736 | 1588 | 1958 | 28 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | BHEL | nr7 | 422.0 | 387.5 | 474.0 | 118 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | BEML | hi52v | 2345 | 1950 | 2940 | 12 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | BBOX | nr7 | 861 | 781 | 981 | 58 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | ASHOKLEY | qdrop10 | 151.5 | 138.75 | 170.75 | 330 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | APOLLOTYRE | nr7 | 426.0 | 401.5 | 463.0 | 117 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | ANURAS | nr7 | 1322 | 1228 | 1464 | 37 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | ANGELONE | hi52v | 376.0 | 340.5 | 429.5 | 132 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | ADANIENSOL | qdrop10 | 1336 | 1168 | 1588 | 29 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | ACE | hi52v | 1326 | 1202 | 1512 | 37 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | ABB | nr7 | 7060 | 6570 | 7800 | 7 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-27 | 360ONE | don55 | 1230 | 1136 | 1372 | 40 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | WOCKPHARMA | volbreak | 2235 | 1905 | 2730 | 3 | no | open | 1 | +0.4% | +1.5% | 11 |
| 2026-11-26 | WELSPUNLIV | don55 | 280.5 | 255.0 | 319.0 | 35 | no | open | 1 | +1.8% | +2.9% | 151 |
| 2026-11-26 | UBL | nr7 | 1272 | 1202 | 1378 | 7 | no | open | 1 | +0.3% | +1.4% | 3 |
| 2026-11-26 | TRENT | nr7 | 3265 | 3035 | 3610 | 3 | no | open | 1 | +0.2% | +1.3% | -0 |
| 2026-11-26 | TORNTPHARM | don55 | 5020 | 4740 | 5440 | 1 | no | open | 1 | +0.3% | +1.4% | 1 |
| 2026-11-26 | TCS | don55 | 2640 | 2480 | 2880 | 3 | no | open | 1 | -2.6% | -1.5% | -222 |
| 2026-11-26 | TATASTEEL | qdrop10 | 163.5 | 145.75 | 190.25 | 56 | no | open | 1 | +0.3% | +1.3% | 2 |
| 2026-11-26 | STLTECH | qdrop | 589 | 509 | 709 | 12 | no | open | 1 | +5.1% | +6.1% | 340 |
| 2026-11-26 | SIGNATURE | flag | 856 | 792 | 952 | 11 | no | open | 1 | -1.1% | -0.1% | -131 |
| 2026-11-26 | SHYAMMETL | nr7 | 1292 | 1200 | 1430 | 7 | no | open | 1 | +1.0% | +2.1% | 71 |
| 2026-11-26 | SBIN | flag | 1136 | 1082 | 1218 | 8 | no | open | 1 | -1.1% | +0.0% | -120 |
| 2026-11-26 | SBICARD | nr7 | 586 | 555 | 633 | 17 | no | open | 1 | -3.4% | -2.4% | -368 |
| 2026-11-26 | SANSERA | nr7 | 4685 | 4255 | 5330 | 2 | no | open | 1 | +1.2% | +2.3% | 91 |
| 2026-11-26 | RUBICON | volbreak | 1852 | 1578 | 2264 | 3 | no | open | 1 | +0.9% | +2.0% | 38 |
| 2026-11-26 | RELIANCE | don55 | 1396 | 1334 | 1490 | 7 | no | open | 1 | -1.0% | +0.1% | -118 |
| 2026-11-26 | RAMCOCEM | nr7 | 828 | 785 | 893 | 12 | no | open | 1 | -0.4% | +0.7% | -62 |
| 2026-11-26 | PRESTIGE | hi52v | 1832 | 1674 | 2070 | 5 | no | open | 1 | -1.9% | -0.9% | -199 |
| 2026-11-26 | PNB | nr7 | 147.5 | 137.0 | 163.25 | 67 | no | open | 1 | -0.7% | +0.4% | -92 |
| 2026-11-26 | PIDILITIND | nr7 | 1604 | 1516 | 1736 | 6 | no | open | 1 | -0.6% | +0.5% | -79 |
| 2026-11-26 | PFOCUS | qdrop | 236.5 | 207.75 | 279.75 | 34 | no | open | 1 | +0.5% | +1.6% | 19 |
| 2026-11-26 | OBEROIRLTY | volbreak | 1906 | 1786 | 2086 | 5 | no | open | 1 | -0.9% | +0.2% | -108 |
| 2026-11-26 | NATIONALUM | qdrop10 | 295.0 | 267.0 | 337.0 | 33 | no | open | 1 | +3.2% | +4.3% | 291 |
| 2026-11-26 | MCX | hi52v | 3835 | 3415 | 4465 | 2 | no | open | 1 | +1.7% | +2.8% | 111 |
| 2026-11-26 | MAXHEALTH | flag | 1082 | 1004 | 1200 | 9 | no | open | 1 | -1.0% | +0.1% | -121 |
| 2026-11-26 | MARICO | don55 | 939 | 896 | 1004 | 10 | no | open | 1 | -1.8% | -0.7% | -190 |
| 2026-11-26 | MANAPPURAM | qdrop | 270.0 | 248.0 | 303.0 | 37 | no | open | 1 | +3.1% | +4.2% | 286 |
| 2026-11-26 | M&M | flag | 3490 | 3250 | 3850 | 2 | no | open | 1 | -1.1% | -0.1% | -98 |
| 2026-11-26 | LODHA | don55 | 1262 | 1156 | 1422 | 7 | no | open | 1 | -0.8% | +0.3% | -94 |
| 2026-11-26 | LLOYDSME | qdrop10 | 1542 | 1350 | 1830 | 5 | no | open | 1 | +1.0% | +2.0% | 55 |
| 2026-11-26 | LAURUSLABS | don55 | 2505 | 2310 | 2800 | 3 | no | open | 1 | -0.0% | +1.0% | -21 |

Full ledger: `journal/recommendations.json` (684 plans).

## The desk's own signal back-test

The 30 signals behind the desk's buy lists, re-tested every run on Dhan daily data from 2015-11-02 (out-of-sample from 2024-11-27, 497 stocks). 7 pass the desk's single-signal test in rising markets; 0 of 30 survive the joint many-signals test (risk lab), which is why the desk makes no real calls. Moved here from the Trading Terminal so the terminal stays a clean screen.

| Signal | passes (rising) | passes (weak) | cases after | 10-day vs Nifty after | lift vs average stock | many-signals p | survives |
|---|---|---|---|---|---|---|---|
| Relative strength line at a 1-year high before the price is | yes | no | 269 | +1.70% | +1.43% | 0.434 | no |
| Gap up of 3% or more that holds into the close on 2x volume | no | no | 233 | +1.66% | +1.40% | 0.434 | no |
| New 52-week closing high on 1.5x average volume | yes | no | 1038 | +1.55% | +1.29% | 0.434 | no |
| Proven stock 25% below its 52-week high, first close back above its 20-day average | no | no | 850 | +1.36% | +1.10% | 0.434 | no |
| Proven stock (beat the Nifty by 20%+ over 2 years) falls 15%+ within 10 days | yes | no | 158 | +1.34% | +1.07% | 0.434 | no |
| Bull flag: up 10%+ over 10 days, then 5 days inside a 5% range (trader-scanner) | yes | no | 2065 | +1.12% | +0.85% | 0.434 | no |
| Proven stock (beat the Nifty by 20%+ over 2 years) falls 10%+ within 10 days | yes | no | 730 | +0.96% | +0.70% | 0.434 | no |
| Donchian breakout: close above the 55-day high (turtle rule) | yes | no | 2529 | +0.81% | +0.54% | 0.434 | no |
| Oversold bounce: RSI(14) under 30 yesterday, closes up today (trader-scanner) | no | no | 1499 | +0.75% | +0.49% | 0.434 | no |
| Tightest range in 7 days, inside the prior bar, in an uptrend | yes | no | 3216 | +0.70% | +0.44% | 0.434 | no |
| Proven stock (beat the Nifty by 20%+ over 2 years) falls 25%+ within 20 days | no | no | 39 | +0.68% | +0.41% | 0.434 | no |
| Volume breakout above the 20-day high (existing setup) | no | no | 2486 | +0.54% | +0.27% | 0.434 | no |
| MACD crosses above its signal line while above zero | no | no | 1730 | +0.47% | +0.20% | 0.434 | no |
| Strong trend starting: ADX(14) crosses above 25 with buyers in control | no | no | 1095 | +0.41% | +0.15% | 0.434 | no |
| Overextended: RSI(14) over 80 and 25% above the 50-day average (warning) | no | no | 118 | +0.41% | +0.14% | 0.434 | no |
| 20-day closing-high breakout with turnover of Rs 10 crore or more (nse-day-trader / trader-scanner) | no | no | 6579 | +0.40% | +0.14% | 0.434 | no |
| Trend template: price above rising 50, 150 and 200-day averages, near its 52-week high | no | no | 1380 | +0.31% | +0.04% | 0.434 | no |
| Downtrend: below a falling 200-day average and 50-day below 200-day (warning) | no | no | 863 | +0.30% | +0.03% | 0.434 | no |
| Pullback in an uptrend (existing setup) | no | no | 1950 | +0.29% | +0.02% | 0.434 | no |
| Accumulation: up-day volume 1.5x down-day volume over 50 days, above the 50-day average | no | no | 2874 | +0.26% | -0.01% | 0.434 | no |
| Three down closes in a row while above the 200-day average | no | no | 3273 | +0.18% | -0.08% | 0.434 | no |
| Closes back above the 200-day average after 20+ days below | no | no | 512 | +0.16% | -0.11% | 0.434 | no |
| Supertrend(10, 3) turns up | no | no | 1423 | +0.15% | -0.12% | 0.434 | no |
| Closes in the bottom 20% of its day's range while above the 200-day average | no | no | 9289 | +0.15% | -0.12% | 0.434 | no |
| Closes back above the 20-day average after 5+ days below, in an uptrend (trader-scanner) | no | no | 1456 | +0.11% | -0.15% | 0.434 | no |
| Bollinger squeeze breakout: band width in its lowest 20% of 6 months, close above the upper band | no | no | 1522 | +0.10% | -0.17% | 0.434 | no |
| Proven stock (beat the Nifty by 20%+ over 2 years) falls to 25% below its 52-week high | no | no | 895 | +0.10% | -0.17% | 0.434 | no |
| Short dip in an uptrend: RSI(2) under 10 while above the 200-day average | no | no | 3040 | +0.09% | -0.17% | 0.434 | no |
| Oversold: RSI(14) under 30 (trader-scanner) | no | no | 1073 | -0.05% | -0.31% | 0.434 | no |
| Volatility contraction near the high: 10-day range under 60% of the 50-day range | no | no | 1 | n/a | n/a | None | no |

## The terminal's intraday back-test (last month)

Desk picks bought at 09:30, 12:30 or 15:00 on each of the last 22 sessions (2026-10-26 to 2026-11-26), 489 stocks, 5-minute Dhan bars, held to the plan's exit. Rules passing: 0.

| Buy time | trades | average vs Nifty | share up | t | passes | Rs over the month |
|---|---|---|---|---|---|---|
| 09:30 | 1287 | -0.28% | 43% | -6.7 | no | -2959 |
| 12:30 | 1287 | -0.07% | 43% | -2.71 | no | 4481 |
| 15:00 | 1287 | -0.09% | 44% | -6.72 | no | -6059 |

## Rule changes

- None yet.

## Daily log, newest first

- **2026-11-27** (run 27 Nov 2026 16:55 IST): Nifty 50 closed at 25,607.2 (above its 200-day average, so the desk used its rising-market rules). 497 stocks loaded from Dhan. Desk signals passing its own back-test: 7 for rising markets, 0 for weak markets. Trade plans printed: 50, real calls (every check passed): 0. Indicator lab: 0 kept of 78. All plans so far: 684 (31 closed, 653 open).
- **2026-11-26** (run 26 Nov 2026 22:27 IST): Nifty 50 closed at 25,884.5 (above its 200-day average, so the desk used its rising-market rules). 497 stocks loaded from Dhan. Desk signals passing its own back-test: 8 for rising markets, 1 for weak markets. Trade plans printed: 81, real calls (every check passed): 0. Indicator lab: 0 kept of 78. All plans so far: 634 (26 closed, 608 open).

## How the desk works

**One run a day.** A single Claude scheduled task runs at 8:43 AM IST on weekdays. It starts the live price feed
(`live-feed.yml`), then the daily refresh (`dhan-refresh.yml`), then republishes the Evidence Desk and the Trading
Terminal. There are no GitHub timers: GitHub's own scheduler started jobs 5 to 10 hours late, so it was removed.
Because the refresh runs in the morning, the desk shows the previous trading day's close until the next morning run;
during market hours the prices tick from the live feed. (An evening close update is being added separately.)

**What the daily refresh does, in order** (`scripts/dhan_refresh/refresh.py --with-tech`):
1. Logs in to Dhan fresh with TOTP and checks the data (Nifty present, no future bars, no 25%+ one-day jumps).
2. Pulls 11 years of daily bars for the Nifty 500 (`tech_model.fetch`).
3. Re-runs the technical model's back-test of 30 desk signals (`tech_model.py`): each signal must beat the average stock
   in the first years and again in the last 2 years, in rising and weak markets separately. Signals are promoted or
   dropped automatically.
4. Value model, portfolio fit, research screener, risk lab (GARCH volatility, conformal ranges, and the joint
   many-signals test), then the trade plan (`tradeplan.py`): entry at the close, stop from the stock's volatility over
   21 sessions, target 1.5x the risk, size from Rs 1,00,000 capital and Rs 1,000 maximum loss per trade, charges
   included, 10,000 replays for the odds.
5. A trade plan is a real call only if every check passes: reward to risk, expected value after charges, turnover,
   position cap, daily loss limit, the many-signals test, and no results meeting while held.
6. The live track record (`track.py`) logs the day's picks before the outcome is known and scores them 10 and 21
   sessions later.
7. This journal (`journal.py`): adds the day's plans to the ledger, scores every past plan on the new bars, re-runs
   the indicator back-test (`indicator_lab.py`), and rebuilds this file.

**Why "no trade" is the usual answer.** With dozens of signals tested at once, some look good by luck. The
many-signals test (and Holm's correction in the indicator lab) asks whether a result is still convincing after
allowing for that. When nothing survives, the honest output is no call.

**Where things live.** Desk: https://claude.ai/artifact/QHCtbgKuHA17eSSS4zbd9h. Code: `scripts/dhan_refresh/`.
Journal: `journal/` in the repo, copied to the project's files as `journal/JOURNAL.md` by the daily task.

