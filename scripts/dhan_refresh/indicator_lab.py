"""Indicator lab: back-test a broad set of technical indicators on the same Dhan daily history the desk uses,
and keep only the ones that survive an honest out-of-sample test.

Pre-registered rules (written before the results were seen, 26 Nov 2026; do not loosen them after a bad run):
  * Event: the first day a condition becomes true (not every day it stays true). Cross-sectional factors
    (momentum, low volatility, short-term reversal, 52-week-high proximity) are formed every 21 trading days.
  * Outcome: the stock's return over the next 21 trading days, bought at the signal day's close:
      - abnormal = stock return minus the equal-weighted average of all stocks over the same 21 days
        (the "average stock" baseline, so a rising market or the universe's small-cap tilt does not count as skill)
      - net vs Nifty = stock return minus the Nifty 50's return minus 0.25% round-trip delivery charges
        (STT 0.1% each side, stamp, exchange, GST; config/trading.json)
  * Split: in-sample = everything before the last 3 years; out-of-sample = the last 3 years.
  * Statistics are clustered by calendar month: cases on the same days move together, so counting each stock as an
    independent case would overstate the evidence by 10x or more. t = mean of monthly averages / standard error.
  * KEEP (buy-side) only if: in-sample abnormal > 0 with t >= 2, out-of-sample abnormal > 0 with a one-sided p-value
    that survives Holm's correction across EVERY indicator tested (the many-ideas test), out-of-sample net vs Nifty
    > 0 after charges, and at least 100 out-of-sample cases in 12 or more months.
  * AVOID (warning) is the mirror image: significantly worse than the average stock in both periods.
  * Everything else is DROPPED. Survivorship bias: the universe is today's Nifty 500, which flatters every
    indicator; the abnormal-return baseline uses the same universe, which cancels part of it.
Research software, not advice.
"""
from __future__ import annotations

import datetime as dt
import math

import numpy as np

H = 21                      # holding period, trading days (the desk's trade plans hold up to 21 sessions)
COST = 0.0025               # round-trip delivery charges as a fraction
OOS_YEARS = 3.0
ALPHA = 0.05

