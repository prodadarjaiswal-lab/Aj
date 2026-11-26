# Evidence Desk journal

Last updated by the daily run: **26 Nov 2026 21:37 IST**, market data as of the close of **2026-11-26**. This file is rebuilt automatically every run. Research software, not advice.

## Today in one paragraph

Nifty 50 closed at 25,884.5 (above its 200-day average, so the desk used its rising-market rules). 497 stocks loaded from Dhan. Desk signals passing its own back-test: 7 for rising markets, 1 for weak markets. Trade plans printed: 0, real calls (every check passed): 0. Indicator lab: 0 kept of 78. All plans so far: 553 (26 closed, 527 open).

## Which indicators work (back-test)

Tested **78 indicators** on 473 Nifty 500 stocks, Dhan daily data 2015-10-30 to 2026-11-26. In-sample: before 2023-11-27. Out-of-sample: 2023-11-27 onwards. Outcome: the next 21 trading days, bought at the signal day's close, after 0.25% round-trip charges.

Yardstick: the average stock in this universe did +0.64% vs the Nifty per 21 days after charges out-of-sample. An indicator has to beat the average stock, not just the Nifty.

**Kept: 0.** None passed every check, so the desk adds no new buy rule from this test.

**Warnings (reliably worse than the average stock): 0.** None.

**Near misses (positive in both periods, p under 0.05 on its own, but not after the many-ideas correction or the charges): 4.** These are watched, not traded.

### All indicators, best out-of-sample first

