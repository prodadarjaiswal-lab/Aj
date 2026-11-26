# Evidence Desk journal

Last updated by the daily run: **26 Nov 2026 22:27 IST**, market data as of the close of **2026-11-26**. This file is rebuilt automatically every run. Research software, not advice.

## Today in one paragraph

Nifty 50 closed at 25,884.5 (above its 200-day average, so the desk used its rising-market rules). 497 stocks loaded from Dhan. Desk signals passing its own back-test: 8 for rising markets, 1 for weak markets. Trade plans printed: 81, real calls (every check passed): 0. Indicator lab: 0 kept of 78. All plans so far: 634 (26 closed, 608 open).

## Today's playbook (feeds the Trading Terminal)

**Market type: rising** since 2026-11-11. Rising market: Nifty above its 200-day average and up 3%+ over 63 sessions. The terminal's at-a-glance cards, its screen order and the back-test picks all follow this section, and the trade plans skip any signal the back-test warns against in this market type. Rebuilt every run, so it changes when the market type changes or the evidence moves.

Grades: **proven** passed every check including the many-ideas correction; **leaning** was positive before and after the cut-off in this market type (t 1.5+ both times) and beat the Nifty after charges, but has not survived the many-ideas correction, so it is a lead; **avoid** was reliably worse than the average stock in this market type.

### Favoured in a rising market

| Indicator | grade | vs average stock after | t | vs Nifty after charges | cases | before cut-off | fired today |
|---|---|---|---|---|---|---|---|
| New 52-week closing high on 1.5x average volume | leaning | +1.5% | 2.75 | +2.1% | 4475 | +0.9% (t 1.6) | ACE, ANANDRATHI, BAJAJHLDNG, MCX, PRESTIGE |
| Relative strength line vs Nifty at a 1-year high | leaning | +1.1% | 2.26 | +1.7% | 2958 | +1.0% (t 1.89) | none |
| Up 10%+ in 10 days | leaning | +0.9% | 3.17 | +1.4% | 4021 | +0.5% (t 2.07) | ABSLAMC, ACE, ANURAS, BRIGADE, DOMS, GODREJPROP, JWL, PRESTIGE |
| Up day on 2x the 50-day average volume | leaning | +0.4% | 1.59 | +1.1% | 8556 | +0.6% (t 2.59) | ACE, APLAPOLLO, BALRAMCHIN, BRIGADE, BRITANNIA, DEEPAKFERT, DOMS, ENRIN, FACT, HDFCBANK, HEGAM, J&KBANK +10 |

### Warnings in a rising market

| Indicator | grade | vs average stock after | t | vs Nifty after charges | cases | before cut-off | fired today |
|---|---|---|---|---|---|---|---|
| Close back inside the lower Bollinger band | avoid | -1.4% | -2.3 | -0.1% | 2496 | -0.2% (t -0.47) | JBMA, KEI, MRPL, NATIONALUM, NTPCGREEN, PFOCUS, TARIL, TATAPOWER, TATASTEEL |
| Factor: bottom 10% by 12-1 month return (losers) | avoid | -1.3% | -2.23 | -0.1% | 705 | -0.9% (t -1.8) | ABREL, ACC, AFCONS, AMBUJACEM, AWL, BATAINDIA, BDL, BLS, CHOLAHLDNG, COCHINSHIP, EIDPARRY, FIRSTCRY +37 |
| Factor: bottom 10% by last month's return (short-term reversal) | avoid | -1.0% | -1.85 | +0.1% | 705 | -0.5% (t -1.4) | APLAPOLLO, APTUS, ASTRAL, AZAD, BHARTIHEXA, CAPLIPOINT, CARBORUNIV, CARTRADE, CHENNPETRO, CLEAN, CONCORDBIO, CRISIL +37 |
| Close above a rising 200-day average, first day | avoid | -0.8% | -1.87 | +0.2% | 1231 | -0.1% (t -0.26) | CIPLA, ENDURANCE, GMRAIRPORT, GODREJPROP, INDUSINDBK, TDPOWERSYS |

