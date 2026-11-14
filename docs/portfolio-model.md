# Portfolio-management notes from Google Drive: research report

Purpose: design a "does this stock suit my portfolio" model (NSE + few US stocks; Dhan data).
Faithfulness note: much of the Drive material is handwritten class notes (CFA L1 Portfolio Mgmt, "Sanjay Saraf" classes) whose OCR text is badly garbled; where I could only partly recover a rule I say so. Damodaran session slides and the typed asset-management notes are clean.

## 1. Files found / read

Drive is large (hundreds of PDFs). Search surfaced these relevant groups.

### Fully read (text extracted)
| File | id | Type | Modified |
|---|---|---|---|
| PM LM 2 ALL CLASSES COMBINED NOTES.pdf (LM2 Risk&Return Part II, classes 1-10; readable, best source) | 1DXx9yEuA9mTHWrwjq1jjLaKdl0zTXlgv | pdf | 2025-07-17 |
| PM LM1 Risk&Return Part I, CW Lecture Notes class 1,2,3,4,5,6,7,9 | 1MdsT5YskKZfz9sbp6Xav8ORHpZ5dmCm6; 1Fat40ACR7lgczE7--04ABJeJSlTm81O0; 1bxMgb2AouTECE5771Rbw0i2n54r5RNNM; 1xdCv503_iGbW4GdzMKBfCQqkXJsX5VL_; 1ThRMi_E5GY-AkAH6nR4iFfyokYbNLwiV; 108C-dv2xIaHlnv0iwO8i-p9PsaCajg-3; 1Fl6hgGptgXjn1HGdP0_fmpLh-LYFOxpr; 1tjiAgGYszZyMAHRHuZ7UIZLKvtXHHwFP | pdf | 2025-06 (OCR mostly garbled: classes 1,2,4,5,6,7,9; class 3 fairly readable) |
| CFA L1 PORTFOLIO LM 3 CLASS 2 CW LECTURE NOTES.pdf (IPS / planning process; garbled) | 1D5jMwmTQQ_3e7rABHqhknQyyaLX1cIox | pdf | 2025-06-20 |
| CFA L1 PM LM 3 CLASS 5 CW Q & A.pdf (pooled investments) | 1dPxI9cyFpUaQ1fEvOUfedpd-EtMFhsuM | pdf | 2025-06-20 |
| THE ASSET MANAGEMENT INDUSTRY FORMAL NOTES.pdf | 11VkUDN_0b-GsqiPqEWq-BR8XqzOj7pys | pdf | 2025-06-20 |
| COVERAGE IN PORTFOLIO CLASS.xlsx (syllabus outline) | 1MCxOwTbFnDb4zD6Q51Vf9_SGFlPszCvQ | xlsx | 2025-06-20 |
| Damodaran Valuation course, folder "Valuation_Investment philosophy" (id 1AeFqcjEKr9hkXy8Ir3ZMuky6jpKu9QC0): session4 (equity risk) 1u0hwPkbrClzra2yQU6oCeoy2WUIJnNQS; session5 (cash flows, growth, risk) 1KnXtII9QTZWB6SCeg5CfjmBIQXmQEaHE; session8 (market efficiency II, performance measures) 1egkTTTbVUiJLeQo087-Uhno17fZyKHT8; session16 (value investing) 1mvOfxP3wdouGa6yeDwENoeeWIPGy-Hgd; session26 (public information/acquisitions) 1TfV1ufj-4IBhP7b2MsTQp7cFzCokwAHC; session28 (near arbitrage) 1ojrZpbqOeB47YzRvEpfY5uhLM0u3CZxT; session29 (pseudo arbitrage, hedge funds) 1j45YmRl5mfEpA7VtyDhStbsIagmjKXZg; session30 (market timing) 1XraJOeRbHpHP_SAK94jFRsH8All_cPCa; session31 (timing indicators) 170ReLWVhUaYfZBN5UXcGsvYxG7Ov9QJf; session33 (market valuation) 1-92PTBMybgghglTVxqv6vV148bG0olpi; session34 (does timing work) 1WU_x7eFVHiOCVENAntCmd91asfTGBDCe | pdf | Aug-Sep 2026 |

### Found but NOT read (honest gaps)
- Remaining Damodaran sessions 1-3, 6, 7, 9-15, 17-25, 27, 32 and all "sessionNsoln.pdf" solution files, plus narrative&numbers.pdf (id 1pVOza8l5fX6ENs6nJwjWEGi3l5Zrl6Sh). Not read for time/context reasons. Likely contain more on relative valuation, growth/value/quality screens, technical analysis; the model could be enriched from them.
- Remaining PM LM1 class 8, 10 notes and LM1/LM2 "Q & A" files (many; CW/HW classes 2-10), PM LM2 Part II individual lecture notes (classes 3,6,7,10; content is covered by the combined LM2 file), CFA L1 PM LM3 Q&A classes 1,2,3,4,6, "PORTFOLIO MATHEMATICS CLASS 1 & 2 CW Q & A.pdf" (1qn7G2DHmpYR-D-zhpuflW354_wf4HMxg), CFA 2025 Level I big books "Quants, Eco, CI" (1nHxCrYmYwBCXLIJOvFSD3m38Zrh_9tsE, ~4MB) and "FSA, Equity" (1FZYm2TnsjenX7DquR_Rh_fAHwEpu92-t, ~8MB), CFA L1 Equity LM2/LM3/LM8 and FSA Q&A (equity valuation, industry analysis), CFA Daily Brief Google Docs (economics only).
- No file in the Drive search covers: Markowitz-specific "marginal risk contribution", sector concentration limits, max single-stock weight, cash-buffer %, rebalancing bands, or option hedging. Searches for "hedge", "value at risk", "margin of safety", "investment policy statement" only hit the files above. So thresholds for those are ASSUMED below.

## 2. Rules, formulas and frameworks (with source)