| Indicator | cases before | vs average stock before | cases after | vs average stock after | vs Nifty after charges | share beating Nifty | p-value | verdict |
|---|---|---|---|---|---|---|---|---|
| Gap up 3%+ that holds into the close | 3143 | +0.1% (t 0.18) | 1584 | +1.0% (t 2.31) | +2.0% | 0.608 | 0.010444 | **near** |
| Factor: top 10% by 12-month return skipping the last month (momentum) | 3075 | +1.6% (t 3.94) | 1533 | +1.3% (t 2.09) | +1.9% | 0.506 | 0.018309 | **near** |
| MACD crosses below its signal line | 24330 | +0.1% (t 1.02) | 13290 | +0.2% (t 2.06) | +0.9% | 0.476 | 0.019699 | **near** |
| Down 10%+ in 5 days | 7485 | +0.4% (t 1.11) | 3297 | +0.7% (t 1.66) | +1.8% | 0.538 | 0.048457 | **near** |
| Close 15%+ below the 50-day average (stretched down) | 3844 | +0.0% (t 0.05) | 1763 | +1.4% (t 1.55) | +2.5% | 0.556 | 0.060571 | **drop** |
| Relative strength line vs Nifty at a 1-year high | 10783 | +0.5% (t 2.01) | 6662 | +0.5% (t 1.54) | +1.0% | 0.521 | 0.06178 | **drop** |
| Down day on 3x the 50-day average volume | 8019 | -0.1% (t -0.36) | 3708 | +0.3% (t 1.33) | +1.0% | 0.481 | 0.091759 | **drop** |
| Factor: highest 10% 60-day volatility | 3076 | +0.9% (t 1.95) | 1533 | +0.9% (t 1.23) | +1.5% | 0.476 | 0.109349 | **drop** |
| ATR(14) under 60% of ATR(100), above the 50-day average | 303 | -2.2% (t -1.51) | 53 | +4.7% (t 1.2) | +4.2% | 0.34 | 0.11507 | **drop** |
| Beats the Nifty by 10%+ over 3 months, first day | 14375 | -0.2% (t -1.4) | 6861 | +0.3% (t 1.15) | +0.7% | 0.488 | 0.125072 | **drop** |
| New 52-week closing high | 15278 | -0.0% (t -0.04) | 8153 | +0.4% (t 1.13) | +0.8% | 0.52 | 0.129238 | **drop** |
| Up day on 2x the 50-day average volume | 40999 | +0.1% (t 0.94) | 18436 | +0.1% (t 1.02) | +0.7% | 0.479 | 0.153864 | **drop** |
| Factor: top 10% by 6-month return skipping the last month | 3075 | +1.3% (t 3.17) | 1533 | +0.6% (t 0.99) | +1.3% | 0.489 | 0.161087 | **drop** |
| Close 40%+ above the 200-day average (overextended) | 3647 | +0.3% (t 0.47) | 1795 | +0.7% (t 0.93) | +1.3% | 0.542 | 0.176186 | **drop** |
| Within 3% of the 52-week high, first day | 14225 | +0.2% (t 0.7) | 7806 | +0.3% (t 0.89) | +0.8% | 0.525 | 0.186733 | **drop** |
| MACD(12,26,9) crosses above its signal line | 24508 | +0.1% (t 1.5) | 13114 | +0.1% (t 0.79) | +0.9% | 0.484 | 0.214764 | **drop** |
| Up 10%+ in 10 days | 17007 | +0.1% (t 0.3) | 8111 | +0.2% (t 0.78) | +0.6% | 0.498 | 0.217695 | **drop** |
| New 52-week closing high on 1.5x average volume | 14524 | +0.3% (t 1.1) | 6843 | +0.3% (t 0.67) | +0.7% | 0.531 | 0.251429 | **drop** |
| 20 > 50 > 200-day averages all lined up, first day | 4976 | -0.1% (t -0.4) | 2368 | +0.2% (t 0.62) | +0.5% | 0.488 | 0.267629 | **drop** |
| Close above the prior 100-day high | 12146 | +0.1% (t 0.3) | 6295 | +0.2% (t 0.6) | +0.5% | 0.509 | 0.274253 | **drop** |
| Narrowest range in 7 days | 82034 | +0.0% (t 1.12) | 40712 | +0.0% (t 0.55) | +0.6% | 0.478 | 0.29116 | **drop** |
| Closes in the bottom 20% of the day's range above the 200-day average | 61065 | +0.3% (t 2.24) | 31931 | +0.1% (t 0.54) | +0.5% | 0.478 | 0.294599 | **drop** |
| Bollinger width in its lowest 20% of 6 months, then close above the upper band | 8909 | +0.3% (t 1.61) | 3917 | +0.1% (t 0.53) | +0.5% | 0.469 | 0.298056 | **drop** |
| New 52-week closing low | 6041 | -0.1% (t -0.26) | 2925 | +0.3% (t 0.51) | +1.3% | 0.52 | 0.305026 | **drop** |
| Factor: top 10% by closeness to the 52-week high | 3237 | +0.6% (t 1.59) | 1589 | +0.2% (t 0.44) | +0.8% | 0.505 | 0.329969 | **drop** |
| 50-day average crosses above the 200-day average (golden cross) | 1767 | -0.5% (t -1.03) | 846 | +0.2% (t 0.41) | +0.8% | 0.5 | 0.340903 | **drop** |
| Three down closes in a row above the 200-day average | 21517 | +0.5% (t 2.97) | 11042 | +0.1% (t 0.39) | +0.6% | 0.477 | 0.348268 | **drop** |
| Aroon up crosses above 70 with Aroon down under 30 | 8415 | +0.3% (t 1.25) | 3689 | +0.1% (t 0.38) | +0.5% | 0.481 | 0.351973 | **drop** |
| Close above the prior 55-day high | 15446 | -0.1% (t -0.27) | 7862 | +0.1% (t 0.32) | +0.4% | 0.503 | 0.374484 | **drop** |
| +DI crosses above -DI with ADX above 25 | 4639 | -0.2% (t -1.01) | 2166 | +0.1% (t 0.32) | +0.9% | 0.477 | 0.374484 | **drop** |
| ADX(14) crosses above 20 with +DI above -DI | 6697 | +0.0% (t 0.16) | 3260 | +0.1% (t 0.24) | +0.2% | 0.47 | 0.405165 | **drop** |
| Factor: bottom 10% by last month's return (short-term reversal) | 3075 | -0.0% (t -0.02) | 1533 | +0.1% (t 0.21) | +0.7% | 0.481 | 0.416834 | **drop** |
| Close above the upper Keltner channel (EMA 20 + 2 ATR) | 15651 | -0.0% (t -0.03) | 7580 | +0.0% (t 0.19) | +0.3% | 0.49 | 0.424655 | **drop** |
| CCI(20) crosses above +100 | 32006 | +0.1% (t 0.82) | 15618 | +0.0% (t 0.18) | +0.5% | 0.487 | 0.428576 | **drop** |
| Up 10%+ over 10 days, then 5 days inside a 5% range | 13508 | +0.3% (t 1.08) | 6474 | +0.0% (t 0.13) | +0.3% | 0.492 | 0.448283 | **drop** |
| Close above the upper Bollinger band (20, 2) | 22273 | +0.0% (t 0.03) | 10286 | -0.0% (t -0.02) | +0.4% | 0.491 | 0.507978 | **drop** |
| Stochastic(14,3) %K crosses above %D below 20 | 19633 | -0.2% (t -1.18) | 10970 | -0.0% (t -0.03) | +1.1% | 0.469 | 0.511966 | **drop** |
| Close above the prior 20-day high | 24523 | -0.2% (t -1.23) | 12386 | -0.0% (t -0.04) | +0.3% | 0.493 | 0.515953 | **drop** |
| 20-day rate of change turns positive | 30705 | +0.1% (t 1.21) | 15825 | -0.0% (t -0.06) | +0.7% | 0.479 | 0.523922 | **drop** |
| MACD crosses above zero | 10429 | -0.0% (t -0.05) | 5335 | -0.0% (t -0.17) | +0.4% | 0.472 | 0.567495 | **drop** |
| Stochastic(14,3) %K crosses below %D above 80 | 18975 | -0.1% (t -0.57) | 10216 | -0.0% (t -0.18) | +0.1% | 0.489 | 0.571424 | **drop** |
| Money Flow Index(14) under 20 | 6255 | -0.2% (t -0.96) | 3240 | -0.1% (t -0.37) | +0.7% | 0.481 | 0.644309 | **drop** |
| Chaikin Money Flow(20) crosses above +0.10 | 18689 | +0.0% (t 0.12) | 11057 | -0.1% (t -0.43) | +0.5% | 0.488 | 0.666402 | **drop** |
| RSI(14) falls back below 70 | 13264 | +0.2% (t 0.93) | 5729 | -0.1% (t -0.44) | +0.2% | 0.498 | 0.670031 | **drop** |
| RSI(14) crosses back above 30 | 7244 | -0.3% (t -1.03) | 4140 | -0.2% (t -0.51) | +0.9% | 0.476 | 0.694974 | **drop** |
| TRIX(15) turns positive | 7423 | -0.0% (t -0.02) | 3645 | -0.1% (t -0.56) | +0.1% | 0.47 | 0.71226 | **drop** |
| Close crosses above the 20-day average | 36186 | -0.0% (t -0.0) | 18909 | -0.1% (t -0.57) | +0.7% | 0.481 | 0.715661 | **drop** |
| RSI(14) crosses above 70 (momentum) | 13299 | +0.1% (t 0.45) | 5691 | -0.2% (t -0.58) | +0.1% | 0.5 | 0.719043 | **drop** |
| RSI(2) under 10 while above the 200-day average | 19927 | +0.4% (t 2.54) | 10576 | -0.1% (t -0.65) | +0.5% | 0.473 | 0.742154 | **drop** |
| Williams %R(14) crosses back above -80 | 38886 | -0.0% (t -0.63) | 21954 | -0.1% (t -0.65) | +0.9% | 0.478 | 0.742154 | **drop** |
| Ichimoku Tenkan crosses above Kijun | 15614 | +0.0% (t 0.34) | 7729 | -0.1% (t -0.67) | +0.4% | 0.467 | 0.748571 | **drop** |
| Close crosses below the 200-day average | 9609 | -0.3% (t -1.9) | 5349 | -0.2% (t -0.74) | +0.5% | 0.444 | 0.77035 | **drop** |
| MACD crosses above its signal line below zero | 13651 | +0.0% (t 0.3) | 7694 | -0.2% (t -0.74) | +0.7% | 0.467 | 0.77035 | **drop** |
| 50-day average crosses below the 200-day average (death cross) | 1705 | -0.5% (t -1.51) | 1034 | -0.3% (t -0.8) | +0.4% | 0.447 | 0.788145 | **drop** |
| Parabolic SAR flips below price | 26756 | -0.1% (t -1.16) | 14387 | -0.1% (t -0.82) | +0.6% | 0.479 | 0.793892 | **drop** |
| 9-day EMA crosses above the 21-day EMA | 13480 | -0.1% (t -0.47) | 7001 | -0.1% (t -0.85) | +0.4% | 0.474 | 0.802337 | **drop** |
| RSI(2) under 5 | 23163 | +0.2% (t 1.86) | 12520 | -0.2% (t -0.95) | +0.7% | 0.468 | 0.828944 | **drop** |
| Narrowest range in 4 days and an inside bar | 67514 | +0.1% (t 1.45) | 28996 | -0.1% (t -0.95) | +0.5% | 0.469 | 0.828944 | **drop** |
| Money Flow Index(14) crosses above 80 | 15236 | -0.1% (t -0.62) | 7227 | -0.3% (t -1.1) | +0.1% | 0.474 | 0.864334 | **drop** |
| Gap down 3%+ | 8441 | -0.5% (t -1.13) | 2880 | -0.6% (t -1.3) | +0.2% | 0.513 | 0.9032 | **drop** |
| 20-day EMA crosses above the 50-day EMA | 5814 | -0.6% (t -2.44) | 2893 | -0.4% (t -1.33) | -0.1% | 0.476 | 0.908241 | **drop** |
| OBV crosses above its 20-day EMA | 35771 | -0.2% (t -3.16) | 18391 | -0.2% (t -1.48) | +0.6% | 0.475 | 0.930563 | **drop** |
| Bullish engulfing candle after a down day | 22242 | -0.0% (t -0.42) | 12339 | -0.2% (t -1.52) | +0.5% | 0.47 | 0.935745 | **drop** |
| Factor: lowest 10% 60-day volatility | 3076 | -0.7% (t -2.22) | 1533 | -0.7% (t -1.52) | -0.1% | 0.47 | 0.935745 | **drop** |
| Close above the Ichimoku cloud, first day | 15979 | -0.2% (t -1.58) | 8204 | -0.2% (t -1.56) | +0.4% | 0.47 | 0.94062 | **drop** |
| OBV at a 50-day high while price is not | 21806 | +0.1% (t 0.45) | 10936 | -0.2% (t -1.57) | +0.3% | 0.464 | 0.941792 | **drop** |
| Close crosses above the 50-day average | 21280 | -0.2% (t -1.75) | 11321 | -0.2% (t -1.59) | +0.5% | 0.47 | 0.944083 | **drop** |
| Close below the lower Bollinger band (20, 2) | 15988 | -0.0% (t -0.14) | 9307 | -0.5% (t -1.59) | +0.6% | 0.482 | 0.944083 | **drop** |
| Hammer after a 5-day decline | 9501 | -0.0% (t -0.26) | 6028 | -0.2% (t -1.6) | +0.8% | 0.484 | 0.945201 | **drop** |
| Close crosses above the 200-day average | 9698 | -0.5% (t -3.32) | 5095 | -0.4% (t -1.65) | +0.3% | 0.465 | 0.950529 | **drop** |
| Up-day volume 1.5x down-day volume over 50 days, above the 50-day average | 16948 | -0.0% (t -0.27) | 8392 | -0.3% (t -1.65) | +0.3% | 0.468 | 0.950529 | **drop** |
| Close back inside the lower Bollinger band | 16010 | -0.0% (t -0.08) | 9271 | -0.4% (t -1.74) | +0.7% | 0.472 | 0.95907 | **drop** |
| CCI(20) crosses back above -100 | 27243 | -0.1% (t -0.98) | 15876 | -0.3% (t -1.77) | +0.6% | 0.476 | 0.961636 | **drop** |
| Close above a rising 200-day average, first day | 6430 | -0.1% (t -0.26) | 3484 | -0.5% (t -2.07) | +0.2% | 0.464 | 0.980774 | **drop** |
| RSI(14) crosses above 50 | 34129 | -0.1% (t -0.91) | 17808 | -0.2% (t -2.21) | +0.5% | 0.473 | 0.986447 | **drop** |
| Factor: bottom 10% by 12-1 month return (losers) | 3075 | -0.6% (t -1.34) | 1533 | -0.9% (t -2.4) | -0.3% | 0.416 | 0.991802 | **drop** |
| Relative strength line crosses above its 50-day average | 23746 | -0.3% (t -2.61) | 11713 | -0.3% (t -2.55) | +0.3% | 0.467 | 0.994614 | **drop** |
| Supertrend(10, 3) turns up | 7574 | -0.4% (t -2.1) | 4148 | -0.5% (t -2.58) | -0.0% | 0.464 | 0.99506 | **drop** |

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