### Market type history (from this journal)

- 2026-11-26 to 2026-11-26: rising (4 indicators favoured at the start)

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

- near: Factor: top 10% by 12-month return skipping the last month (momentum): ACMESOLAR, ACUTAAS, AEGISLOG, AETHER, ANANDRATHI, APARINDS, ATHERENERG, AZAD, BBOX, CEMPRO, CHENNPETRO, CPPLUS, CRAFTSMAN, CUPID, DIVISLAB, FEDERALBNK, FINCABLES, GESHIP, GLAND, GRANULES, HFCL, HONASA, INOXINDIA, JINDALSAW, KIRLOSENG, LAURUSLABS, LENSKART, LLOYDSME, MCX, MOTHERSON and 19 more
- near: MACD crosses below its signal line: AUROPHARMA, BAJAJHFL, BBOX, BPCL, ELGIEQUIP, EMCURE, FEDERALBNK, FINCABLES, GICRE, GRAVITA, HINDPETRO, INDIANB, IOC, JINDALSAW, KALYANKJIL, NATCOPHARM, NBCC, PETRONET, PVRINOX, SHREECEM, SYNGENE, TBOTEK, ZYDUSLIFE
- near: Down 10%+ in 5 days: HFCL, IIFL, LLOYDSME, STLTECH, TTML
- near: Gap up 3%+ that holds into the close: JWL

## Every recommendation and what happened

The desk printed **634 trade plans** since 2026-11-13. **0** passed every check (a real call); the rest failed at least one check, most often the many-signals test, and were shown as plans only. Each plan is scored on Dhan daily bars: stop first if the stop and target are touched the same day, otherwise target, otherwise sold at the 21st close. Rupee results use the plan's own share count and 0.25% charges.

- Closed so far: 26 (target 11, stop 15, time exit 0); open: 608.
- All plans, including open ones marked to the last close: average -0.1%, -1.8% vs the Nifty, 0.275 beat the Nifty, Rs -21,882 if every plan had been taken.
- Closed plans only: average +0.2%, Rs -1,730.
- Real calls (all checks passed): 0.

| Signal | plans | closed | target / stop / time | average so far | vs Nifty so far | Rs if all taken |
|---|---|---|---|---|---|---|
| flag | 376 | 17 | 7 / 10 / 0 | -0.1% | -1.8% | -14,195 |
| don55 | 81 | 2 | 0 / 2 / 0 | -0.5% | -1.5% | -4,635 |
| nr7 | 50 | 1 | 1 / 0 / 0 | +0.6% | -0.7% | 513 |
| qdrop10 | 33 | 0 | 0 / 0 / 0 | +0.3% | -1.0% | 552 |
| volbreak | 27 | 1 | 1 / 0 / 0 | -1.1% | -2.4% | -1,401 |
| hi52v | 26 | 1 | 0 / 1 / 0 | -0.6% | -1.9% | -1,852 |
| downtrend | 24 | 3 | 2 / 1 / 0 | +0.9% | -1.3% | 1,027 |
| qdrop | 17 | 1 | 0 / 1 / 0 | -2.8% | -4.1% | -1,891 |

### The live track record (picks logged before the outcome)

| Kind | picks | vs Nifty so far | share ahead of Nifty |
|---|---|---|---|
| dips | 49 | -1.1% | 0.306 |
| rising | 232 | -1.2% | 0.198 |
| score0 | 100 | -1.1% | 0.22 |
| score2 | 317 | -1.8% | 0.271 |
| score4 | 195 | -1.4% | 0.297 |
| score6 | 81 | -1.2% | 0.272 |

Kinds: *rising* = tested breakout signals on leading stocks, *dips* = tested dip signals, *score0/2/4/6* = the research screener's score bands (score0 is a random control group). These are days old, so they say very little yet; they become meaningful after 21 trading days.