NAMES = {
    # trend and moving averages
    "golden_cross": "50-day average crosses above the 200-day average (golden cross)",
    "death_cross": "50-day average crosses below the 200-day average (death cross)",
    "ema9_21": "9-day EMA crosses above the 21-day EMA",
    "ema20_50": "20-day EMA crosses above the 50-day EMA",
    "x_sma20": "Close crosses above the 20-day average",
    "x_sma50": "Close crosses above the 50-day average",
    "x_sma200": "Close crosses above the 200-day average",
    "xd_sma200": "Close crosses below the 200-day average",
    "align": "20 > 50 > 200-day averages all lined up, first day",
    "above200_rising": "Close above a rising 200-day average, first day",
    "ext200": "Close 40%+ above the 200-day average (overextended)",
    "below50_15": "Close 15%+ below the 50-day average (stretched down)",
    # momentum
    "roc20_up": "20-day rate of change turns positive",
    "roc10_10": "Up 10%+ in 10 days",
    "macd_up": "MACD(12,26,9) crosses above its signal line",
    "macd_up_neg": "MACD crosses above its signal line below zero",
    "macd_dn": "MACD crosses below its signal line",
    "macd_zero": "MACD crosses above zero",
    "trix_up": "TRIX(15) turns positive",
    # oscillators
    "rsi14_x30": "RSI(14) crosses back above 30",
    "rsi14_x50": "RSI(14) crosses above 50",
    "rsi14_x70": "RSI(14) crosses above 70 (momentum)",
    "rsi14_dn70": "RSI(14) falls back below 70",
    "rsi2_5": "RSI(2) under 5",
    "rsi2_10_up": "RSI(2) under 10 while above the 200-day average",
    "stoch_up20": "Stochastic(14,3) %K crosses above %D below 20",
    "stoch_dn80": "Stochastic(14,3) %K crosses below %D above 80",
    "willr_x80": "Williams %R(14) crosses back above -80",
    "cci_xm100": "CCI(20) crosses back above -100",
    "cci_x100": "CCI(20) crosses above +100",
    "mfi_20": "Money Flow Index(14) under 20",
    "mfi_x80": "Money Flow Index(14) crosses above 80",
    # volatility and bands
    "bb_below": "Close below the lower Bollinger band (20, 2)",
    "bb_reenter": "Close back inside the lower Bollinger band",
    "bb_above": "Close above the upper Bollinger band (20, 2)",
    "bb_squeeze_up": "Bollinger width in its lowest 20% of 6 months, then close above the upper band",
    "kelt_up": "Close above the upper Keltner channel (EMA 20 + 2 ATR)",
    "atr_contract": "ATR(14) under 60% of ATR(100), above the 50-day average",
    "nr7": "Narrowest range in 7 days",
    "nr4_inside": "Narrowest range in 4 days and an inside bar",
    # breakouts
    "don20": "Close above the prior 20-day high",
    "don55": "Close above the prior 55-day high",
    "don100": "Close above the prior 100-day high",
    "hi52": "New 52-week closing high",
    "hi52_vol": "New 52-week closing high on 1.5x average volume",
    "near_hi52": "Within 3% of the 52-week high, first day",
    "lo52": "New 52-week closing low",
    # volume
    "vol2_up": "Up day on 2x the 50-day average volume",
    "vol3_dn": "Down day on 3x the 50-day average volume",
    "obv_div": "OBV at a 50-day high while price is not",
    "obv_x20": "OBV crosses above its 20-day EMA",
    "cmf_x10": "Chaikin Money Flow(20) crosses above +0.10",
    "accum": "Up-day volume 1.5x down-day volume over 50 days, above the 50-day average",
    # trend strength
    "adx_x20": "ADX(14) crosses above 20 with +DI above -DI",
    "di_cross": "+DI crosses above -DI with ADX above 25",
    "aroon_up": "Aroon up crosses above 70 with Aroon down under 30",
    "supertrend_up": "Supertrend(10, 3) turns up",
    "psar_up": "Parabolic SAR flips below price",
    "ichi_cloud": "Close above the Ichimoku cloud, first day",
    "tk_cross": "Ichimoku Tenkan crosses above Kijun",
    # candles and short-term patterns
    "engulf": "Bullish engulfing candle after a down day",
    "hammer": "Hammer after a 5-day decline",
    "gap_up3": "Gap up 3%+ that holds into the close",
    "gap_dn3": "Gap down 3%+",
    "dip3": "Three down closes in a row above the 200-day average",
    "drop5d_10": "Down 10%+ in 5 days",
    "ibs_low": "Closes in the bottom 20% of the day's range above the 200-day average",
    "flag": "Up 10%+ over 10 days, then 5 days inside a 5% range",
    # relative strength vs the Nifty
    "rs_hi": "Relative strength line vs Nifty at a 1-year high",
    "rs_x50": "Relative strength line crosses above its 50-day average",
    "rs3m_10": "Beats the Nifty by 10%+ over 3 months, first day",
    # cross-sectional factors, formed every 21 trading days
    "xs_mom12": "Factor: top 10% by 12-month return skipping the last month (momentum)",
    "xs_mom6": "Factor: top 10% by 6-month return skipping the last month",
    "xs_mom12_low": "Factor: bottom 10% by 12-1 month return (losers)",
    "xs_rev1": "Factor: bottom 10% by last month's return (short-term reversal)",
    "xs_lowvol": "Factor: lowest 10% 60-day volatility",
    "xs_highvol": "Factor: highest 10% 60-day volatility",
    "xs_hi52": "Factor: top 10% by closeness to the 52-week high",
}
XS = [k for k in NAMES if k.startswith("xs_")]