- near: MACD crosses below its signal line: AUROPHARMA, BAJAJHFL, BBOX, BPCL, ELGIEQUIP, EMCURE, FEDERALBNK, FINCABLES, GICRE, GRAVITA, HINDPETRO, INDIANB, IOC, JINDALSAW, KALYANKJIL, NATCOPHARM, NBCC, PETRONET, PVRINOX, SHREECEM, SYNGENE, TBOTEK, ZYDUSLIFE
- near: Down 10%+ in 5 days: HFCL, IIFL, LLOYDSME, STLTECH, TTML
- near: Gap up 3%+ that holds into the close: JWL

## Every recommendation and what happened

The desk printed **553 trade plans** since 2026-11-13. **0** passed every check (a real call); the rest failed at least one check, most often the many-signals test, and were shown as plans only. Each plan is scored on Dhan daily bars: stop first if the stop and target are touched the same day, otherwise target, otherwise sold at the 21st close. Rupee results use the plan's own share count and 0.25% charges.

- Closed so far: 26 (target 11, stop 15, time exit 0); open: 527.
- All plans, including open ones marked to the last close: average -0.1%, -1.8% vs the Nifty, 0.275 beat the Nifty, Rs -21,882 if every plan had been taken.
- Closed plans only: average +0.2%, Rs -1,730.
- Real calls (all checks passed): 0.