### Latest plans, newest first

| Day | Stock | Signal | Entry | Stop | Target | Qty | Called? | Status | Days | Return | vs Nifty | Rs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-26 | WOCKPHARMA | volbreak | 2235 | 1905 | 2730 | 3 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | WELSPUNLIV | don55 | 280.5 | 255.0 | 319.0 | 35 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | UBL | nr7 | 1272 | 1202 | 1378 | 7 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | TRENT | nr7 | 3265 | 3035 | 3610 | 3 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | TORNTPHARM | don55 | 5020 | 4740 | 5440 | 1 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | TCS | don55 | 2640 | 2480 | 2880 | 3 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | TATASTEEL | qdrop10 | 163.5 | 145.75 | 190.25 | 56 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | STLTECH | qdrop | 589 | 509 | 709 | 12 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | SIGNATURE | flag | 856 | 792 | 952 | 11 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | SHYAMMETL | nr7 | 1292 | 1200 | 1430 | 7 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | SBIN | flag | 1136 | 1082 | 1218 | 8 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | SBICARD | nr7 | 586 | 555 | 633 | 17 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | SANSERA | nr7 | 4685 | 4255 | 5330 | 2 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | RUBICON | volbreak | 1852 | 1578 | 2264 | 3 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | RELIANCE | don55 | 1396 | 1334 | 1490 | 7 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | RAMCOCEM | nr7 | 828 | 785 | 893 | 12 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | PRESTIGE | hi52v | 1832 | 1674 | 2070 | 5 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | PNB | nr7 | 147.5 | 137.0 | 163.25 | 67 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | PIDILITIND | nr7 | 1604 | 1516 | 1736 | 6 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | PFOCUS | qdrop | 236.5 | 207.75 | 279.75 | 34 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | OBEROIRLTY | volbreak | 1906 | 1786 | 2086 | 5 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | NATIONALUM | qdrop10 | 295.0 | 267.0 | 337.0 | 33 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | MCX | hi52v | 3835 | 3415 | 4465 | 2 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | MAXHEALTH | flag | 1082 | 1004 | 1200 | 9 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | MARICO | don55 | 939 | 896 | 1004 | 10 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | MANAPPURAM | qdrop | 270.0 | 248.0 | 303.0 | 37 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | M&M | flag | 3490 | 3250 | 3850 | 2 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | LODHA | don55 | 1262 | 1156 | 1422 | 7 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | LLOYDSME | qdrop10 | 1542 | 1350 | 1830 | 5 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | LAURUSLABS | don55 | 2505 | 2310 | 2800 | 3 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | KPRMILL | nr7 | 1190 | 1100 | 1326 | 8 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | KOTAKBANK | nr7 | 510 | 485 | 548 | 19 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | KFINTECH | don55 | 995 | 851 | 1211 | 6 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | KARURVYSYA | flag | 370.0 | 341.0 | 413.5 | 27 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | KALYANKJIL | flag | 640 | 574 | 739 | 15 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | JWL | volbreak | 238.75 | 189.0 | 313.5 | 20 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | JSWSTEEL | nr7 | 1304 | 1240 | 1400 | 7 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | JINDALSTEL | nr7 | 1114 | 1040 | 1226 | 8 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | J&KBANK | don55 | 162.75 | 142.25 | 193.5 | 48 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | IIFL | qdrop10 | 594 | 531 | 689 | 15 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | IGIL | flag | 423.0 | 390.5 | 472.0 | 23 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | IDFCFIRSTB | flag | 86.7 | 81.5 | 94.5 | 115 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | IDEA | qdrop10 | 11.6 | 10.25 | 13.65 | 740 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | ICICILIFE | nr7 | 468.5 | 440.0 | 511.5 | 21 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | HONASA | flag | 533 | 494 | 592 | 18 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | HFCL | qdrop | 164.25 | 140.25 | 200.25 | 41 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | HEROMOTOCO | don55 | 5790 | 5440 | 6320 | 1 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | HDFCBANK | don55 | 862 | 801 | 954 | 11 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | HAVELLS | nr7 | 1180 | 1106 | 1292 | 8 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | GODREJPROP | volbreak | 2005 | 1825 | 2275 | 4 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | GLENMARK | don55 | 2740 | 2570 | 2995 | 3 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | FORCEMOT | flag | 20350 | 18625 | 22950 | 0 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | FLUOROCHEM | nr7 | 4780 | 4400 | 5350 | 2 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | ENDURANCE | volbreak | 2695 | 2505 | 2980 | 3 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | DOMS | don55 | 2300 | 2140 | 2540 | 4 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | DLF | don55 | 808 | 763 | 876 | 12 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | DIVISLAB | flag | 11625 | 10875 | 12750 | 0 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | DELHIVERY | nr7 | 460.5 | 431.0 | 505.0 | 21 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | DEEPAKFERT | flag | 1442 | 1302 | 1652 | 6 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | DATAPATTNS | nr7 | 4155 | 3770 | 4735 | 2 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | CIPLA | don55 | 1450 | 1382 | 1552 | 6 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | CEMPRO | nr7 | 1424 | 1310 | 1596 | 7 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | CAPLIPOINT | qdrop | 2005 | 1820 | 2285 | 4 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | BSOFT | nr7 | 303.5 | 281.0 | 337.5 | 32 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | BRITANNIA | don55 | 5180 | 4820 | 5720 | 1 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | BRIGADE | volbreak | 628 | 577 | 705 | 15 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | BIOCON | nr7 | 365.0 | 343.0 | 398.0 | 27 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | BHARTIHEXA | qdrop10 | 1536 | 1430 | 1696 | 6 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | BANKINDIA | flag | 160.25 | 147.0 | 180.25 | 62 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | BANKBARODA | flag | 274.5 | 255.5 | 303.0 | 36 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | BANDHANBNK | nr7 | 169.5 | 156.75 | 188.75 | 58 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | BAJAJHLDNG | hi52v | 11925 | 11000 | 13325 | 0 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | AXISBANK | flag | 1408 | 1324 | 1534 | 7 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | ATHERENERG | nr7 | 1906 | 1682 | 2242 | 4 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | ASHOKLEY | qdrop10 | 156.25 | 143.75 | 175.0 | 64 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | APOLLOHOSP | nr7 | 9220 | 8790 | 9870 | 1 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | APLAPOLLO | qdrop | 1482 | 1038 | 2148 | 2 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | ANANDRATHI | hi52v | 2410 | 2300 | 2575 | 4 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | ACE | hi52v | 1296 | 1166 | 1492 | 7 | no | open | 0 | n/a | n/a | 0 |
| 2026-11-26 | ABSLAMC | volbreak | 992 | 911 | 1114 | 10 | no | open | 0 | n/a | n/a | 0 |

