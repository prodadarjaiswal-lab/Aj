# Market view, 2026-11-25

Research software, not advice. Dhan daily history 2010-01-04 to 2026-11-25; out of sample from 2023-11-26.

**Market type today: Rising market** (Nifty +6.6% over 63 sessions, +7.6% vs its 200-day average).

## Popular beliefs, tested

| Belief | Verdict | In-sample (avg, t) | Out of sample (avg, t, worked) | Months OOS |
|---|---|---|---|---|
| Bank Nifty is the index to buy in a flat market | **UNPROVEN** | +0.08%, t 0.29 | +0.73%, t 1.92, 66% | 24 |
| Bank Nifty is a no-brainer (beats the Nifty in any market) | **UNPROVEN** | +0.23%, t 0.99 | +0.26%, t 0.82, 61% | 36 |
| Bank Nifty leads the Nifty | **UNPROVEN** | +0.05%, t 0.53 | +0.03%, t 0.18, 52% | 34 |
| Exchange, broker and AMC stocks win in a slow market | **UNPROVEN** | +0.10%, t 0.16 | +2.06%, t 1.53, 57% | 24 |
| After a sharp fall the Nifty bounces | **UNPROVEN** | +0.94%, t 2.98 | +1.42%, t 1.97, 54% | 12 |
| After a sharp rise the Nifty gives some back | **UNPROVEN** | +0.06%, t -0.3 | -0.33%, t 0.73, 35% | 15 |
| Last month's worst sector bounces (mean reversion) | **UNPROVEN** | +0.17%, t 0.34 | +0.71%, t 0.68, 59% | 33 |
| The strongest sector keeps winning (momentum) | **UNPROVEN** | +0.45%, t 0.86 | +0.32%, t 0.31, 56% | 33 |
| A sector that lagged for a year is cheap and catches up | **FAILS** | -0.46%, t -0.51 | -4.31%, t -2.37, 40% | 25 |

Worked = share of cases where the belief was right. Averages are per case, over the belief's horizon (1 month, 5 sessions for the lead and bounce beliefs, 6 months for the laggard belief).

## Forecast track record (walk-forward, no look-ahead)

- Next-session Nifty direction from market type + today's move: right 53% of 3435 days, vs 54% for simply saying 'up' every day.
- Monthly sector rotation (hold the sector that did best in this market type before): average +0.03% a month vs the Nifty, beat it in 49% of 162 months, t 0.07.

Tomorrow: in this setup (rising / up) the Nifty rose the next session 65% of 205 times.

## Sectors in this market type (1-month excess vs Nifty)

| Sector | In-sample | Out of sample | OOS worked |
|---|---|---|---|
| Nifty Smallcap 100 | +1.36% | +0.27% | 52% |
| Nifty IT | +1.14% | +0.71% | 60% |
| Nifty Midcap 100 | +0.50% | +0.58% | 60% |
| Nifty Pharma | +0.49% | +0.91% | 60% |
| Nifty Next 50 | +0.42% | +0.99% | 65% |
| Nifty Private Bank | +0.32% | -0.57% | 41% |
| Nifty Metal | +0.23% | +1.69% | 59% |
| Nifty Media | +0.19% | -2.30% | 25% |
| Nifty FMCG | +0.15% | -1.06% | 38% |
| Nifty Financial Services | +0.11% | -0.00% | 53% |
| Nifty PSU Bank | +0.10% | +1.50% | 52% |
| Nifty Bank | +0.08% | +0.04% | 58% |
| Nifty Realty | +0.01% | -0.03% | 46% |
| Nifty Auto | -0.01% | +1.01% | 69% |
| Nifty Commodities | -0.20% | +0.63% | 57% |
| Nifty PSE | -0.32% | +1.33% | 54% |
| Nifty Energy | -0.38% | +0.47% | 46% |
| Nifty Infrastructure | -0.42% | +0.56% | 54% |

## Not testable yet

- FII / DII flows: only a few days are stored (docs/nse-feeds.json), so flow-driven views cannot be back-tested yet; each day's figures are now kept so they can be later.
- Valuation (P/E) of sector indices: no history in the data, so 'cheap' is tested with a price proxy.