| Signal | plans | closed | target / stop / time | average so far | vs Nifty so far | Rs if all taken |
|---|---|---|---|---|---|---|
| flag | 360 | 17 | 7 / 10 / 0 | -0.1% | -1.8% | -14,195 |
| don55 | 65 | 2 | 0 / 2 / 0 | -0.5% | -1.5% | -4,635 |
| nr7 | 27 | 1 | 1 / 0 / 0 | +0.6% | -0.7% | 513 |
| qdrop10 | 26 | 0 | 0 / 0 / 0 | +0.3% | -1.0% | 552 |
| downtrend | 24 | 3 | 2 / 1 / 0 | +0.9% | -1.3% | 1,027 |
| hi52v | 21 | 1 | 0 / 1 / 0 | -0.6% | -1.9% | -1,852 |
| volbreak | 19 | 1 | 1 / 0 / 0 | -1.1% | -2.4% | -1,401 |
| qdrop | 11 | 1 | 0 / 1 / 0 | -2.8% | -4.1% | -1,891 |

### The live track record (picks logged before the outcome)

| Kind | picks | vs Nifty so far | share ahead of Nifty |
|---|---|---|---|
| dips | 36 | -1.5% | 0.417 |
| rising | 186 | -1.5% | 0.247 |
| score0 | 80 | -1.4% | 0.275 |
| score2 | 301 | -1.9% | 0.286 |
| score4 | 186 | -1.4% | 0.312 |
| score6 | 68 | -1.4% | 0.324 |