Full ledger: `journal/recommendations.json` (634 plans).

## The desk's own signal back-test

The 30 signals behind the desk's buy lists, re-tested every run on Dhan daily data from 2015-10-30 (out-of-sample from 2024-11-26, 497 stocks). 8 pass the desk's single-signal test in rising markets; 0 of 30 survive the joint many-signals test (risk lab), which is why the desk makes no real calls. Moved here from the Trading Terminal so the terminal stays a clean screen.

| Signal | passes (rising) | passes (weak) | cases after | 10-day vs Nifty after | lift vs average stock | many-signals p | survives |
|---|---|---|---|---|---|---|---|
| Relative strength line at a 1-year high before the price is | yes | no | 273 | +1.76% | +1.54% | 0.434 | no |
| Gap up of 3% or more that holds into the close on 2x volume | no | yes | 234 | +1.69% | +1.46% | 0.434 | no |
| New 52-week closing high on 1.5x average volume | yes | no | 1041 | +1.56% | +1.34% | 0.434 | no |
| Proven stock 25% below its 52-week high, first close back above its 20-day average | no | no | 858 | +1.46% | +1.23% | 0.434 | no |
| Proven stock (beat the Nifty by 20%+ over 2 years) falls 15%+ within 10 days | yes | no | 158 | +1.34% | +1.11% | 0.434 | no |
| Bull flag: up 10%+ over 10 days, then 5 days inside a 5% range (trader-scanner) | yes | no | 2065 | +1.12% | +0.90% | 0.434 | no |
| Proven stock (beat the Nifty by 20%+ over 2 years) falls 10%+ within 10 days | yes | no | 731 | +0.96% | +0.74% | 0.434 | no |
| Donchian breakout: close above the 55-day high (turtle rule) | yes | no | 2532 | +0.81% | +0.59% | 0.434 | no |
| Oversold bounce: RSI(14) under 30 yesterday, closes up today (trader-scanner) | no | no | 1505 | +0.76% | +0.54% | 0.434 | no |
| Tightest range in 7 days, inside the prior bar, in an uptrend | yes | no | 3236 | +0.72% | +0.50% | 0.434 | no |
| Proven stock (beat the Nifty by 20%+ over 2 years) falls 25%+ within 20 days | no | no | 39 | +0.68% | +0.46% | 0.434 | no |
| Volume breakout above the 20-day high (existing setup) | yes | no | 2490 | +0.54% | +0.32% | 0.434 | no |
| MACD crosses above its signal line while above zero | no | no | 1738 | +0.50% | +0.27% | 0.434 | no |
| Strong trend starting: ADX(14) crosses above 25 with buyers in control | no | no | 1097 | +0.41% | +0.19% | 0.434 | no |
| 20-day closing-high breakout with turnover of Rs 10 crore or more (nse-day-trader / trader-scanner) | no | no | 6601 | +0.41% | +0.19% | 0.434 | no |
| Overextended: RSI(14) over 80 and 25% above the 50-day average (warning) | no | no | 118 | +0.41% | +0.19% | 0.434 | no |
| Trend template: price above rising 50, 150 and 200-day averages, near its 52-week high | no | no | 1387 | +0.33% | +0.11% | 0.434 | no |
| Pullback in an uptrend (existing setup) | no | no | 1955 | +0.31% | +0.09% | 0.434 | no |
| Downtrend: below a falling 200-day average and 50-day below 200-day (warning) | no | no | 866 | +0.30% | +0.08% | 0.434 | no |
| Accumulation: up-day volume 1.5x down-day volume over 50 days, above the 50-day average | no | no | 2886 | +0.27% | +0.05% | 0.434 | no |
| Three down closes in a row while above the 200-day average | no | no | 3275 | +0.19% | -0.04% | 0.434 | no |
| Supertrend(10, 3) turns up | no | no | 1435 | +0.17% | -0.06% | 0.434 | no |
| Closes in the bottom 20% of its day's range while above the 200-day average | no | no | 9336 | +0.16% | -0.06% | 0.434 | no |
| Closes back above the 20-day average after 5+ days below, in an uptrend (trader-scanner) | no | no | 1471 | +0.16% | -0.06% | 0.434 | no |
| Closes back above the 200-day average after 20+ days below | no | no | 512 | +0.16% | -0.07% | 0.434 | no |
| Proven stock (beat the Nifty by 20%+ over 2 years) falls to 25% below its 52-week high | no | no | 897 | +0.14% | -0.08% | 0.434 | no |
| Short dip in an uptrend: RSI(2) under 10 while above the 200-day average | no | no | 3041 | +0.10% | -0.12% | 0.434 | no |
| Bollinger squeeze breakout: band width in its lowest 20% of 6 months, close above the upper band | no | no | 1525 | +0.10% | -0.13% | 0.434 | no |
| Oversold: RSI(14) under 30 (trader-scanner) | no | no | 1076 | -0.03% | -0.25% | 0.434 | no |
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