### A. Diversification / correlation (LM1 Part I; LM2)
1. Two-asset portfolio: wp = wA*RA + wB*RB; variance = wA^2 sA^2 + wB^2 sB^2 + 2 wA wB cov(A,B), cov = rho*sA*sB. (LM1 classes 5-7, garbled; formula text recognisable.)
2. Correlation limits: rho = +1 gives no risk reduction (risk is weighted average); rho = -1 can eliminate risk; "Diversification benefit = risk reduction; lower correlation, more benefit". Intuition given: "put not all eggs in one basket". (LM1 class 5, 6, 7; LM1 class 4 CW example: correlation -1 eliminates risk, otherwise only reduces it.)
3. MVP (minimum variance portfolio), GMVP, MEF (minimum-variance/efficient frontier), CAL, optimum risky portfolio = tangency portfolio with highest Sharpe ratio. (LM1 classes 4-7.)
4. Number of stocks: "the major benefit of diversification is exhausted when you construct a portfolio of N ~ 30 assets from different sectors/industries such that they have low correlation among themselves." (LM2 Class 7 CW.) Damodaran agrees: hold "the best thirty or forty stocks" rather than 1-5 (session16).
5. Risk decomposition: Total risk (variance) = systematic (beta^2 * sigma_m^2) + unsystematic (error-term variance). Only systematic risk is priced; unsystematic is diversifiable. Example: correlation with market 0.6 -> R^2 = 0.36, so 36% of variance systematic, 64% firm-specific. (LM2 Class 1 and 5.)
6. Efficient portfolios on the CML have correlation 1 with the market; individual stocks do not. (LM2 Class 1-2.)

### B. Beta / CAPM / SML (LM2; Damodaran s4)
- beta_i = cov(Ri,Rm)/var(Rm) = rho_im * sigma_i/sigma_m. Example: rho 0.7, sd stock 25, sd mkt 15 -> beta 1.167. (LM2 Class 2, 5.)
- Aggressive stocks beta>1, defensive beta<1; cyclical stocks high beta; utilities/pharma defensive. Beta rises with financial leverage (D/E) and business risk. (LM2 Class 2.)
- Systematic risk = beta^2 * var(m); unsystematic = var(i) - that. (LM2 Class 5/6.)
- Portfolio beta = weighted average of stock betas; with borrowing at Rf or short positions weights are relative to own funds (can exceed 100%). Example: A:B 3:2 on 1,00,000 own + 50,000 borrowed. (LM2 Class 10.)
- CAPM: E(R) = Rf + beta (Rm - Rf). Required return Re; intrinsic value Vo = PV of expected cash flows at Re; Alpha (Jensen) = E(R) - Re. alpha>0 (above SML, underpriced, buy/long), alpha<0 (overpriced, short), 0 fairly priced -> passive. (LM2 Class 2-3, 8.)
- Beta estimation: regress stock returns on market returns (characteristic line); slope = beta, intercept = Jensen alpha. Practical flexibility: how many years of data, frequency (annual/monthly/weekly/daily); true market portfolio does not exist, use proxy such as S&P 500 / Nifty. CAPM empirically weak at forecasting; limitations: single-factor, single-period. (LM2 Class 5, 9.)
- Beta pitfalls (Damodaran s4): beta measures market risk only, not total risk; a regression beta has high standard error; beta measures risk not investment quality.
- Multi-factor: Fama-French (market, SMB size, HML value), Carhart (+ momentum UMD). Caution: no strong theoretical basis; worked historically (small cap, value, momentum premia) with no guarantee. (LM2 Class 4, 9; Damodaran s4: factors incl. size, P/B, earnings momentum, price momentum, liquidity.)

### C. Active/alpha-based position sizing (LM2 Class 7-8)
- Core-satellite idea: benchmark proxy index (S&P500/Nifty) is the core; add selected mispriced stocks as satellites; avoid concentrated unsystematic risk. (LM2 Class 7; LM3 Q&A: "core-satellite = majority passive, rest active".)
- Compute alpha_i = E(R_i) - [Rf + beta_i (Rm-Rf)] for each candidate; keep alpha>0 longs; compute Information ratio IR_i = alpha_i / sigma(e_i) (residual/unsystematic risk); weights proportional to IR: w_i = IR_i / sum(IR). Higher IR gets higher weight (worked example 54%/46%).
- Method 1 for forecasting alpha: regress past stock excess returns on market excess returns; intercept = alpha (assumes the future resembles the past). Method 2: forecast return distribution if you expect structural change. Hardest practical problem = forecasting alpha.
- Realistic borrowing: borrow rate > lend rate so the CML kinks at the market portfolio. (LM2 Class 3.)

### D. Risk preference / utility (LM1 Part I classes 2-3)
- Utility U = E(R) - 0.5*A*sigma^2 (A = risk aversion coefficient; A>0 risk averse, A=0 risk neutral, A<0 risk seeking; examples A=2 vs A=5 choose different portfolios, "maximise utility"). Garbled but the structure is clear.
- Indifference curves for risk averse investors are upward sloping and concave; investor picks the portfolio on the CAL/MEF tangent to the highest curve. Mean-variance is not enough: returns show negative skew and fat tails (leptokurtosis); supplement with Value at Risk and tail loss measures. Liquidity and transaction costs matter (explicit: brokerage; implicit: bid-ask, impact cost, opportunity cost); emerging and lower-quality bond markets less liquid; liquidity rises with volume. (LM1 class 3.)
- Foreign asset (class 9, garbled): an Indian investor buying a US stock (example Tesla) faces currency (INR/USD) return and extra risk; return in domestic currency combines asset and FX returns.

### E. Performance measures (LM2 Class 9; Damodaran s8)
- Sharpe = (Rp - Rf)/sigma_p. Treynor = (Rp - Rf)/beta_p. M-squared = Rf + Sharpe*sigma_m - Rm (risk-matched to market). Jensen alpha = Rp - [Rf + beta_p (Rm-Rf)]. Information ratio = (Rp - R_index)/tracking error. Sharpe/Treynor are unit-free; M2 and alpha in %.
- Choose measure by context: diversified whole portfolio -> Sharpe (total risk); manager of one sleeve in a bigger diversified portfolio -> Treynor/alpha (systematic risk). Biases: Sharpe penalises sector-specific funds; IR biased against stocks outside index; Jensen/Treynor favour small-cap/low-PE/low-PBV tilts. (s8 table)
- Sortino: not in the notes.
- Strategy tests: include transaction costs, holdout periods, control for risk, beware data mining and survivor bias. (s8)