Kinds: *rising* = tested breakout signals on leading stocks, *dips* = tested dip signals, *score0/2/4/6* = the research screener's score bands (score0 is a random control group). These are days old, so they say very little yet; they become meaningful after 21 trading days.

### Latest plans, newest first

| Day | Stock | Signal | Entry | Stop | Target | Qty | Called? | Status | Days | Return | vs Nifty | Rs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-25 | VIJAYA | hi52v | 1628 | 1460 | 1880 | 5 | no | open | 1 | -2.5% | -2.8% | -225 |
| 2026-11-25 | VEDL | qdrop10 | 232.75 | 216.5 | 257.25 | 42 | no | open | 1 | +2.3% | +2.0% | 196 |
| 2026-11-25 | UNITDSPR | don55 | 1514 | 1428 | 1644 | 6 | no | open | 1 | -1.7% | -1.9% | -176 |
| 2026-11-25 | UCOBANK | flag | 24.65 | 22.8 | 27.45 | 405 | no | open | 1 | -1.1% | -1.3% | -134 |
| 2026-11-25 | TRENT | don55 | 3320 | 3095 | 3660 | 3 | no | open | 1 | -1.7% | -2.0% | -197 |
| 2026-11-25 | THANGAMAYL | qdrop10 | 3845 | 3510 | 4350 | 2 | no | open | 1 | +2.7% | +2.5% | 191 |
| 2026-11-25 | TATASTEEL | qdrop | 159.25 | 138.75 | 190.0 | 48 | no | open | 1 | +2.7% | +2.4% | 187 |
| 2026-11-25 | TATAINVEST | flag | 582 | 540 | 645 | 17 | no | open | 1 | -0.1% | -0.4% | -38 |
| 2026-11-25 | TATACONSUM | don55 | 1186 | 1106 | 1306 | 8 | no | open | 1 | -1.9% | -2.1% | -200 |
| 2026-11-25 | STLTECH | qdrop | 580 | 498 | 703 | 12 | no | open | 1 | +1.6% | +1.4% | 95 |
| 2026-11-25 | SONACOMS | nr7 | 883 | 826 | 969 | 11 | no | open | 1 | -0.2% | -0.4% | -41 |
| 2026-11-25 | SIGNATURE | flag | 847 | 778 | 951 | 11 | no | open | 1 | +1.1% | +0.8% | 79 |
| 2026-11-25 | SBIN | flag | 1138 | 1078 | 1228 | 8 | no | open | 1 | -0.1% | -0.4% | -34 |
| 2026-11-25 | SAILIFE | flag | 1800 | 1670 | 1996 | 5 | no | open | 1 | +0.7% | +0.4% | 40 |
| 2026-11-25 | RKFORGE | flag | 746 | 682 | 842 | 13 | no | open | 1 | +5.6% | +5.4% | 520 |
| 2026-11-25 | RBLBANK | flag | 390.5 | 360.5 | 435.5 | 25 | no | open | 1 | -0.3% | -0.6% | -56 |
| 2026-11-25 | PVRINOX | flag | 1710 | 1592 | 1888 | 5 | no | open | 1 | -4.2% | -4.5% | -380 |
| 2026-11-25 | POWERINDIA | flag | 29750 | 26650 | 34400 | 0 | no | open | 1 | +2.0% | +1.7% | 0 |
| 2026-11-25 | PNB | flag | 148.5 | 137.0 | 165.75 | 67 | no | open | 1 | -0.7% | -0.9% | -92 |
| 2026-11-25 | PHOENIXLTD | nr7 | 2285 | 2140 | 2505 | 4 | no | open | 1 | +0.3% | +0.0% | 1 |
| 2026-11-25 | PFOCUS | qdrop10 | 239.25 | 207.25 | 287.25 | 31 | no | open | 1 | -1.1% | -1.4% | -102 |
| 2026-11-25 | NH | don55 | 2005 | 1875 | 2200 | 4 | no | open | 1 | -1.1% | -1.4% | -111 |
| 2026-11-25 | NEULANDLAB | flag | 20975 | 18975 | 23975 | 0 | no | open | 1 | +0.7% | +0.4% | 0 |
| 2026-11-25 | NATIONALUM | qdrop10 | 288.0 | 260.0 | 330.0 | 34 | no | open | 1 | +2.4% | +2.2% | 212 |
| 2026-11-25 | MEDANTA | nr7 | 1528 | 1434 | 1670 | 6 | no | open | 1 | -1.1% | -1.3% | -122 |
| 2026-11-25 | MARICO | don55 | 935 | 888 | 1006 | 10 | no | open | 1 | +0.4% | +0.2% | 18 |
| 2026-11-25 | MANAPPURAM | qdrop | 267.5 | 243.5 | 303.5 | 37 | no | open | 1 | +0.9% | +0.7% | 68 |
| 2026-11-25 | MAHABANK | flag | 98.7 | 90.8 | 110.6 | 101 | no | open | 1 | -4.6% | -4.8% | -479 |
| 2026-11-25 | M&MFIN | flag | 292.5 | 272.5 | 322.5 | 34 | no | open | 1 | -2.4% | -2.7% | -268 |
| 2026-11-25 | LLOYDSME | qdrop10 | 1606 | 1412 | 1898 | 5 | no | open | 1 | -4.0% | -4.2% | -339 |
| 2026-11-25 | LICHSGFIN | flag | 598 | 561 | 654 | 16 | no | open | 1 | -0.3% | -0.5% | -52 |
| 2026-11-25 | LGEINDIA | hi52v | 1818 | 1630 | 2100 | 5 | no | open | 1 | -3.3% | -3.5% | -322 |
| 2026-11-25 | KARURVYSYA | flag | 379.0 | 352.0 | 419.5 | 26 | no | open | 1 | -2.4% | -2.6% | -259 |
| 2026-11-25 | KALYANKJIL | flag | 636 | 561 | 749 | 13 | no | open | 1 | +0.6% | +0.3% | 29 |
| 2026-11-25 | J&KBANK | don55 | 155.25 | 135.75 | 184.5 | 51 | no | open | 1 | +4.9% | +4.6% | 366 |
| 2026-11-25 | ITC | don55 | 309.0 | 296.0 | 328.5 | 32 | no | open | 1 | -0.6% | -0.9% | -89 |
| 2026-11-25 | IRB | flag | 17.35 | 15.65 | 19.9 | 576 | no | open | 1 | -0.2% | -0.5% | -48 |
| 2026-11-25 | IOC | nr7 | 147.75 | 138.5 | 161.75 | 67 | no | open | 1 | -2.3% | -2.5% | -248 |
| 2026-11-25 | INDIGO | don55 | 5720 | 5340 | 6290 | 1 | no | open | 1 | -1.7% | -1.9% | -109 |
| 2026-11-25 | INDIANB | flag | 930 | 864 | 1029 | 10 | no | open | 1 | +0.3% | +0.1% | 7 |
| 2026-11-25 | IIFL | nr7 | 610 | 557 | 690 | 16 | no | open | 1 | -2.6% | -2.9% | -281 |
| 2026-11-25 | IGL | flag | 149.75 | 139.25 | 165.5 | 66 | no | open | 1 | -1.0% | -1.3% | -125 |
| 2026-11-25 | HONASA | flag | 536 | 496 | 596 | 18 | no | open | 1 | -0.5% | -0.8% | -74 |
| 2026-11-25 | HINDUNILVR | don55 | 2140 | 1955 | 2420 | 4 | no | open | 1 | -0.4% | -0.7% | -58 |
| 2026-11-25 | HINDCOPPER | qdrop10 | 399.0 | 352.5 | 469.0 | 21 | no | open | 1 | +3.0% | +2.8% | 234 |
| 2026-11-25 | HFCL | qdrop | 170.0 | 145.0 | 207.5 | 40 | no | open | 1 | -3.4% | -3.6% | -246 |
| 2026-11-25 | HEROMOTOCO | don55 | 5750 | 5400 | 6280 | 1 | no | open | 1 | +0.7% | +0.4% | 25 |
| 2026-11-25 | HEGAM | flag | 258.5 | 234.0 | 295.5 | 38 | no | open | 1 | +8.7% | +8.4% | 830 |
| 2026-11-25 | HDFCLIFE | flag | 601 | 560 | 663 | 16 | no | open | 1 | -1.1% | -1.4% | -130 |
| 2026-11-25 | GODREJCP | don55 | 963 | 902 | 1055 | 10 | no | open | 1 | -1.6% | -1.9% | -179 |
| 2026-11-25 | GMRAIRPORT | flag | 102.75 | 95.25 | 114.0 | 97 | no | open | 1 | -1.5% | -1.8% | -175 |
| 2026-11-25 | GMDCLTD | flag | 455.0 | 407.5 | 526.5 | 21 | no | open | 1 | +0.1% | -0.1% | -11 |
| 2026-11-25 | GLENMARK | don55 | 2720 | 2545 | 2985 | 3 | no | open | 1 | +0.7% | +0.5% | 40 |
| 2026-11-25 | FORCEMOT | flag | 20400 | 18650 | 23025 | 0 | no | open | 1 | -0.2% | -0.4% | -0 |
| 2026-11-25 | FIVESTAR | flag | 424.5 | 389.5 | 477.0 | 23 | no | open | 1 | -2.6% | -2.9% | -283 |
| 2026-11-25 | EMCURE | nr7 | 2315 | 2175 | 2525 | 4 | no | open | 1 | +0.6% | +0.4% | 33 |
| 2026-11-25 | EMAMILTD | don55 | 427.5 | 400.5 | 468.0 | 23 | no | open | 1 | -1.4% | -1.6% | -158 |
| 2026-11-25 | EIHOTEL | don55 | 340.0 | 312.5 | 381.5 | 29 | no | open | 1 | -2.1% | -2.4% | -236 |
| 2026-11-25 | EICHERMOT | hi52v | 8340 | 7910 | 8990 | 1 | no | open | 1 | -1.9% | -2.2% | -181 |
| 2026-11-25 | DELHIVERY | flag | 462.0 | 432.0 | 507.0 | 21 | no | open | 1 | -0.3% | -0.6% | -56 |
| 2026-11-25 | DABUR | don55 | 430.0 | 397.0 | 479.5 | 23 | no | open | 1 | -2.7% | -2.9% | -289 |
| 2026-11-25 | BPCL | nr7 | 310.0 | 291.0 | 338.5 | 32 | no | open | 1 | -0.8% | -1.0% | -100 |
| 2026-11-25 | BLUESTARCO | don55 | 1822 | 1670 | 2050 | 5 | no | open | 1 | -2.3% | -2.5% | -232 |
| 2026-11-25 | BELRISE | flag | 241.75 | 221.25 | 272.5 | 41 | no | open | 1 | -0.3% | -0.5% | -53 |
| 2026-11-25 | BANKINDIA | flag | 160.0 | 146.75 | 180.0 | 62 | no | open | 1 | +0.2% | -0.1% | -7 |
| 2026-11-25 | BANKBARODA | flag | 276.5 | 256.0 | 307.5 | 36 | no | open | 1 | -0.7% | -0.9% | -93 |
| 2026-11-25 | BANDHANBNK | flag | 171.75 | 159.0 | 191.0 | 58 | no | open | 1 | -1.3% | -1.6% | -156 |
| 2026-11-25 | BAJFINANCE | don55 | 1132 | 1052 | 1252 | 8 | no | open | 1 | -3.0% | -3.3% | -296 |
| 2026-11-25 | AUBANK | flag | 1006 | 936 | 1112 | 9 | no | open | 1 | -2.4% | -2.6% | -239 |
| 2026-11-25 | ASAHIINDIA | flag | 1196 | 1112 | 1322 | 8 | no | open | 1 | -0.5% | -0.8% | -73 |
| 2026-11-25 | APLAPOLLO | qdrop | 1476 | 988 | 2208 | 2 | no | open | 1 | +0.4% | +0.1% | 4 |
| 2026-11-25 | ANURAS | flag | 1316 | 1218 | 1464 | 7 | no | open | 1 | +0.6% | +0.4% | 36 |
| 2026-11-25 | ABSLAMC | flag | 959 | 884 | 1072 | 10 | no | open | 1 | +3.5% | +3.2% | 308 |
| 2026-11-25 | ABDL | flag | 807 | 741 | 906 | 12 | no | open | 1 | +1.6% | +1.4% | 135 |
| 2026-11-23 | ZEEL | flag | 71.6 | 63.8 | 83.3 | 128 | no | open | 2 | -7.8% | -9.9% | -740 |
| 2026-11-23 | WELSPUNLIV | hi52v | 271.0 | 243.5 | 312.5 | 36 | no | open | 2 | +3.5% | +1.3% | 312 |
| 2026-11-23 | VIJAYA | hi52v | 1572 | 1432 | 1782 | 6 | no | open | 2 | +1.0% | -1.1% | 67 |
| 2026-11-23 | VEDL | qdrop10 | 235.5 | 218.25 | 261.5 | 42 | no | open | 2 | +1.1% | -1.0% | 80 |
| 2026-11-23 | VBL | flag | 427.0 | 401.5 | 465.5 | 23 | no | open | 2 | +0.3% | -1.8% | 8 |
| 2026-11-23 | THERMAX | downtrend | 2705 | 2515 | 2990 | 3 | no | open | 2 | -1.1% | -3.2% | -108 |

Full ledger: `journal/recommendations.json` (553 plans).

## Rule changes

- None yet.

## Daily log, newest first

- **2026-11-26** (run 26 Nov 2026 21:37 IST): Nifty 50 closed at 25,884.5 (above its 200-day average, so the desk used its rising-market rules). 497 stocks loaded from Dhan. Desk signals passing its own back-test: 7 for rising markets, 1 for weak markets. Trade plans printed: 0, real calls (every check passed): 0. Indicator lab: 0 kept of 78. All plans so far: 553 (26 closed, 527 open).

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

