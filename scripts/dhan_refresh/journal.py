"""Desk journal: what the desk did each day, every recommendation with its outcome, and the indicator back-test.

Runs inside the daily dhan-refresh run (refresh.py --with-tech), after the technical model, trade plan and track
record, on the same Dhan history; no extra login, no extra schedule. Writes:
  journal/JOURNAL.md              the journal a person reads (rebuilt every run)
  journal/recommendations.json    ledger: every trade plan the desk printed, scored against later Dhan bars
  journal/daily-log.json          one entry per trading day the run saw
  journal/indicator-lab.json      the indicator back-test (indicator_lab.py)
  journal/lab-today.json          stocks where an indicator the lab keeps fired on the last session
Research software, not advice.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
J = "journal"
COST = 0.0025


def _j(p: Path, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def _w(p: Path, obj, compact=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, separators=(",", ":")) if compact else json.dumps(obj, indent=1), encoding="utf-8")


# ---------- recommendations ledger ----------
def add_plans(ledger: dict, tp: dict) -> int:
    """Add the trade plans of one day (docs/tradeplan.json) to the ledger. Returns how many were new."""
    day, have, n = tp.get("asof"), {(r["d"], r["sym"]) for r in ledger.get("recs", [])}, 0
    if not day:
        return 0
    for sym, p in (tp.get("plans") or {}).items():
        if (day, sym) in have or not p.get("entry"):
            continue
        fails = [c["rule"] for c in p.get("checks", []) if not c.get("ok")]
        ledger.setdefault("recs", []).append({
            "d": day, "sym": sym, "sig": p.get("signal"), "entry": p["entry"], "stop": p.get("stop"),
            "target": p.get("target"), "qty": p.get("qty") or 0, "p_target": p.get("p_target"), "p_stop": p.get("p_stop"),
            "exp_rs": p.get("exp_net_rs"), "called": not fails, "failed": fails})
        n += 1
    return n


def score(rec: dict, o: dict | None, nmap: dict, horizon: int = 21) -> dict:
    """Walk Dhan daily bars after the plan's day: stop first if both are touched the same day, else target,
    else exit at the close of day `horizon`. Open plans are marked to the last close."""
    out = {k: rec[k] for k in rec if k not in ("status", "days", "exit", "ret", "x_nifty", "pnl_rs", "last")}
    if not o:
        return {**out, "status": "no data"}
    d = o["d"]
    after = [k for k, x in enumerate(d) if x > rec["d"]]
    e, s, t = rec["entry"], rec.get("stop"), rec.get("target")
    status, ex, k_end = "open", None, None
    for j, k in enumerate(after[:horizon]):
        if s and o["l"][k] is not None and o["l"][k] <= s:
            status, ex, k_end = "stop", s, k
            break
        if t and o["h"][k] is not None and o["h"][k] >= t:
            status, ex, k_end = "target", t, k
            break
        if j == horizon - 1:
            status, ex, k_end = "time", o["c"][k], k
    if not after:
        return {**out, "status": "open", "days": 0}
    if ex is None:
        k_end, ex = after[-1], o["c"][after[-1]]
    days = after.index(k_end) + 1
    ret = ex / e - 1
    n0, n1 = nmap.get(rec["d"]), nmap.get(d[k_end])
    xn = ret - (n1 / n0 - 1) if n0 and n1 else None
    qty = rec.get("qty") or 0
    pnl = qty * (ex - e) - COST * qty * e
    return {**out, "status": status, "days": days, "exit": round(ex, 2), "last": d[k_end], "ret": round(ret, 5),
            "x_nifty": round(xn, 5) if xn is not None else None, "pnl_rs": round(pnl, 1)}


def rec_summary(recs: list) -> dict:
    def block(rs):
        done = [r for r in rs if r.get("status") in ("stop", "target", "time")]
        opn = [r for r in rs if r.get("status") == "open"]
        b = {"plans": len(rs), "closed": len(done), "open": len(opn)}
        for name, grp in (("closed", done), ("all", [r for r in rs if r.get("ret") is not None])):
            if grp:
                b[f"{name}_avg_ret"] = round(float(np.mean([r["ret"] for r in grp])), 5)
                xs = [r["x_nifty"] for r in grp if r.get("x_nifty") is not None]
                b[f"{name}_avg_x_nifty"] = round(float(np.mean(xs)), 5) if xs else None
                b[f"{name}_beat_nifty"] = round(sum(x > 0 for x in xs) / len(xs), 3) if xs else None
                b[f"{name}_pnl_rs"] = round(sum(r.get("pnl_rs") or 0 for r in grp), 0)
        if done:
            b["target_first"] = sum(r["status"] == "target" for r in done)
            b["stop_first"] = sum(r["status"] == "stop" for r in done)
            b["time_exit"] = sum(r["status"] == "time" for r in done)
        return b
    out = {"all": block(recs), "called": block([r for r in recs if r.get("called")])}
    for sig in sorted({r.get("sig") for r in recs if r.get("sig")}):
        out["sig:" + sig] = block([r for r in recs if r.get("sig") == sig])
    return out


def picks_summary(track: dict, data: dict, nmap: dict, last: str) -> dict:
    """The live track record (docs/track-record.json) marked to the last close: return vs the Nifty so far."""
    out = {}
    for p in track.get("picks", []):
        o = data.get(p["sym"])
        if not o or not p.get("c0") or not p.get("n0"):
            continue
        c1, n1 = o["c"][-1], nmap.get(o["d"][-1]) or nmap.get(last)
        if c1 is None or not n1:
            continue
        x = (c1 / p["c0"] - 1) - (n1 / p["n0"] - 1)
        b = out.setdefault(p["kind"], {"n": 0, "xs": []})
        b["n"] += 1
        b["xs"].append(x)
    res = {}
    for k, b in out.items():
        xs = np.array(b["xs"])
        res[k] = {"picks": b["n"], "avg_x_nifty_so_far": round(float(xs.mean()), 5), "beat_nifty": round(float((xs > 0).mean()), 3)}
    return res


def indicator_lab_playbook(lab: dict) -> dict:
    import indicator_lab as L
    return L.playbook(lab)


def lab_today(data: dict, nifty: dict, keep: list, near: list, play: dict | None = None) -> dict:
    """Stocks where a kept, near-miss or playbook indicator fired on the last session."""
    import indicator_lab as L
    nm = dict(zip(nifty["d"], nifty["c"]))
    last = nifty["d"][-1]
    pu = [x["k"] for x in (play or {}).get("use", [])]
    pa = [x["k"] for x in (play or {}).get("avoid", [])]
    allk = list(dict.fromkeys(keep + near + pu + pa))
    out = {"asof": last, "keep": {}, "near": {}, "use": {}, "avoid": {}}
    if any(k.startswith("xs_") for k in allk):
        xs = L.xs_today(data, last)
        for k in allk:
            if k in xs:
                for grp, ks in (("keep", keep), ("near", near), ("use", pu), ("avoid", pa)):
                    if k in ks:
                        out[grp][k] = xs[k]
    want = [k for k in allk if not k.startswith("xs_")]
    if not want:
        return out
    for sym, o in data.items():
        if len(o["c"]) < 300 or o["d"][-1] != last:
            continue
        try:
            arr = lambda key: np.array([x if x is not None else np.nan for x in o[key]], float)
            nc = np.array([nm.get(d, np.nan) for d in o["d"]], float)
            if np.isnan(nc).any():
                continue
            ev = L.events(arr("o"), arr("h"), arr("l"), arr("c"), arr("v") if o.get("v") else None, nc)
        except Exception:
            continue
        for k in want:
            if k in ev and ev[k][-1]:
                for grp, ks in (("keep", keep), ("near", near), ("use", pu), ("avoid", pa)):
                    if k in ks:
                        out[grp].setdefault(k, []).append(sym)
    return out


# ---------- the desk's own back-tests (moved here from the Trading Terminal, 26 Nov 2026) ----------
def desk_backtests(root: Path) -> list:
    L = []
    tm = _j(root / "docs/tech-model.json", {})
    rl = (_j(root / "docs/risklab.json", {}) or {}).get("signals") or {}
    if tm.get("signals"):
        names = tm.get("names") or {}
        sig = tm["signals"]
        nt = sum(1 for v in sig.values() if v.get("tested"))
        ns = sum(1 for v in rl.values() if v.get("survives"))
        L.append("## The desk's own signal back-test\n")
        L.append(f"The {len(sig)} signals behind the desk's buy lists, re-tested every run on Dhan daily data from {tm.get('from')} "
                 f"(out-of-sample from {tm.get('cutoff')}, {tm.get('stocks')} stocks). {nt} pass the desk's single-signal test in "
                 f"rising markets; {ns} of {len(rl) or len(sig)} survive the joint many-signals test (risk lab), which is why the "
                 f"desk makes no real calls. Moved here from the Trading Terminal so the terminal stays a clean screen.\n")
        L.append("| Signal | passes (rising) | passes (weak) | cases after | 10-day vs Nifty after | lift vs average stock | many-signals p | survives |\n"
                 "|---|---|---|---|---|---|---|---|")
        for k, v in sorted(sig.items(), key=lambda kv: -((kv[1].get("lift_out_x10") or -9))):
            o = (v.get("out") or {}).get("up") or {}
            r = rl.get(k) or {}
            L.append(f"| {names.get(k, k)} | {'yes' if v.get('tested') else 'no'} | {'yes' if v.get('tested_weak') else 'no'} | "
                     f"{o.get('n', 0)} | {pct(o.get('x10'), 2)} | {pct(v.get('lift_out_x10'), 2)} | {r.get('spa_p', 'n/a')} | "
                     f"{'yes' if r.get('survives') else 'no'} |")
        L.append("")
    bt = _j(root / "docs/terminal/backtest.json", {})
    g = ((bt.get("grid") or {}).get("picks") or {})
    if g:
        days = bt.get("days") or []
        L.append("## The terminal's intraday back-test (last month)\n")
        L.append(f"Desk picks bought at 09:30, 12:30 or 15:00 on each of the last {len(days)} sessions "
                 f"({days[0] if days else '?'} to {days[-1] if days else '?'}), {bt.get('stocks')} stocks, 5-minute Dhan bars, "
                 f"held to the plan's exit. Rules passing: {len(bt.get('passing') or [])}.\n")
        L.append("| Buy time | trades | average vs Nifty | share up | t | passes | Rs over the month |\n|---|---|---|---|---|---|---|")
        for t_, by in g.items():
            r = ((by or {}).get("any") or {}).get("plan") or {}
            eq = ((bt.get("equity") or {}).get(t_) or [None])[-1]
            L.append(f"| {t_} | {r.get('n', 0)} | {r.get('ex', 0):+.2f}% | {r.get('hit', 0):.0%} | {r.get('t')} | "
                     f"{'yes' if r.get('pass') else 'no'} | {eq if eq is not None else 'n/a'} |")
        L.append("")
    return L


# ---------- the markdown journal ----------
def pct(x, d=1):
    return "n/a" if x is None else f"{x * 100:+.{d}f}%"


def render_playbook(play: dict, log: list) -> list:
    L = ["## Today's playbook (feeds the Trading Terminal)\n"]
    L.append(f"**Market type: {play['type']}** since {play.get('since')}. {play['label']}. The terminal's at-a-glance "
             f"cards, its screen order and the back-test picks all follow this section, and the trade plans skip any "
             f"signal the back-test warns against in this market type. Rebuilt every run, so it changes when the market "
             f"type changes or the evidence moves.\n")
    L.append("Grades: **proven** passed every check including the many-ideas correction; **leaning** was positive "
             "before and after the cut-off in this market type (t 1.5+ both times) and beat the Nifty after charges, but "
             "has not survived the many-ideas correction, so it is a lead; **avoid** was reliably worse than the average "
             "stock in this market type.\n")
    def tab(rows, title):
        out = [f"### {title}\n"]
        if not rows:
            return out + ["None in this market type.\n"]
        out.append("| Indicator | grade | vs average stock after | t | vs Nifty after charges | cases | before cut-off | fired today |\n|---|---|---|---|---|---|---|---|")
        fired = {**play.get("fired", {}), **play.get("warned", {})}
        for x in rows:
            f = fired.get(x["k"]) or []
            out.append(f"| {x['name']} | {x['grade']} | {pct(x['abn'])} | {x.get('t')} | {pct(x.get('net'))} | {x['n']} | "
                       f"{pct(x.get('in_abn'))} (t {x.get('in_t')}) | {', '.join(sorted(f)[:12]) + (f' +{len(f) - 12}' if len(f) > 12 else '') or 'none'} |")
        return out + [""]
    L += tab(play.get("use", []), f"Favoured in a {play['type']} market")
    L += tab(play.get("avoid", []), f"Warnings in a {play['type']} market")
    hist = [e for e in log if e.get("market")]
    if hist:
        L.append("### Market type history (from this journal)\n")
        runs, cur = [], None
        for e in hist:
            if not cur or cur[0] != e["market"]:
                cur = [e["market"], e["asof"], e["asof"], len(e.get("play_use") or [])]
                runs.append(cur)
            else:
                cur[2] = e["asof"]
        for m, a, b, n in reversed(runs[-20:]):
            L.append(f"- {a} to {b}: {m} ({n} indicators favoured at the start)")
        L.append("")
    return L


def render(root: Path, lab: dict, ledger: dict, log: list, picks: dict, today: dict, tech: dict | None, play: dict | None = None) -> str:
    how = (root / J / "how-it-works.md").read_text(encoding="utf-8") if (root / J / "how-it-works.md").exists() else ""
    L = []
    last = log[-1] if log else {}
    L.append("# Evidence Desk journal\n")
    L.append(f"Last updated by the daily run: **{last.get('run_ist', 'n/a')} IST**, market data as of the close of "
             f"**{last.get('asof', 'n/a')}**. This file is rebuilt automatically every run. Research software, not advice.\n")
    L.append("## Today in one paragraph\n")
    L.append(last.get("summary", "No run logged yet.") + "\n")
    if play and play.get("type"):
        L += render_playbook(play, log)
    # indicator lab
    ind = lab.get("indicators", {}) if lab else {}
    if lab:
        L.append("## Which indicators work (back-test)\n")
        L.append(f"Tested **{lab['tested']} indicators** on {lab['stocks']} Nifty 500 stocks, Dhan daily data "
                 f"{lab['from']} to {lab['asof']}. In-sample: before {lab['cutoff']}. Out-of-sample: {lab['cutoff']} "
                 f"onwards. Outcome: the next {lab['horizon_days']} trading days, bought at the signal day's close, "
                 f"after {lab['cost'] * 100:.2f}% round-trip charges.\n")
        b = lab.get("base", {}).get("out", {})
        L.append(f"Yardstick: the average stock in this universe did {pct(b.get('net'), 2)} vs the Nifty per 21 days "
                 f"after charges out-of-sample. An indicator has to beat the average stock, not just the Nifty.\n")
        def line(k):
            r = ind[k]
            o, i_ = r["out"], r["in"]
            return (f"| {r['name']} | {i_.get('n', 0)} | {pct(i_.get('abn'))} (t {i_.get('t_abn')}) | {o.get('n', 0)} | "
                    f"{pct(o.get('abn'))} (t {o.get('t_abn')}) | {pct(o.get('net'))} | {o.get('win_net', 'n/a')} | "
                    f"{r['p_keep'] if r['verdict'] != 'avoid' else r['p_avoid']} | **{r['verdict']}** |")
        head = ("| Indicator | cases before | vs average stock before | cases after | vs average stock after | "
                "vs Nifty after charges | share beating Nifty | p-value | verdict |\n|---|---|---|---|---|---|---|---|---|")
        keep, avoid, near = lab.get("keep", []), lab.get("avoid", []), lab.get("near", [])
        L.append(f"**Kept: {len(keep)}.** " + ("; ".join(ind[k]["name"] for k in keep) if keep else
                 "None passed every check, so the desk adds no new buy rule from this test.") + "\n")
        L.append(f"**Warnings (reliably worse than the average stock): {len(avoid)}.** "
                 + ("; ".join(ind[k]["name"] for k in avoid) if avoid else "None.") + "\n")
        L.append(f"**Near misses (positive in both periods, p under 0.05 on its own, but not after the many-ideas "
                 f"correction or the charges): {len(near)}.** These are watched, not traded.\n")
        L.append("### All indicators, best out-of-sample first\n")
        L.append(head)
        order = sorted(ind, key=lambda k: -(ind[k]["out"].get("t_abn") or -99))
        L += [line(k) for k in order]
        L.append("\nHow to read: *vs average stock* is the extra 21-day return over the average Nifty 500 stock on the "
                 "same days, with a t-statistic clustered by month (2 or more is the usual bar for one idea; with "
                 f"{lab['tested']} ideas the bar is higher, which is what the p-value column and Holm's correction "
                 "handle). Rules, fixed before the results:\n")
        L.append("> " + lab.get("rules", "").replace("\n", "\n> ") + "\n")
        if today and (today.get("keep") or today.get("near")):
            L.append("### Fired on the last session\n")
            for grp in ("keep", "near"):
                for k, syms in (today.get(grp) or {}).items():
                    L.append(f"- {grp}: {ind.get(k, {}).get('name', k)}: {', '.join(sorted(syms)[:30])}"
                             + (f" and {len(syms) - 30} more" if len(syms) > 30 else ""))
            L.append("")
    # recommendations
    recs = ledger.get("recs", [])
    sm = ledger.get("summary", {})
    L.append("## Every recommendation and what happened\n")
    a, c = sm.get("all", {}), sm.get("called", {})
    L.append(f"The desk printed **{a.get('plans', 0)} trade plans** since {min((r['d'] for r in recs), default='n/a')}. "
             f"**{c.get('plans', 0)}** passed every check (a real call); the rest failed at least one check, most often "
             f"the many-signals test, and were shown as plans only. Each plan is scored on Dhan daily bars: stop first if "
             f"the stop and target are touched the same day, otherwise target, otherwise sold at the 21st close. "
             f"Rupee results use the plan's own share count and 0.25% charges.\n")
    L.append(f"- Closed so far: {a.get('closed', 0)} (target {a.get('target_first', 0)}, stop {a.get('stop_first', 0)}, "
             f"time exit {a.get('time_exit', 0)}); open: {a.get('open', 0)}.")
    L.append(f"- All plans, including open ones marked to the last close: average {pct(a.get('all_avg_ret'))}, "
             f"{pct(a.get('all_avg_x_nifty'))} vs the Nifty, {a.get('all_beat_nifty', 'n/a')} beat the Nifty, "
             f"Rs {a.get('all_pnl_rs', 0):,.0f} if every plan had been taken.")
    if a.get("closed"):
        L.append(f"- Closed plans only: average {pct(a.get('closed_avg_ret'))}, Rs {a.get('closed_pnl_rs', 0):,.0f}.")
    L.append(f"- Real calls (all checks passed): {c.get('plans', 0)}.\n")
    sigs = [(k[4:], v) for k, v in sm.items() if k.startswith("sig:")]
    if sigs:
        L.append("| Signal | plans | closed | target / stop / time | average so far | vs Nifty so far | Rs if all taken |\n|---|---|---|---|---|---|---|")
        for k, v in sorted(sigs, key=lambda kv: -kv[1]["plans"]):
            L.append(f"| {k} | {v['plans']} | {v['closed']} | {v.get('target_first', 0)} / {v.get('stop_first', 0)} / "
                     f"{v.get('time_exit', 0)} | {pct(v.get('all_avg_ret'))} | {pct(v.get('all_avg_x_nifty'))} | "
                     f"{v.get('all_pnl_rs', 0):,.0f} |")
        L.append("")
    if picks:
        L.append("### The live track record (picks logged before the outcome)\n")
        L.append("| Kind | picks | vs Nifty so far | share ahead of Nifty |\n|---|---|---|---|")
        for k, v in sorted(picks.items()):
            L.append(f"| {k} | {v['picks']} | {pct(v['avg_x_nifty_so_far'])} | {v['beat_nifty']} |")
        L.append("\nKinds: *rising* = tested breakout signals on leading stocks, *dips* = tested dip signals, "
                 "*score0/2/4/6* = the research screener's score bands (score0 is a random control group). "
                 "These are days old, so they say very little yet; they become meaningful after 21 trading days.\n")
    if recs:
        L.append("### Latest plans, newest first\n")
        L.append("| Day | Stock | Signal | Entry | Stop | Target | Qty | Called? | Status | Days | Return | vs Nifty | Rs |\n"
                 "|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in sorted(recs, key=lambda r: (r["d"], r["sym"]), reverse=True)[:80]:
            L.append(f"| {r['d']} | {r['sym']} | {r.get('sig')} | {r['entry']} | {r.get('stop')} | {r.get('target')} | "
                     f"{r.get('qty')} | {'yes' if r.get('called') else 'no'} | {r.get('status')} | {r.get('days', 0)} | "
                     f"{pct(r.get('ret'))} | {pct(r.get('x_nifty'))} | {r.get('pnl_rs', 0):,.0f} |")
        L.append(f"\nFull ledger: `journal/recommendations.json` ({len(recs)} plans).\n")
    L += desk_backtests(root)
    # rule changes and daily log
    ch = [e for e in log if e.get("changes")]
    L.append("## Rule changes\n")
    if ch:
        for e in reversed(ch[-30:]):
            L.append(f"- {e['asof']}: " + "; ".join(e["changes"]))
    else:
        L.append("- None yet.")
    L.append("")
    L.append("## Daily log, newest first\n")
    for e in reversed(log[-60:]):
        L.append(f"- **{e['asof']}** (run {e.get('run_ist', '?')} IST): {e.get('summary', '')}")
    L.append("")
    if how:
        L.append(how)
    return "\n".join(L) + "\n"


# ---------- entry point ----------
def run(root: Path, data: dict, nifty: dict, tech: dict | None = None, with_lab: bool = True) -> str:
    root = Path(root)
    jd = root / J
    jd.mkdir(exist_ok=True)
    nmap = dict(zip(nifty["d"], nifty["c"]))
    asof = nifty["d"][-1]
    msgs = []
    # 1. indicator lab
    lab_p = jd / "indicator-lab.json"
    prev_lab = _j(lab_p, {})
    lab = prev_lab
    if with_lab:
        import indicator_lab
        try:
            lab = indicator_lab.run(data, nifty, asof)
            _w(lab_p, lab)
            msgs.append(f"lab: {lab['tested']} tested, keep {lab['keep']}, avoid {lab['avoid']}, near {lab['near']}")
        except Exception as e:
            msgs.append(f"lab FAILED: {str(e)[:200]}")
    today, play = {}, {}
    if lab:
        try:
            play = indicator_lab_playbook(lab)
        except Exception as e:
            msgs.append(f"playbook failed: {str(e)[:120]}")
        try:
            today = lab_today(data, nifty, lab.get("keep", []), lab.get("near", []), play)
            _w(jd / "lab-today.json", today)
        except Exception as e:
            msgs.append(f"lab-today failed: {str(e)[:120]}")
        if play and play.get("type"):
            # the terminal reads this file: today's market type, what the back-test favours and warns against,
            # and the stocks where those indicators fired on the last session
            play = dict(play, fired=(today or {}).get("use", {}), warned=(today or {}).get("avoid", {}))
            _w(jd / "playbook.json", play)
            msgs.append(f"playbook: {play['type']}, use {[x['k'] for x in play['use']]}, avoid {[x['k'] for x in play['avoid']]}")
    # 2. recommendations ledger
    led_p = jd / "recommendations.json"
    ledger = _j(led_p, {"recs": []})
    tp = _j(root / "docs/tradeplan.json", {})
    added = add_plans(ledger, tp)
    ledger["recs"] = [score(r, data.get(r["sym"]), nmap) for r in ledger.get("recs", [])]
    ledger["summary"] = rec_summary(ledger["recs"])
    ledger["asof"] = asof
    _w(led_p, ledger, compact=True)
    # 3. live track record marked to market
    picks = picks_summary(_j(root / "docs/track-record.json", {}), data, nmap, asof)
    # 4. daily log
    log_p = jd / "daily-log.json"
    log = [e for e in _j(log_p, []) if e.get("asof") != asof]
    changes = []
    if prev_lab and lab and prev_lab.get("asof") != lab.get("asof"):
        for side in ("keep", "avoid"):
            was, now = set(prev_lab.get(side, [])), set(lab.get(side, []))
            for k in sorted(now - was):
                changes.append(f"{lab['indicators'][k]['name']} added to {side}")
            for k in sorted(was - now):
                changes.append(f"{lab['indicators'].get(k, {}).get('name', k)} removed from {side}")
    prev = log[-1] if log else {}
    if play and play.get("type"):
        if prev.get("market") and prev.get("market") != play["type"]:
            changes.append(f"market type changed from {prev['market']} to {play['type']}: the playbook switched to the {play['type']}-market results")
        pu = set(prev.get("play_use") or [])
        nu = {x["k"] for x in play["use"]}
        pa_, na_ = set(prev.get("play_avoid") or []), {x["k"] for x in play["avoid"]}
        nm_ = lambda k: (lab["indicators"].get(k) or {}).get("name", k)
        if prev.get("play_use") is not None:
            changes += [f"now favoured: {nm_(k)}" for k in sorted(nu - pu)] + [f"no longer favoured: {nm_(k)}" for k in sorted(pu - nu)]
            changes += [f"now a warning: {nm_(k)}" for k in sorted(na_ - pa_)] + [f"no longer a warning: {nm_(k)}" for k in sorted(pa_ - na_)]
    sig = (tech or {}).get("signals", {})
    rising = [k for k, v in sig.items() if v.get("tested")]
    weak = [k for k, v in sig.items() if v.get("tested_weak")]
    called = sum(1 for r in ledger["recs"] if r["d"] == tp.get("asof") and r.get("called"))
    nplans = len((tp.get("plans") or {})) if tp.get("asof") == asof else 0
    up = nifty["c"][-1] > float(np.mean(nifty["c"][-200:])) if len(nifty["c"]) >= 200 else None
    a = ledger["summary"]["all"]
    summ = (f"Nifty 50 closed at {nifty['c'][-1]:,.1f} ({'above' if up else 'below'} its 200-day average, so the desk "
            f"used its {'rising' if up else 'weak'}-market rules). {len(data)} stocks loaded from Dhan. "
            f"Desk signals passing its own back-test: {len(rising)} for rising markets, {len(weak)} for weak markets. "
            f"Trade plans printed: {nplans}, real calls (every check passed): {called}. "
            f"Indicator lab: {len((lab or {}).get('keep', []))} kept of {(lab or {}).get('tested', 0)}. "
            f"All plans so far: {a.get('plans', 0)} ({a.get('closed', 0)} closed, {a.get('open', 0)} open).")
    now_ist = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).strftime("%d %b %Y %H:%M")
    log.append({"asof": asof, "run_ist": now_ist, "stocks": len(data), "rising": rising, "weak": weak, "plans": nplans,
                "called": called, "lab_keep": (lab or {}).get("keep", []), "changes": changes, "summary": summ,
                "market": play.get("type"), "play_use": [x["k"] for x in play.get("use", [])] if play else None,
                "play_avoid": [x["k"] for x in play.get("avoid", [])] if play else None})
    log = sorted(log, key=lambda e: e["asof"])[-400:]
    _w(log_p, log)
    # 5. the journal
    (jd / "JOURNAL.md").write_text(render(root, lab, ledger, log, picks, today, tech, play), encoding="utf-8")
    msgs.append(f"journal: {added} new plans, {a.get('plans', 0)} in ledger, log {len(log)} days")
    return " | ".join(msgs)


def main() -> int:
    """Lab-only run (the manual 'journal only' workflow input): log in, fetch the history, write the journal."""
    import refresh as R
    import tech_model
    root = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else ROOT
    cid, pin, sec = (os.environ[k] for k in ("DHAN_CLIENT_ID", "DHAN_PIN", "DHAN_TOTP_SECRET"))
    dhan = R.Dhan(cid, R.login(cid, pin, sec))
    data, nifty, _ = tech_model.fetch(dhan, root, tech_model.YEARS)
    tech = _j(root / "docs/tech-model.json", {})
    print(run(root, data, nifty, tech))
    return 0


if __name__ == "__main__":
    sys.exit(main())