### F. Investment policy / planning process (LM3 Class 2, garbled; LM3 Q&A)
- Planning -> execution -> feedback (monitor, rebalance, evaluate vs benchmark). IPS contains objectives (return, risk: ability and willingness) and constraints (liquidity, time horizon, tax, legal/regulatory, unique circumstances). Strategic asset allocation first, then security selection; asset allocation sets the long-run framework; periodic monitoring and rebalancing; rebalance when allocation drifts from target. (Hand notes mention rebalancing and "liquidity", "time horizon", "tax" constraints; I could not recover numeric bands.)
- Risk budgeting = allocate permitted overall risk among strategic allocation, tactical allocation, security selection. (LM3 Q&A)
- Asset allocation importance (Damodaran s30): ~93.6% of variation in quarterly returns explained by stock/bond/cash mix (1986 study); ~40% of cross-fund return differences from allocation, 60% from security selection (Ibbotson). Investment process starts from client utility: risk tolerance, investment horizon, tax status.
- Active vs passive; smart beta; fees (asset mgmt notes): passive ~20% of AUM but ~6% of revenue; robo-advisers automate allocation, rebalancing, tax-loss harvesting, fee ~0.20% vs ~1%.

### G. Valuation / investor-view rules (Damodaran)
- Intrinsic value = PV of expected cash flows (FCFF/FCFE) at a risk-adjusted rate; value drivers: cash flows from existing assets, growth, quality of growth; price is driven by mood, momentum, liquidity, incremental information, group-think. "THE GAP: is there one? will it close? what will make it close?" (s5)
- Cost of equity = Rf + beta * ERP (s5); expected growth = retention ratio * ROE, or reinvestment rate * ROC; quality growth requires ROC > cost of capital; larger firms find it harder; stable growth rate must be below nominal growth of the economy; reinvestment rate = g / ROC; terminal value = EBIT(1-t)(1-RR)/(cost of capital - g). (s5)
- Implied required return from price: Price = DPS1/(r-g) -> r (e.g., $20 = 1/(r-.03) -> 8%). Gordon example in LM2: Re = 6+... , IV = D1/(Re-g) (e.g. 40/(0.135-0.04) = 421.05). (s4; LM2 Class 6)
- Relative valuation rules (s5): pick a multiple consistently (equity value / equity earnings; EV / operating metrics), choose comparables, control for differences in risk, growth and quality of growth; "play Moneyball": judge cheap/expensive from the cross-sectional distribution; make implicit assumptions explicit. Lowest-P/E quintile beat highest by 4.56% (illustrative portfolio study, s8).
- Value investing (s16): P/E, P/B, dividend-yield screens worked in the 20th century but "none have worked" in last 15 years; active value investors don't clearly beat a value index; accounting numbers less reliable (R&D); concentration is a false choice versus diversification (hold best 30-40 stocks).
- Market valuation (s33): value index by DCF (example: Rf 4.58% + ERP 4.5% = 9.08% cost of equity) or by regression of E/P on T-bond rate; PE regression for emerging markets on interest rate, GDP growth, country risk (PE = 16.16 - 7.94*rate + 154.4*GDPg - 0.1116*country risk). Beware structural shifts; longer horizon improves odds.
- Market timing (s30,31,34): evidence weak; newsletters underperform buy-and-hold (183 of 237); costs and taxes; indicators must be observable, leading, and strong enough to cover costs; if timing undercuts security selection, abandon it. Missing the 10 best days halves returns.
- Margin of safety, P/E vs own history, earnings growth thresholds: NOT stated as rules in the notes I read (Graham is only mentioned in s4/s16 on dividends and screens).

### H. Hedging / arbitrage (Damodaran s28-29; LM3 Q&A)
- Pairs trading: pick stocks with historically high correlation / minimum normalised squared deviation; top-20 pairs earned ~6% excess per 6 months but lost money in 1 of 6 periods and spreads can widen first; returns faded as imitation grew. Risk arbitrage (merger spread) = payoff like selling puts; excess ~9.25%/yr falls by ~2/3 after costs. Use leverage in proportion to riskiness; minimise market impact. Hedge funds: long/short; lower SD, higher fees (about 1/5 of excess returns). No option-hedging rules (protective put, collars) appear in the notes read.

## 3. Recommended model (computable checklist)

Inputs: holdings (symbol, qty, price, sector, currency), candidate symbol and its daily price history, a benchmark index series (Nifty 50 / S&P 500 for US names), Rf (India 10y G-sec, ASSUMED to be supplied), USDINR series for US stocks, optional option-chain (IV) for the candidate.
Use daily or weekly log/simple returns over 3 years where available (choice of window and frequency is a "flexibility" per the notes; ASSUMED 3y, weekly for beta, daily for correlation).

Step 0 - Data and liquidity sanity (LM1 class 3: liquidity matters)
- Candidate needs >= 250 trading days (ASSUMED). Average daily traded value >= INR 1 crore (ASSUMED). Fail -> "does not suit: illiquid/insufficient data".

Step 1 - Candidate beta and risk split (LM2)
- beta_c = cov(Rc,Rm)/var(Rm) (characteristic line slope), alpha_c = intercept, R2 = rho^2, systematic share = R2, unsystematic share = 1-R2, sigma_c.
- Flag if beta_c > 1.3 (ASSUMED) as aggressive; <0.8 as defensive (notes: >1 aggressive, <1 defensive).

Step 2 - Portfolio fit by correlation (LM1/LM2 diversification)
- Compute portfolio return series Rp (current weights, FX-adjusted to INR for US stocks - class 9 FX note).
- rho(c,p) = correlation of candidate with the existing portfolio; also average pairwise rho with each holding.
- Diversification benefit: sigma_new vs sigma_old using sigma^2 = w_c^2 s_c^2 + (1-w_c)^2 s_p^2 + 2 w_c(1-w_c) rho s_c s_p at proposed weight w_c (ASSUMED default 5%, or user-specified).
- Marginal risk: MCR_c = cov(Rc,Rp)/sigma_p; risk reduces if rho < sigma_p/sigma_c (Markowitz result; derived from the two-asset formula in the notes, not quoted).
- Rating inputs: rho(c,p) <= 0.5 good (ASSUMED), 0.5-0.75 partial (ASSUMED), > 0.75 poor (ASSUMED). Note rho = 1 gives no benefit, rho < 1 always gives some (notes).