# ---------- numpy helpers (all causal: value at i uses data up to i) ----------
def sma(a, n):
    """Simple moving average; leading NaNs (from an earlier indicator's warm-up) are skipped."""
    out = np.full(len(a), np.nan)
    ok = np.where(~np.isnan(a))[0]
    if not len(ok):
        return out
    s = ok[0]
    b = a[s:]
    if len(b) >= n:
        cs = np.cumsum(np.insert(b, 0, 0.0))
        out[s + n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


def ema(a, n):
    out = np.full(len(a), np.nan)
    k, e = 2 / (n + 1), np.nan
    for i, x in enumerate(a):
        if np.isnan(x):
            continue
        e = x if np.isnan(e) else x * k + e * (1 - k)
        out[i] = e
    out[:n - 1] = np.nan
    return out


def wilder(a, n):
    out, s = np.full(len(a), np.nan), np.nan
    for i in range(len(a)):
        if i == n - 1:
            s = np.nanmean(a[:n])
        elif i >= n:
            s = (s * (n - 1) + a[i]) / n
        if i >= n - 1:
            out[i] = s
    return out


def rmax(a, n):
    out = np.full(len(a), np.nan)
    if len(a) >= n:
        out[n - 1:] = np.lib.stride_tricks.sliding_window_view(a, n).max(axis=1)
    return out


def rmin(a, n):
    out = np.full(len(a), np.nan)
    if len(a) >= n:
        out[n - 1:] = np.lib.stride_tricks.sliding_window_view(a, n).min(axis=1)
    return out


def rstd(a, n):
    out = np.full(len(a), np.nan)
    if len(a) >= n:
        out[n - 1:] = np.lib.stride_tricks.sliding_window_view(a, n).std(axis=1)
    return out


def rsum(a, n):
    out = np.full(len(a), np.nan)
    if len(a) >= n:
        cs = np.cumsum(np.insert(a, 0, 0.0))
        out[n - 1:] = cs[n:] - cs[:-n]
    return out


def lag(a, k=1):
    out = np.full(len(a), np.nan)
    out[k:] = a[:-k]
    return out


def rsi(c, n):
    d = np.diff(c, prepend=np.nan)
    g, l_ = np.where(d > 0, d, 0.0), np.where(d < 0, -d, 0.0)
    g[0] = l_[0] = 0.0
    ag, al = wilder(g, n), wilder(l_, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(al == 0, 100.0, 100 - 100 / (1 + ag / al))


def cross_up(a, b):
    return (a > b) & (lag(a) <= lag(b))


def first(cond):
    cond = np.nan_to_num(cond.astype(float)).astype(bool)
    return cond & ~np.concatenate([[False], cond[:-1]])


def supertrend(h, l, c, n=10, m=3.0):
    tr = np.maximum(h - l, np.maximum(abs(h - lag(c)), abs(l - lag(c))))
    tr[0] = h[0] - l[0]
    a = wilder(tr, n)
    mid = (h + l) / 2
    ub, lb = mid + m * a, mid - m * a
    d = np.zeros(len(c))
    fu, fl = ub.copy(), lb.copy()
    for i in range(1, len(c)):
        if np.isnan(a[i]):
            continue
        fu[i] = ub[i] if (np.isnan(fu[i - 1]) or ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (np.isnan(fl[i - 1]) or lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        prev = d[i - 1] or 1
        d[i] = 1 if c[i] > fu[i - 1] else -1 if c[i] < fl[i - 1] else prev
    return d


def psar_dir(h, l, step=0.02, mx=0.2):
    n = len(h)
    d = np.zeros(n)
    if n < 3:
        return d
    up, af, ep, sar = True, step, h[0], l[0]
    for i in range(1, n):
        sar = sar + af * (ep - sar)
        if up:
            sar = min(sar, l[i - 1], l[i - 2] if i > 1 else l[i - 1])
            if l[i] < sar:
                up, sar, ep, af = False, ep, l[i], step
            elif h[i] > ep:
                ep, af = h[i], min(mx, af + step)
        else:
            sar = max(sar, h[i - 1], h[i - 2] if i > 1 else h[i - 1])
            if h[i] > sar:
                up, sar, ep, af = True, ep, h[i], step
            elif l[i] < ep:
                ep, af = l[i], min(mx, af + step)
        d[i] = 1 if up else -1
    return d


def events(o, h, l, c, v, nc) -> dict:
    """{name: bool array} of first-day events for one stock (time-series indicators only)."""
    E = {}
    with np.errstate(invalid="ignore", divide="ignore"):
        m20, m50, m200 = sma(c, 20), sma(c, 50), sma(c, 200)
        e9, e12, e20, e21, e26, e50 = (ema(c, n) for n in (9, 12, 20, 21, 26, 50))
        tr = np.maximum(h - l, np.maximum(abs(h - lag(c)), abs(l - lag(c))))
        tr[0] = h[0] - l[0]
        atr14, atr100 = wilder(tr, 14), wilder(tr, 100)
        r200 = m200 > lag(m200, 21)
        E["golden_cross"] = cross_up(m50, m200)
        E["death_cross"] = cross_up(m200, m50)
        E["ema9_21"] = cross_up(e9, e21)
        E["ema20_50"] = cross_up(e20, e50)
        E["x_sma20"] = cross_up(c, m20)
        E["x_sma50"] = cross_up(c, m50)
        E["x_sma200"] = cross_up(c, m200)
        E["xd_sma200"] = cross_up(m200, c)
        E["align"] = first((m20 > m50) & (m50 > m200))
        E["above200_rising"] = first((c > m200) & r200)
        E["ext200"] = first(c > 1.4 * m200)
        E["below50_15"] = first(c < 0.85 * m50)
        roc20 = c / lag(c, 20) - 1
        E["roc20_up"] = cross_up(roc20, np.zeros(len(c)))
        E["roc10_10"] = first(c / lag(c, 10) - 1 >= 0.10)
        macd = e12 - e26
        sig = ema(np.nan_to_num(macd), 9)
        sig[np.isnan(macd)] = np.nan
        E["macd_up"] = cross_up(macd, sig)
        E["macd_up_neg"] = E["macd_up"] & (macd < 0)
        E["macd_dn"] = cross_up(sig, macd)
        E["macd_zero"] = cross_up(macd, np.zeros(len(c)))
        t1 = ema(ema(ema(np.log(c), 15), 15), 15)
        trix = t1 - lag(t1)
        E["trix_up"] = cross_up(trix, np.zeros(len(c)))
        r14, r2 = rsi(c, 14), rsi(c, 2)
        E["rsi14_x30"] = cross_up(r14, np.full(len(c), 30.0))
        E["rsi14_x50"] = cross_up(r14, np.full(len(c), 50.0))
        E["rsi14_x70"] = cross_up(r14, np.full(len(c), 70.0))
        E["rsi14_dn70"] = cross_up(np.full(len(c), 70.0), r14)
        E["rsi2_5"] = first(r2 < 5)
        E["rsi2_10_up"] = first((r2 < 10) & (c > m200))
        hh14, ll14 = rmax(h, 14), rmin(l, 14)
        k = 100 * (c - ll14) / (hh14 - ll14)
        kk = sma(np.nan_to_num(k, nan=50.0), 3)
        dd = sma(kk, 3)
        E["stoch_up20"] = cross_up(kk, dd) & (kk < 20)
        E["stoch_dn80"] = cross_up(dd, kk) & (kk > 80)
        wr = -100 * (hh14 - c) / (hh14 - ll14)
        E["willr_x80"] = cross_up(wr, np.full(len(c), -80.0))
        tp = (h + l + c) / 3
        tps = sma(tp, 20)
        md = np.full(len(c), np.nan)
        if len(c) >= 20:
            w = np.lib.stride_tricks.sliding_window_view(tp, 20)
            md[19:] = np.abs(w - w.mean(axis=1, keepdims=True)).mean(axis=1)
        cci = (tp - tps) / (0.015 * md)
        E["cci_xm100"] = cross_up(cci, np.full(len(c), -100.0))
        E["cci_x100"] = cross_up(cci, np.full(len(c), 100.0))
        if v is not None:
            mf = tp * v
            pos = rsum(np.where(tp > lag(tp), mf, 0.0), 14)
            neg = rsum(np.where(tp < lag(tp), mf, 0.0), 14)
            mfi = 100 - 100 / (1 + pos / np.where(neg == 0, np.nan, neg))
            E["mfi_20"] = first(mfi < 20)
            E["mfi_x80"] = cross_up(mfi, np.full(len(c), 80.0))
        sd20 = rstd(c, 20)
        ub, lb = m20 + 2 * sd20, m20 - 2 * sd20
        E["bb_below"] = first(c < lb)
        E["bb_reenter"] = cross_up(c, lb)
        E["bb_above"] = first(c > ub)
        bw = (ub - lb) / m20
        bwq = np.full(len(c), np.nan)
        for i in range(126, len(c)):
            wv = bw[i - 126:i]
            wv = wv[~np.isnan(wv)]
            if len(wv) and not np.isnan(bw[i - 1]):
                bwq[i] = (wv < bw[i - 1]).mean()
        E["bb_squeeze_up"] = (bwq <= 0.2) & first(c > ub)
        atr10 = wilder(tr, 10)
        E["kelt_up"] = first(c > e20 + 2 * atr10)
        E["atr_contract"] = first((atr14 < 0.6 * atr100) & (c > m50))
        rng = h - l
        E["nr7"] = first(rng <= rmin(rng, 7))
        E["nr4_inside"] = (rng <= rmin(rng, 4)) & (h <= lag(h)) & (l >= lag(l))
        E["don20"] = first(c > lag(rmax(h, 20)))
        E["don55"] = first(c > lag(rmax(h, 55)))
        E["don100"] = first(c > lag(rmax(h, 100)))
        hi52c = lag(rmax(c, 252))
        E["hi52"] = first(c > hi52c)
        E["near_hi52"] = first(c >= 0.97 * rmax(h, 252))
        E["lo52"] = first(c < lag(rmin(c, 252)))
        if v is not None:
            v50 = lag(sma(v, 50))
            E["hi52_vol"] = (c > hi52c) & (v >= 1.5 * v50)
            E["vol2_up"] = (c > lag(c)) & (v >= 2 * v50)
            E["vol3_dn"] = (c < lag(c)) & (v >= 3 * v50)
            obv = np.cumsum(np.sign(np.nan_to_num(np.diff(c, prepend=c[0]))) * v)
            E["obv_div"] = first((obv >= rmax(obv, 50)) & (c < rmax(c, 50)))
            E["obv_x20"] = cross_up(obv, ema(obv, 20))
            mfm = np.where(h > l, ((c - l) - (h - c)) / np.where(h > l, h - l, 1), 0.0)
            cmf = rsum(mfm * v, 20) / rsum(v, 20)
            E["cmf_x10"] = cross_up(cmf, np.full(len(c), 0.10))
            upv = rsum(np.where(c > lag(c), v, 0.0), 50)
            dnv = rsum(np.where(c < lag(c), v, 0.0), 50)
            E["accum"] = first((upv >= 1.5 * dnv) & (c > m50))
        up_m, dn_m = h - lag(h), lag(l) - l
        pdm = np.where((up_m > dn_m) & (up_m > 0), up_m, 0.0)
        ndm = np.where((dn_m > up_m) & (dn_m > 0), dn_m, 0.0)
        pdi, ndi = 100 * wilder(pdm, 14) / atr14, 100 * wilder(ndm, 14) / atr14
        dx = 100 * abs(pdi - ndi) / (pdi + ndi)
        adx = wilder(np.nan_to_num(dx), 14)
        adx[:28] = np.nan
        E["adx_x20"] = cross_up(adx, np.full(len(c), 20.0)) & (pdi > ndi)
        E["di_cross"] = cross_up(pdi, ndi) & (adx > 25)
        ar_up = np.full(len(c), np.nan)
        ar_dn = np.full(len(c), np.nan)
        if len(c) > 25:
            wh = np.lib.stride_tricks.sliding_window_view(h, 26)
            wl = np.lib.stride_tricks.sliding_window_view(l, 26)
            ar_up[25:] = 100 * wh.argmax(axis=1) / 25
            ar_dn[25:] = 100 * wl.argmin(axis=1) / 25
        E["aroon_up"] = cross_up(ar_up, np.full(len(c), 70.0)) & (ar_dn < 30)
        st = supertrend(h, l, c)
        E["supertrend_up"] = (st == 1) & (lag(st) == -1)
        ps = psar_dir(h, l)
        E["psar_up"] = (ps == 1) & (lag(ps) == -1)
        tenkan = (rmax(h, 9) + rmin(l, 9)) / 2
        kijun = (rmax(h, 26) + rmin(l, 26)) / 2
        spa, spb = lag((tenkan + kijun) / 2, 26), lag((rmax(h, 52) + rmin(l, 52)) / 2, 26)
        E["ichi_cloud"] = first(c > np.fmax(spa, spb))
        E["tk_cross"] = cross_up(tenkan, kijun)
        po, pc = lag(o), lag(c)
        E["engulf"] = (pc < po) & (c > o) & (o <= pc) & (c >= po)
        body = abs(c - o)
        lower = np.minimum(o, c) - l
        upper = h - np.maximum(o, c)
        E["hammer"] = (lower >= 2 * body) & (upper <= body) & (c < lag(c, 5)) & (h > l)
        E["gap_up3"] = (o >= 1.03 * pc) & (c > o)
        E["gap_dn3"] = o <= 0.97 * pc
        E["dip3"] = first((c < lag(c)) & (lag(c) < lag(c, 2)) & (lag(c, 2) < lag(c, 3)) & (c > m200))
        E["drop5d_10"] = first(c / lag(c, 5) - 1 <= -0.10)
        E["ibs_low"] = first(((c - l) / np.where(h > l, h - l, np.nan) <= 0.2) & (c > m200))
        E["flag"] = first((lag(c, 5) / lag(c, 15) - 1 >= 0.10) & (rmax(c, 5) <= 1.05 * rmin(c, 5)))
        rs = c / nc
        E["rs_hi"] = first(rs >= rmax(rs, 252))
        E["rs_x50"] = cross_up(rs, sma(rs, 50))
        E["rs3m_10"] = first((c / lag(c, 63)) / (nc / lag(nc, 63)) - 1 >= 0.10)
    return {k: np.nan_to_num(x.astype(float)).astype(bool) for k, x in E.items()}


# ---------- statistics ----------
def month_t(rows):
    """rows: list of (month, value). Mean of monthly means, its t-stat and the number of months."""
    by = {}
    for m, x in rows:
        by.setdefault(m, []).append(x)
    mm = np.array([np.mean(v) for v in by.values()])
    if len(mm) < 3:
        return float(mm.mean()) if len(mm) else None, None, len(mm)
    se = mm.std(ddof=1) / math.sqrt(len(mm))
    return float(mm.mean()), (float(mm.mean() / se) if se > 0 else None), len(mm)


def p_one_sided(t, df):
    """Upper-tail p-value of t (normal approximation; df is 12+ months here)."""
    if t is None:
        return 1.0
    return 0.5 * math.erfc(t / math.sqrt(2))


def summarize(rows):
    """rows: list of (month, abnormal, net_vs_nifty, up_regime)."""
    if not rows:
        return {"n": 0}
    ab = np.array([r[1] for r in rows])
    nv = np.array([r[2] for r in rows])
    m_ab, t_ab, months = month_t([(r[0], r[1]) for r in rows])
    m_nv, t_nv, _ = month_t([(r[0], r[2]) for r in rows])
    years = {}
    for r in rows:
        years.setdefault(r[0][:4], []).append(r[1])
    return {"n": len(rows), "months": months, "abn": round(m_ab, 5) if m_ab is not None else None,
            "t_abn": round(t_ab, 2) if t_ab is not None else None, "net": round(m_nv, 5) if m_nv is not None else None,
            "t_net": round(t_nv, 2) if t_nv is not None else None, "win_abn": round(float((ab > 0).mean()), 3),
            "win_net": round(float((nv > 0).mean()), 3), "pos_years": sum(1 for v in years.values() if np.mean(v) > 0),
            "years": len(years)}


MTYPES = {"rising": "Rising market: Nifty above a rising 200-day average",
          "falling": "Falling market: Nifty below a falling 200-day average",
          "choppy": "Choppy market: Nifty and its 200-day average disagree (a turn may be under way)"}


def market_types(ncl) -> list:
    """The market type on each date, from the Nifty 50 alone (known on that day, no look-ahead)."""
    m200 = sma(ncl, 200)
    out = []
    for t in range(len(ncl)):
        if t < 220 or np.isnan(m200[t]) or np.isnan(m200[t - 20]):
            out.append("choppy")
            continue
        above, rising = ncl[t] > m200[t], m200[t] > m200[t - 20]
        out.append("rising" if above and rising else "falling" if not above and not rising else "choppy")
    return out


def playbook(lab: dict, mt: str | None = None) -> dict:
    """Which indicators the back-test favours, and which it warns against, in today's market type.

    Grades (out-of-sample = last 3 years, never used to pick the rules):
      proven  - passed every check in run() including Holm's many-ideas correction, and positive in this market type
      leaning - in this market type: positive before AND after the cut-off (t >= 1.5 in both), beats the Nifty after
                charges out of sample, 60+ cases over 6+ months. A lead, not proven: it has not survived the many-ideas test.
      avoid   - in this market type: negative before and after the cut-off, out-of-sample t <= -1.5.
    """
    mt = mt or (lab.get("market") or {}).get("type") or "choppy"
    use, avoid = [], []
    for k, r in (lab.get("indicators") or {}).items():
        o, i_ = r.get("out_" + mt) or {}, r.get("in_" + mt) or {}
        if o.get("n", 0) < 60 or (o.get("months") or 0) < 6 or o.get("abn") is None or i_.get("abn") is None:
            continue
        row = {"k": k, "name": r["name"], "abn": o["abn"], "net": o.get("net"), "t": o.get("t_abn"), "n": o["n"],
               "in_abn": i_["abn"], "in_t": i_.get("t_abn"), "win": o.get("win_abn")}
        if r.get("verdict") == "keep" and o["abn"] > 0:
            use.append(dict(row, grade="proven"))
        elif (i_["abn"] > 0 and o["abn"] > 0 and (i_.get("t_abn") or 0) >= 1.5 and (o.get("t_abn") or 0) >= 1.5
              and (o.get("net") or 0) > 0):
            use.append(dict(row, grade="leaning"))
        elif i_["abn"] < 0 and o["abn"] < 0 and (o.get("t_abn") or 0) <= -1.5:
            avoid.append(dict(row, grade="avoid"))
    use.sort(key=lambda x: (x["grade"] != "proven", -x["abn"]))
    avoid.sort(key=lambda x: x["abn"])
    return {"asof": lab.get("asof"), "type": mt, "label": MTYPES.get(mt, mt), "since": (lab.get("market") or {}).get("since"),
            "use": use, "avoid": avoid, "proven": sum(1 for x in use if x["grade"] == "proven")}


def xs_today(data: dict, last: str) -> dict:
    """Today's members of each cross-sectional factor (same rules as run(), on the last session)."""
    rows = []
    for sym, o in data.items():
        c = [x for x in o["c"] if x is not None]
        if len(c) < 253 or o["d"][-1] != last:
            continue
        c = np.array(c[-253:], float)
        dl = np.diff(np.log(c[-61:]))
        rows.append((sym, c[-22] / c[0] - 1, c[-22] / c[-127] - 1, c[-1] / c[-22] - 1, float(np.std(dl)), c[-1] / c[-252:].max()))
    out = {}
    if len(rows) < 100:
        return out
    for name, col, top in (("xs_mom12", 1, True), ("xs_mom6", 2, True), ("xs_mom12_low", 1, False), ("xs_rev1", 3, False),
                           ("xs_lowvol", 4, False), ("xs_highvol", 4, True), ("xs_hi52", 5, True)):
        v = np.array([r[col] for r in rows])
        q = np.quantile(v, 0.9 if top else 0.1)
        pick = [(rows[j][0], v[j]) for j in range(len(rows)) if (v[j] >= q if top else v[j] <= q)]
        pick.sort(key=lambda z: -z[1] if top else z[1])
        out[name] = [s for s, _ in pick]
    return out


def run(data: dict, nifty: dict, asof: str | None = None) -> dict:
    """data: {sym: {d,o,h,l,c,v}}; nifty: {d,c}. Returns the lab result (JSON-able)."""
    dates = list(nifty["d"])
    di = {d: i for i, d in enumerate(dates)}
    N = len(dates)
    ncl = np.array(nifty["c"], float)
    nm200 = sma(ncl, 200)
    up_reg = ncl > nm200
    mtype = market_types(ncl)
    nfwd = np.full(N, np.nan)
    nfwd[:N - H] = ncl[H:] / ncl[:N - H] - 1
    cut = (dt.date.fromisoformat(dates[-1]) - dt.timedelta(days=int(365 * OOS_YEARS))).isoformat()
    syms = sorted(data)
    S = len(syms)
    fwd = np.full((S, N), np.nan)              # stock 21-day forward return by panel date
    cl = np.full((S, N), np.nan)
    ok = np.zeros((S, N), bool)                 # usable case: 252 bars of history, no split/bad tick in the window
    ev_rows = []                                # (sym index, date index, name)
    for si, sym in enumerate(syms):
        o_ = data[sym]
        keep = [(di[d], k) for k, d in enumerate(o_["d"]) if d in di]
        if len(keep) < 300:
            continue
        pos = np.array([p for p, _ in keep])
        idx = [k for _, k in keep]
        col = lambda key: np.array([o_[key][k] if o_[key][k] is not None else np.nan for k in idx], float)
        c, h, l, op = col("c"), col("h"), col("l"), col("o")
        v = col("v") if o_.get("v") else None
        if np.isnan(c).any():                    # forward-fill rare gaps
            for k in range(1, len(c)):
                if np.isnan(c[k]):
                    c[k] = c[k - 1]
        for a in (h, l, op):
            a[np.isnan(a)] = c[np.isnan(a)]
        nc = ncl[pos]
        n = len(c)
        f = np.full(n, np.nan)
        f[:n - H] = c[H:] / c[:n - H] - 1
        fwd[si, pos] = f
        cl[si, pos] = c
        jump = np.abs(c[1:] / c[:-1] - 1) > 0.40
        bad = np.zeros(n, bool)
        for k in np.where(jump)[0] + 1:
            bad[max(0, k - H - 1):k + 11] = True
        good = ~bad & ~np.isnan(f)
        good[:252] = False
        ok[si, pos] = good
        for name, e in events(op, h, l, c, v, nc).items():
            for k in np.where(e & good)[0]:
                ev_rows.append((si, pos[k], name))
    # cross-sectional factors every 21 trading days
    with np.errstate(invalid="ignore", divide="ignore"):
        lr = np.log(cl)
        dl = np.diff(lr, axis=1, prepend=np.nan)
        for t in range(252, N - H, H):
            avail = ok[:, t] & ~np.isnan(cl[:, t - 252])
            if avail.sum() < 100:
                continue
            m12 = cl[:, t - 21] / cl[:, t - 252] - 1
            m6 = cl[:, t - 21] / cl[:, t - 126] - 1
            r1 = cl[:, t] / cl[:, t - 21] - 1
            vol = np.nanstd(dl[:, t - 59:t + 1], axis=1)
            hi = cl[:, t] / np.nanmax(cl[:, t - 251:t + 1], axis=1)
            for name, x, top in (("xs_mom12", m12, True), ("xs_mom6", m6, True), ("xs_mom12_low", m12, False),
                                 ("xs_rev1", r1, False), ("xs_lowvol", vol, False), ("xs_highvol", vol, True),
                                 ("xs_hi52", hi, True)):
                vals = np.where(avail & ~np.isnan(x), x, np.nan)
                good = ~np.isnan(vals)
                if good.sum() < 100:
                    continue
                q = np.nanquantile(vals, 0.9 if top else 0.1)
                pick = good & ((vals >= q) if top else (vals <= q))
                for si in np.where(pick)[0]:
                    ev_rows.append((si, t, name))
    # baseline: the average usable stock's forward return on each date
    base = np.array([np.nanmean(np.where(ok[:, t], fwd[:, t], np.nan)) if ok[:, t].any() else np.nan for t in range(N)])
    rows = {k: {"in": [], "out": []} for k in NAMES}
    for si, t, name in ev_rows:
        r = fwd[si, t]
        if np.isnan(r) or np.isnan(base[t]) or np.isnan(nfwd[t]):
            continue
        per = "out" if dates[t] >= cut else "in"
        rows[name][per].append((dates[t][:7], float(r - base[t]), float(r - nfwd[t] - COST), bool(up_reg[t]), mtype[t]))
    K = len(NAMES)
    res = {}
    for k in NAMES:
        r = {"name": NAMES[k]}
        for per in ("in", "out"):
            rr = rows[k][per]
            r[per] = summarize(rr)
            r[per + "_up"] = summarize([x for x in rr if x[3]])
            r[per + "_weak"] = summarize([x for x in rr if not x[3]])
            for mt in MTYPES:
                r[per + "_" + mt] = summarize([x for x in rr if x[4] == mt])
        res[k] = r
    # base rate (the average stock vs the Nifty, after charges) for context
    base_rows = {"in": [], "out": []}
    for t in range(252, N - H, 5):
        if np.isnan(base[t]) or np.isnan(nfwd[t]):
            continue
        base_rows["out" if dates[t] >= cut else "in"].append((dates[t][:7], 0.0, float(base[t] - nfwd[t] - COST), bool(up_reg[t])))
    # Holm's step-down across all K indicators, separately for the buy side and the warning side
    for side, sign in (("keep", 1), ("avoid", -1)):
        ps = sorted(((p_one_sided((res[k]["out"].get("t_abn") or 0) * sign, None), k) for k in NAMES), key=lambda x: x[0])
        passed, stop = set(), False
        for j, (p, k) in enumerate(ps):
            if not stop and p <= ALPHA / (K - j):
                passed.add(k)
            else:
                stop = True
        for k in NAMES:
            res[k][f"holm_{side}"] = k in passed
            res[k][f"p_{side}"] = round(next(p for p, kk in ps if kk == k), 6)
    for k, r in res.items():
        i_, o_ = r["in"], r["out"]
        enough = o_.get("n", 0) >= 100 and o_.get("months", 0) >= 12
        keep = (enough and (i_.get("abn") or 0) > 0 and (i_.get("t_abn") or 0) >= 2 and (o_.get("abn") or 0) > 0
                and r["holm_keep"] and (o_.get("net") or 0) > 0)
        avoid = (enough and (i_.get("abn") or 0) < 0 and (i_.get("t_abn") or 0) <= -2 and (o_.get("abn") or 0) < 0
                 and r["holm_avoid"])
        near = (not keep and enough and (i_.get("abn") or 0) > 0 and (o_.get("abn") or 0) > 0 and r["p_keep"] <= 0.05)
        r["verdict"] = "keep" if keep else "avoid" if avoid else "near" if near else "drop"
    keep = sorted([k for k in res if res[k]["verdict"] == "keep"], key=lambda k: -(res[k]["out"]["net"] or 0))
    since = N - 1
    while since > 0 and mtype[since - 1] == mtype[N - 1]:
        since -= 1
    out_days = [t for t in range(N) if dates[t] >= cut]
    return {"asof": asof or dates[-1], "from": dates[0], "cutoff": cut,
            "market": {"type": mtype[N - 1], "since": dates[since], "label": MTYPES[mtype[N - 1]],
                       "share_out": {mt: round(sum(1 for t in out_days if mtype[t] == mt) / max(1, len(out_days)), 3) for mt in MTYPES}}, "stocks": int((ok.any(axis=1)).sum()),
            "tested": K, "horizon_days": H, "cost": COST, "alpha": ALPHA,
            "base": {p: summarize(base_rows[p]) for p in ("in", "out")},
            "keep": keep, "avoid": [k for k in res if res[k]["verdict"] == "avoid"],
            "near": sorted([k for k in res if res[k]["verdict"] == "near"], key=lambda k: res[k]["p_keep"]),
            "indicators": res,
            "rules": __doc__.split("Pre-registered rules")[1].split("Research software")[0].strip()}