Step 3 - Beta and CAPM check
- Portfolio beta_p = sum(w_i beta_i); new beta_p' with candidate at w_c. Compare with target beta band from user risk tolerance (ASSUMED: conservative <=0.9, moderate 0.9-1.1, aggressive >1.1). Flag if beta_p' moves outside the band.
- Candidate alpha: Jensen alpha = realised mean excess return - beta_c*(market excess). If user supplies a forecast E(R_c), compute SML alpha = E(R_c) - [Rf + beta_c (Rm-Rf)]; alpha > 0 supports adding, < 0 argues against (LM2 Class 3/8). Rm-Rf: use user input; ASSUMED 5-6% if absent.
- Information ratio IR = alpha / residual sd (annualised); use for relative sizing: weights proportional to IR across candidates (LM2 Class 7). Positive IR required for "suits" (ASSUMED).

Step 4 - Concentration and diversification count (notes: ~30 stocks)
- Number of holdings after adding: if < 30 then adding a low-correlation name is beneficial; if >= 30, benefit marginal (LM2 Class 7). Flag if already >= 40 (Damodaran: 30-40).
- Sector: count candidate sector weight after addition; limit ASSUMED 25% per sector (notes give no number); single-stock cap ASSUMED 10% (notes give none; consistent with ~30 stocks => ~3.3% equal weight, so ASSUMED default starting weight 3-5%).
- Asset-class: if candidate is US stock, include INR/USD FX risk (class 9). ASSUMED cap on foreign equity 20-25% of equity.
- Cash buffer: ASSUMED keep >= 5% cash after purchase (notes mention liquidity needs/constraints but no figure).

Step 5 - Investor constraints (IPS, LM3)
- Check against user-supplied IPS: return objective, risk tolerance (utility U = E(R) - 0.5*A*sigma^2; compute U before/after with user A, ASSUMED A=3 if unknown; accept if U improves), time horizon (valuation-based ideas need long horizon, per s33/s34), liquidity, tax, unique constraints.
- Tail risk: compute historical VaR(95%) and max drawdown of new portfolio vs old (notes: supplement mean-variance with VaR/tail measures); flag if VaR worsens by > 20% (ASSUMED).

Step 6 - Valuation overlay (Damodaran; optional, needs fundamentals)
- Required return Re = Rf + beta*ERP; implied return from price = DPS1/P + g; compare. Use relative valuation vs peers in same sector for P/E, EV/EBITDA, controlling for growth and risk (s5). Flag "expensive" if multiple above sector median by > 1 sd (ASSUMED) and growth below peers. Notes give no margin-of-safety % or P/E-history rule; do not present these as the notes' rules.
- Quality of growth: ROC > cost of capital (s5) where data exist.
- Sanity: do not rely on market-timing signals (s34); do not rely on value screens alone (s16).

Step 7 - Hedging (notes are thin)
- If option chain available: report implied vol of candidate vs its realised vol; suggest hedge only if candidate would exceed single-stock cap. No hedging rules in the notes; any put/collar logic is ASSUMED engineering, not from the notes. Pair-hedge idea (s29): hedge with a highly correlated name or index only as a risky approximation, not riskless.

Step 8 - Verdict
- SUITS: liquid, rho(c,p) <= 0.5, sigma_new <= sigma_old (risk not increased), beta_p' within band, sector/single caps respected, utility improves, alpha/IR not negative.
- PARTLY SUITS: passes liquidity but fails one or two (rho in 0.5-0.75, or beta band exceeded, or sector cap near limit, or IR <= 0): give a smaller suggested weight (scale w_c until constraints hold) and the reasons.
- DOES NOT SUIT: illiquid, rho > 0.75 with sigma_new > sigma_old, breaches caps, beta band exceeded materially, or utility worsens.
- Output per check: metric, value, threshold, source (notes vs ASSUMED), reason text.

## 4. Caveats
- Handwritten LM1/LM3 notes were not reliably recoverable; I relied on typed/readable parts. A manual look at the original PDFs may reveal more thresholds (e.g., IPS constraints, rebalancing).
- Unread files listed in section 1 might contain additional rules (esp. Damodaran sessions 9-15, 17-25 and CFA equity valuation Q&A).

## 4b. Additional sources (second pass)

Method note: Drive text extraction gives slide text without page numbers, so locations are given as "file, slide topic". Charts/tables drawn as images (e.g. low-PE vs high-PE return bars, PE history charts) did not come through as numbers; where a chart's number is missing I say so rather than guess. Handwritten class notes (LM1 class 8 notes, Equity LM8 class 1 and 10 notes) are unreadable OCR.

### Read this pass (Drive id in brackets)
Damodaran, folder "Valuation_Investment philosophy":
- session9 [1tT9XYqEdPUXdOijy6gZuw69kaEoHCtys] + session9soln [1UiJ80Jsbsr6bGYkQy_2wJH_hJSYsI3TS] (random walks, momentum)
- session10 [1ci6tomR7MFBs8mm9IdFgD2gq9hPEeXMS] + soln [1XrU0zkEhWlKh-legjIMF1AKnGqzJXzzd] (temporal patterns)
- session11 [1Eo3LCAW-sT1sftfRFWTYwNogMtLMfclq] + soln [1vnlW9gXfVnkSpNtV5WE1dpqB5-L8Bbf9] (technical rules)
- session12 [1YSqoHT42rSX_ohQ4GJjqrC6LOo_X-Jb9] + soln [1o-qfg7zjcD58ELRvgt-Mvf3Uaxb8CY8l] (value investing intro, Graham, Buffett)
- session13 [1jpO0OkLuqJGRmNQ3JFjkMeP7A8hmFf7U] + soln [1ZHuer8X7omgek8dUKeCiwVC6KKFS9GNf] (value screens)
- session17 [1x0hIjMJJnyhcDP6jl-V3gIegyivZpc_K] + soln [1iJAjG5CjKaz2SqireG0YsxgzBuef5L1y]; session16soln [1ImK0MTrLsKslGy7qI3JqmRx-XDzEl7Q4]
- session18 [18L7CglrNZZi-ME_Sn_Ih07fD--vKfNrw] (IPO), session23 [1YuvyWECoEwXeEVHo22fkyydSm8B1J9XE] (insiders), session24 [13HeFV0b4cI5AU1RiiemE6LdyPYrEtzIi] (analysts), session32 [185CNbLqdGCcbQOwjaGSA1OG3NGaTIXfH] (timing indicators II)
- Solutions only: session1soln, 2Nsoln, 3Nsoln, 4Nsoln, 5soln, 6soln, 7soln, 8soln, 15soln, 19soln, 20soln, 22soln, 30soln, 31soln, 32soln, 33soln, 34soln
CFA / PM:
- PM LM1 class 10 CW Q&A [1BpeVe5LLjmJ22HTUXafuUPvRB-iLqbTP]; PM LM1 class 8 CW Q&A [1oemFPnyUDXgA-aQj2r0OfsQvX2rS7eB5]; PM LM1 class 8 lecture notes [16ereyH7k8iPAPoG2DtR0fGoNmsK1X87-] (handwritten, only fragments: Sharpe/CAL/diversification, pairwise correlation, systematic vs diversifiable risk; nothing numeric usable)
- PM LM2 class 8 CW Q&A [1OpKeZ5_8hviISlQIdxcooAGvTDRVcaml]
- CFA PM LM3 class 2 CW Q&A [1KAXzHtxlpSUBZ9odHURXO8JXVcLDxSH1], class 3 [1Om3Eq3TO--woA34HG7-TT51_MuGu_dbk], class 4 [1HxNEqCAGWlP8MmNTdvPZcDbu-8pHFNkD], class 6 [14Uzd-mDKv0-SCD426yEZdP_XKTjSQzGh]
- CFA Equity LM8 (Equity Valuation: Concepts and Basic Tools) class 6 Q&A [1jpl_Po7X1UGxJA1Cf8H7lIlq8gQTv0Y0], class 7 [1JR1Qee1cfMvgg6ru2cdQ-2Gz0joBvzd_], class 8 [1B6hYWOw-zPwK_STzrrq4bvQ9tKOth9wP], class 9 [1iL7pxIpgskpfkqg8dq053k2UShMr5kOG], class 10 [1PUDAuoe0_BYZR3YBOJk-Lv3w1t-ajR0o]; class 1 handwritten notes [1oEa4LMPbsqDQMuDypCjlp67L-lrR-UiK] and class 10 notes [1btpN0RhVMDNWKD59A6smADrTnu4bhpRz] (garbled, nothing recovered)
- CFA Equity LM3 (Market Efficiency) class 6 Q&A [1-1UsK_PeEurEKy2qSFkdbhl5GIZEIPe5]

### Still NOT read (honest gaps)
- Damodaran: main decks for sessions 1-3, 6, 7, 14, 15, 19-22, 25, 27 do not appear in the folder listing (only their solution files were present for some); solution files for sessions 18, 24, 25, 26, 27, 28, 29 and session 12-13's extra material not read (topics: IPO, analysts, acquisitions, arbitrage - low relevance). narrative&numbers.pdf (9 MB) [1pVOza8l5fX6ENs6nJwjWEGi3l5Zrl6Sh] not read.
- Big books "FSA, Equity" [1FZYm2TnsjenX7DquR_Rh_fAHwEpu92-t] and "Quants, Eco, CI" [1nHxCrYmYwBCXLIJOvFSD3m38Zrh_9tsE]: not read. Their chapters on equity valuation are instead covered through the Equity LM8 Q&A above.
- Equity LM8 Q&A classes 1-5, Equity LM2/LM3 other Q&As, Equity LM1/LM2 combined notes, EI LM6 industry analysis, all FSA LM3-LM10 files, PM LM1 Q&A classes 2/3 and HW files, PM LM3 class 5 part 1/2 lecture notes: not read this pass. FSA/ratio material is accounting analysis, not portfolio rules.

### Per-file findings

**session12.pdf (Damodaran, value investing intro), Graham screens slide - the only explicit numeric value-investing screens in the Drive.** Ben Graham's ten screens:
1. PE < 1 / (AAA corporate bond yield)
2. PE < 40% of the average PE of the last 5 years
3. Dividend yield > two-thirds of the AAA bond yield
4. Price < two-thirds of book value
5. Price < two-thirds of net current assets
6. Debt/equity (book) < 1
7. Current assets > 2x current liabilities
8. Debt < 2x net current assets
9. EPS growth over last 10 years > 7%
10. No more than 2 years of negative earnings in the previous 10.
Evidence on the slide: Oppenheimer study found stocks passing Graham screens earned well above the market; Hulbert found newsletters using similar screens did better; James Rea's actual mutual fund run on the screens failed to deliver. Buffett followers/students did not adhere to the screens strictly. Buffett tenets: understandable business, consistent history, high ROE, high and stable margins, "owner earnings = net income + D&A - capex", conservative earnings, riskless rate as discount rate. Impediments today: imitators, scale, data now flat to everyone; "index fund investors have outperformed the Omaha value investing contingent over the last two decades" (slide text, session12). Passive screening is explicitly the "lazy" definition of a value investor.
**session12soln.pdf:** value investor = values assets in place and buys at a bargain; growth is a "bonus", not the reason for the investment.

**session13.pdf (value screeners), key numeric/structural rules:**
- Margin of safety defined: "a MOS of 20% would imply that an investor would buy a stock only if its price is more than 20% below the estimated value (estimated using a multiple or DCF)". Only number given; it is an example, not a recommended level.
- P/B justified by P/B = (ROE - g)/(ROE - cost of equity): low P/B firms are expected to earn low ROE; high P/B is not necessarily overvalued. Low-PE explanations: high-risk earnings, tax cost of dividends, low growth.
- EV/EBITDA = (equity market value + debt - cash)/EBITDA; fewer negatives than PE but EBITDA is not free cash flow.
- A 4-part screen design: cheap (PE/PBV/EV-EBITDA), low risk (beta, SD, debt ratio), some growth (minimum growth), quality growth (ROC > cost of capital). Variants: normalised earnings, adjusted earnings, owner earnings; moat.
- Practical rules (last slide): long horizon (low P/B has underperformed high P/B over shorter periods); too many screens remove the stocks that create the excess return; diversify because excess returns come from a few holdings in a large portfolio; watch tax and transaction costs; value trap risk when industry is being disrupted.
- Dogs of the Dow / Dividend aristocrats mentioned; no yield numbers survive extraction.
**session13soln.pdf:** want low price with high ROC and stable earnings; if a screen of ~25 stocks is dominated by one sector, that sector may be undervalued OR share an unscreened risk or be in decline (so check sector concentration of screen results).

**session16soln.pdf:** to judge active value investing compare it with a value index fund, not the whole market; Barber and Odean: average active individual investor lags the market and more trading hurts; activist investors beat the market on average only because of the biggest winners (median does not); a stock dividend is the only listed event that does not change intrinsic value.

**session17.pdf + soln (growth / small cap):** small-cap premium disappears for sub-periods as long as five years; premium weakened over the last 40 years "perhaps even disappeared"; mostly a 1970s effect (Siegel); higher transaction costs; need larger, more diversified portfolio for small caps because they cluster in few sectors; replicable via index fund so not an active edge. Soln: it is false that small caps always beat large over any 5-year horizon (1925-2000).
**session19soln.pdf (growth/GARP):** PE < growth GARP screen produces too many "cheap" stocks when interest rates are high; PEG favours high-risk, low-ROE growth stocks unless extra screens added; value of growth is highest when growth is high AND return on capital > cost of capital (e.g. 20% growth at 15% ROC beats 20% growth at 10% ROC when cost is 10%); historical earnings growth is a poor predictor; high-PE stocks have delivered lower returns than low-PE, so betting on them needs timing skill.
**session5soln.pdf:** PE 10 vs sector median 15 is "cheap" only if the stock is also no riskier and has no less growth; growth adds value only if ROC > cost of capital; cost of capital uses market-value weights and current borrowing rate.

**session9.pdf + soln (momentum):** Jegadeesh-Titman: stocks that rose over the previous 6-12 months tended to keep rising; 1945-2010 top decile minus bottom decile of prior-year returns = 16.5% a year; momentum stronger with high volume, stronger for high growth/high P/B stocks; over multi-year (3-5 year) horizons reversal dominates; momentum plus reversal = bubble mechanics. Short-term (day/week) correlation exists but small and not exploitable after costs. Effects work better in smaller, less liquid stocks. Soln: excess return must exceed trading costs (price impact, bid-ask, brokerage).
**session10.pdf + soln:** January effect (strongest for smallest-cap decile), Monday/weekend effect (Friday close to Monday open), mid-day swoon: "little evidence that investors have been able to exploit these effects"; Friday has recently been the worst day. No usable numeric returns survived (charts).
**session11.pdf + soln:** technical rules (relative strength, support/resistance, moving averages, volume) rest on investor irrationality or slow learning; evidence is "mild"; rules for use: need a behavioural basis, back-test (check volatility of performance and holding-period sensitivity), timely trading, control trading cost; contrarian sentiment indicators e.g. advisory bearish ratio threshold "eg 60%" before contrarian buys; intrinsic-value investors can use technicals for timing entries.
**session23.pdf (insiders):** insider buying is a noisy signal (about 4 in 10 stocks with insider buying turn out poor); Lakonishok-Lee: firms with insider buying earned 22.2% over next 12 months vs 14.4% for firms with heavy insider selling; effect concentrated in small firms, almost none in large; price effect of legal insider trading has "almost disappeared since 2002"; only large trades by top executives carry information.
**session24.pdf (analysts):** analysts beat time-series models only for 1-2 quarters ahead; no edge at 3-5 year forecasts; portfolio of the 20 largest upward earnings revisions earned 14% a year vs 7% index (Hawkins, 1983) and Givoly-Lakonishok 4.7% over four months; strategy is short-term, small excess returns and dependent on the weakest links (company earnings and analyst bias); advantage of analysts has shrunk.
**session18.pdf (IPO):** average initial IPO return 15.8% (13,308 IPOs) but you do not get the full allotment of good ones; offers revised up: 30.22% average initial return (642 IPOs) vs revised down 3.54% (708 IPOs). Relevant only as a reason NOT to chase new listings: about 15% of IPOs are overpriced and you get the full allotment of those.
**session32.pdf + soln (timing indicators II):** T-bill rate change vs next-year stock return: drop >1% -> 9.14% avg, 68.75% up-years (16 yrs); drop 0-1% -> 18.40%, 85.19% (27 yrs); rise 0-1% -> 9.84%, 71.43% (35 yrs); rise >1% -> 6.25%, 61.11% (18 yrs). Predictive power came from 1950-1975, "almost no predictive power since 1975". Level of T-bond rate alone gives no indication of stock returns. Earnings yield minus T-bond rate: when E/P - T-bond > 2% (21 years) average next-year return 13.85%; 1-2% (12 yrs) 0.08% with SD 20.30%; 0-1% (4 yrs) 18.62%; -1-0% (7 yrs) 13.33%; -2--1% (16 yrs) 7.74%; < -2% (5 yrs) 3.04%. Not monotonic, so a weak signal. GDP growth bands show no clean relation to next-year returns (worst class 0-2% growth: -13.98%; all years 10.92%). Conclusion on slide: links between macro variables and stocks are weak, forecasting the macro variable adds a second error, mean reversion fails under structural change.
**session32soln.pdf:** worked example - normal market PE 16, index 1800, earnings 100 growing 10%, reversion to PE 16 gives expected index 1760 (i.e. below today). E/P above T-bond rate = bullish.
**session33soln.pdf (market valuation):** DDM index example: dividends 90, growth 3%, required return 7.5% -> value 2000 vs index 1800 = 10% undervalued. E/P regression example E/P = 0.02 + 0.75 x T-bond rate; at 4% T-bond, E/P = 5%, PE 20 (illustrative regression, not a rule). Higher PE can be justified by lower real rates; higher inflation, lower growth, higher uncertainty all depress PE.
**session30soln.pdf:** Shilling: avoiding the 50 worst months would lift annual return from 11% to over 19%; Sharpe (1975): a timer must be right about 70% of the time to pay off; tactical asset allocation funds underperform both the market and fixed-mix portfolios; ~40% of fund return differences from allocation, 60% from security selection (recent studies) vs the older >90% claim.
**session31soln.pdf:** volatility rises -> stocks fall that period, positive returns in the next period; a timing indicator must lead, not lag; January-barometer is not usable because January is only known after the fact; returns are higher on average after a down year than after an up year but with no economic basis.
**session34soln.pdf:** newsletters collectively lower returns than buy-and-hold; professional timers' calls are short term and too frequent (hundreds of trades a year).
**session8soln.pdf (performance tests):** Sharpe example (12% return, 30% SD) 0.4 vs market (10%, 20%) 0.5 - higher return but worse risk-adjusted; risk-and-cost-adjusted alpha example: 11% gross - 1% costs = 10% vs CAPM 3% + 1.2 x (9%-3%) = 10.2%, alpha -0.2%; test strategies on a sample available at the start of the test (survivor/look-ahead bias).
**session6soln.pdf (costs):** bid-ask spread is larger for small, low-priced, little-followed stocks; a 4% round-trip spread with a 2-year hold needs about 12.22% gross a year to deliver 10% net; price impact largest for big money in small caps; index funds with long holds minimise tax drag.
**session7soln.pdf:** inefficiencies persist where costs are high and few people look; easy-to-copy edges decay.
**session15soln.pdf, 20soln, 22soln, 1-4Nsoln:** activist, VC, news-drift and basic risk material; no numeric portfolio rules. Useful: philosophy must be tied to risk aversion, time horizon, tax status (session1soln); beta captures only the diversified investor's risk and a risky company can have low beta (session4Nsoln); bond duration/price examples (session3Nsoln) irrelevant to equity model.

**PM LM1 class 8 Q&A [1oemFPnyUDXgA-aQj2r0OfsQvX2rS7eB5]:** equal-weighted portfolio variance depends on individual variances and covariances, not on returns; as the number of assets rises each asset's own variance contributes less and "the average covariance between all pairs of assets contributes the most" to volatility - so beyond ~30 names the dominant driver is average pairwise correlation, which supports measuring candidate-to-portfolio correlation rather than adding names (Q2-3). The global minimum-variance portfolio is the lowest-SD point on the frontier; CAL from the optimal risky portfolio dominates the frontier because of borrowing at the risk-free rate (Q4-7).
**PM LM1 class 10 Q&A [1BpeVe5LLjmJ22HTUXafuUPvRB-iLqbTP]:** worked correlation numbers: cov = rho x sd1 x sd2 (weights irrelevant); two-asset example weights 25/75, SD 17.9%/6.2%, rho 0.5 -> portfolio SD about 7.90% (vs 9.13% weighted average) (Q5); weights 40/60, SD 15%/18%, rho 0.20 -> 13.4% (Q9); lower correlation always lowers risk with equal weights (Q6, Q11); of US vs Europe 0.74, Japan 0.67, India 0.61 correlations, the lowest correlation (India 0.61) cuts risk most (Q17); higher risk aversion A gives lower utility for the same portfolio (Q10). Diversification ratio = portfolio SD / average SD of holdings (PM LM3 class 3 Q23) - a usable metric.
**PM LM2 class 8 Q&A:** CAPM numeric examples (3% + 1.5 x 6% = 12%); alpha = intercept of the characteristic line; undervalued if estimated return > CAPM return; "only systematic risk is priced"; use M2 (total risk) for a not fully diversified investor, Jensen alpha/Treynor for a diversified one; Sharpe example (Manager 3: (13.10-2.60)/8.23 = 1.28 beats Manager 1 1.12 and 2 1.05).
**PM LM3 classes 2, 3, 4, 6 Q&A:** IPS components: description, purpose, duties, update procedure, objectives, constraints, guidelines, benchmark; review IPS at regular intervals or on major change in objectives/constraints, NOT based on recent performance; tax is a constraint, not risk tolerance; greater spending needs allow LOWER risk; rebalancing is in the feedback step "on an as-needed basis, reviewed on a regular schedule" - no numeric band; top-down: economy, then industry, then company; evaluate each holding by its contribution to portfolio risk and return (Markowitz view); smart beta = rules-based factor tilt, fees/turnover between passive and active; robo advisers about 0.20% fee vs 1%; passive growing because alpha is harder in efficient markets.
**Equity LM8 Q&A classes 6-10 (valuation tools), formulas and numbers:**
- Gordon: V0 = D1/(k-g); k > g required; only for mature, stable payers (class 6 Q3, Q15-16). Multistage DDM for growth/"natural growth" firms (class 9 Q15). Examples: D1 2.00, k 12%, g 5% -> 28.57 (class 6 Q4); required return implied by price: D1/P + g, 1.00 x 1.05/20 + 5% = 10.25% (class 6 Q6); g = retention x ROE, e.g. ROE 15% x 40% = 6%; DuPont ROE = margin x turnover x equity multiplier (class 6 Q7-11).
- CAPM feeds k: example k = 4.2% + 1.5 x 5.6% = 12.6% (not WACC) -> price 1.2612/(0.126-0.051) = 16.82 (class 10 Q13).
- Justified P/E = payout/(k-g) (leading); payout 40%, k 12%, g 7% -> 8; payout up from 30% to 40% with ROE 12%, k 12.4% gives 7.7x (class 9 Q16, class 10 Q17). Higher k lowers P/E; g falling to zero lowers P/E (class 8 Q7-8).
- Multiples: P/S works for distressed firms but misses cost control; P/E meaningless if earnings negative; P/BV best for firms with liquid/financial assets and consistent accounting, not for service firms with few fixed assets; P/CF for loss makers with different accounting; EV/EBITDA for firms with different capital structure; asset-based valuation not for firms with big intangibles (class 8 Q1-6, class 9 Q3-6, class 10 Q20-22).
- Peer comparison with law of one price: company with highest P/E and P/CF in peer set looks overvalued; mixed signals across multiples (class 10 Q15-16).
- Valuation decision rule: undervalued/overvalued only if market price lies outside the confidence interval of the value estimate (class 10 Q1: value 98 +/- 2 x 0.55 -> price 97.50 is "fairly valued"). Gives a form of margin: act only outside +/- 2 SD of the estimate.
**Equity LM3 class 6 Q&A (market efficiency):** value effect (low P/E, low P/B, high yield outperformed over the long run); overreaction (losers beat the market later); January, weekend effects; "majority of evidence is that anomalies are due to research methodology and not exploitable after transaction costs"; if semi-strong efficient, passive management is appropriate; low-P/E abnormal returns would be evidence against semi-strong efficiency; behavioural biases: overconfidence, loss aversion, herding/information cascades.

### Numeric rules table (new, with source)
| Rule | Value | Source |
|---|---|---|
| Graham PE cap | PE < 1/AAA yield (e.g. AAA 7% -> PE < 14.3) and PE < 40% of 5-yr average PE | session12.pdf Graham screens slide |
| Graham yield/asset screens | Div yield > 2/3 AAA yield; P < 2/3 book; P < 2/3 net current assets | session12.pdf |
| Graham balance sheet | D/E < 1; current ratio > 2; debt < 2x NCA | session12.pdf |
| Graham earnings quality | 10-yr EPS growth > 7%; max 2 loss years in 10 | session12.pdf |
| Margin of safety | example 20% below estimated value | session13.pdf last slides |
| Decision band | value +/- 2 SD of estimate | Equity LM8 class 10 Q1 |
| Diversification | hold best 30-40 stocks (earlier); average covariance dominates large equal-weight portfolios | s16 (earlier), LM1 class 8 Q&A |
| Momentum | 6-12 month winners continue; top minus bottom decile 16.5% a year (1945-2010); 3-5 year reversal | session9.pdf |
| Earnings revisions | top 20 upgrades 14% vs 7% index; effect lasts weeks to months | session24.pdf |
| Insider buying | 22.2% vs 14.4% for heavy selling next 12 months; about 4 in 10 buys still fail; small caps only | session23.pdf |
| Timing | right ~70% of the time to pay off; missing best days costly; macro/rate signals weak | session30soln, session32.pdf |
| T-bill signal | weak, only 1950-1975 | session32.pdf |
| E/P minus T-bond > 2% | avg next-year return 13.85% (21 yrs) vs < -2%: 3.04% (5 yrs) | session32.pdf |
| Round-trip costs | 4% spread needs about 2.2% extra gross per year over a 2-yr hold | session6soln |
| Cash, sector cap, single-stock cap, rebalancing band | NOT found in any additional file | - |

## 5. Changes to the recommended model

1. Valuation overlay (Step 6): add a "Graham-style screen" panel with the ten Graham tests above as pass/fail flags (data: PE, 5-yr average PE, AAA/Indian corporate bond yield as supplied by user, dividend yield, P/B, net current assets, D/E, current ratio, 10-yr EPS CAGR, loss years). Show a count (e.g. 7 of 10) but do NOT make it a hard gate: Damodaran says screens worked in the 20th century and have faltered for ~15 years (s16, s13), and Rea's fund failed (s12). Mark the Indian AAA yield input as user-supplied (ASSUMED source).
2. Replace the earlier ASSUMED "expensive if multiple above sector median by > 1 sd" with: (a) compare to sector peers only after controlling for growth and risk (s5soln: cheap only if low PE AND not riskier AND not lower growth), and (b) require the price to lie outside the intrinsic value estimate +/- 2 SD before calling over/under-valued (Equity LM8 class 10 Q1). Keep the 20% margin-of-safety value as a configurable default of 20%, labelled "example from s13, not a recommended level" (ASSUMED as default).
3. Add intrinsic-value helpers: Gordon/multistage DDM and justified P/E = payout/(k-g), with k from CAPM (not WACC), g = retention x ROE, and a guard that k > g. Flag P/E-based comparisons invalid when earnings are negative; offer P/S or P/CF or EV/EBITDA fallback by case (Equity LM8 classes 6-10).
4. Quality-of-growth flag: require ROC > cost of capital (s19soln, s5soln); PEG/GARP screen must be combined with ROE and risk screens (s19soln).
5. Diversification step: keep the "30-40 names" guidance but make the primary metric the candidate's correlation with the existing portfolio plus the diversification ratio (portfolio SD / average holding SD) (PM LM3 class 3 Q23, LM1 class 8 Q&A). Use the two-asset formula checks with rho thresholds as before (still ASSUMED).
6. Screen-concentration warning: if a batch of candidate stocks that pass is dominated by one sector, warn about shared unscreened risk (s13soln). Apply to any candidate list the model produces.
7. Timing and momentum: do not gate on market-timing or macro signals (s30soln, s32, s34soln). Optionally display (informational, not scored) the candidate's 6-12 month price momentum and volume trend, labelled with the s9 evidence and its decay at long horizons; show 3-5 year loser status as a reversal/value-trap caution, not a buy signal (s9soln Q5, s13).
8. Costs: add an estimated round-trip cost input (spread plus brokerage plus taxes) and require expected gross return/alpha to exceed it; for small illiquid stocks use the bid-ask effect (s6soln, s9soln Q3). Reinforce the earlier INR 1 crore daily value liquidity floor (still ASSUMED).
9. Small-cap handling: do not assume a size premium; treat small-cap candidates as needing larger diversified exposure and higher costs (s17, s17soln). Keep any size tilt optional.
10. Information-based extras (optional, low weight): insider buying by top executives in small firms and upward earnings revisions are weak, short-lived signals (s23, s24); show as context only.
11. IPS / rebalancing: no numeric rebalancing band exists in the Drive; keep the band ASSUMED (e.g. 5 percentage points absolute or 20% relative drift - ASSUMED, not from notes), review on a calendar schedule and after changes in objectives/constraints, not after performance (LM3 class 2 Q&A). Greater spending needs lower risk capacity (LM3 class 3 Q17); IPS needs objective, constraints, benchmark.
12. Performance/tests: add Sharpe, Treynor, Jensen alpha, M2 with the rule "Sharpe/M2 for a non-diversified investor, Treynor/alpha when the candidate is one sleeve of a diversified portfolio" (LM2 class 8 Q&A; s8soln) and require strategy tests to be net of costs and free of survivorship bias.
13. Still ASSUMED (unchanged because no new source): sector cap 25%, single-stock cap 10%, cash buffer 5%, foreign equity cap 20-25%, beta bands, correlation thresholds 0.5/0.75, VaR worsening threshold of 20%, A=3.
