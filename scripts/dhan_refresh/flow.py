"""Live order flow from Dhan quote snapshots (POST /marketfeed/quote every few seconds).

Dhan's REST quote gives, per instrument: last traded price and quantity, cumulative
volume, total pending buy and sell quantity, and 5-level market depth. It does not
stream every trade, so everything here is SNAPSHOT-DERIVED: the volume traded between
two snapshots is treated as one print at the snapshot's last price, and its side is
judged against the previous snapshot's best bid and ask (at or above the ask = buyer
initiated, at or below the bid = seller initiated, otherwise the tick rule).

Modules (all labelled snapshot-derived):
  tape          time and sales: prints with side; large prints (>= 5x the session's median print)
  delta         buy, sell, net and cumulative delta; price/delta divergence
  footprint     buy and sell volume per price level; imbalances (one side >= 3x the other)
                and stacked imbalances (3+ adjacent levels)
  depth         top-5 bid vs ask quantity, total pending buy vs sell quantity
  absorption    a large print that did not move price (sellers absorbed at the bid, or buyers at the ask)
  exhaustion    price at a session extreme on shrinking delta
  trapped       heavy aggressive volume at a new high (low) followed by a close back below (above) it
"""
from __future__ import annotations

import statistics as st


def tick_bin(price: float) -> float:
    step = 0.05 if price < 100 else 0.1 if price < 500 else 0.5 if price < 2000 else 1.0 if price < 10000 else 5.0
    return round(round(price / step) * step, 2)


class Flow:
    def __init__(self, state: dict | None = None):
        s = state or {}
        self.last = s.get("last")                     # previous snapshot: ltp, vol, bid, ask
        self.tape = s.get("tape", [])                 # [t, price, qty, side]  side: 1 buy, -1 sell
        self.fp = {float(k): v for k, v in s.get("fp", {}).items()}   # price -> [buy, sell]
        self.cum = s.get("cum", 0.0)
        self.path = s.get("path", [])                 # [t, ltp, cum] one per minute
        self.depth = s.get("depth", {})
        self.events = s.get("events", [])

    def state(self) -> dict:
        return {"last": self.last, "tape": self.tape[-400:], "fp": {str(k): v for k, v in self.fp.items()},
                "cum": self.cum, "path": self.path[-400:], "depth": self.depth, "events": self.events[-40:]}

    def update(self, t: str, q: dict) -> None:
        """t: 'HH:MM:SS'. q: one instrument from Dhan's quote reply."""
        ltp = float(q.get("last_price") or 0)
        vol = float(q.get("volume") or 0)
        dep = q.get("depth") or {}
        bids = [(float(x.get("price") or 0), float(x.get("quantity") or 0)) for x in (dep.get("buy") or [])]
        asks = [(float(x.get("price") or 0), float(x.get("quantity") or 0)) for x in (dep.get("sell") or [])]
        bid = bids[0][0] if bids and bids[0][0] > 0 else None
        ask = asks[0][0] if asks and asks[0][0] > 0 else None
        if ltp <= 0:
            return
        self.depth = {"bid_qty5": sum(x[1] for x in bids), "ask_qty5": sum(x[1] for x in asks),
                      "total_buy": float(q.get("buy_quantity") or 0), "total_sell": float(q.get("sell_quantity") or 0),
                      "bid": bid, "ask": ask}
        if self.last and vol > self.last["vol"]:
            dv = vol - self.last["vol"]
            pb, pa, pl = self.last.get("bid"), self.last.get("ask"), self.last["ltp"]
            if pa and ltp >= pa:
                side = 1
            elif pb and ltp <= pb:
                side = -1
            else:
                side = 1 if ltp > pl else -1 if ltp < pl else (self.tape[-1][3] if self.tape else 0)
            self.tape.append([t, ltp, dv, side])
            k = tick_bin(ltp)
            cell = self.fp.setdefault(k, [0.0, 0.0])
            cell[0 if side > 0 else 1] += dv if side else 0
            self.cum += side * dv
            self._events(t, ltp, dv, side)
        if not self.path or self.path[-1][0][:5] != t[:5]:
            self.path.append([t, ltp, self.cum])
        else:
            self.path[-1] = [t, ltp, self.cum]
        self.last = {"ltp": ltp, "vol": vol, "bid": bid, "ask": ask}

    def _events(self, t, ltp, dv, side):
        sizes = [x[2] for x in self.tape[-300:]]
        med = st.median(sizes) if len(sizes) >= 20 else None
        if med and dv >= 5 * med:
            moved = len(self.tape) >= 2 and ltp != self.tape[-2][1]
            kind = "large print" if moved else ("absorption: sellers absorbed" if side < 0 else "absorption: buyers absorbed")
            self.events.append([t, kind, ltp, dv, side])

    def summary(self) -> dict:
        if not self.tape:
            return {"prints": 0}
        buy = sum(x[2] for x in self.tape if x[3] > 0)
        sell = sum(x[2] for x in self.tape if x[3] < 0)
        sizes = sorted(x[2] for x in self.tape)
        big = sizes[int(0.95 * (len(sizes) - 1))]
        # footprint imbalances and stacks
        levels = sorted(self.fp)
        imb = []
        med_level = st.median([sum(v) for v in self.fp.values()]) or 1
        for k in levels:
            b, s = self.fp[k]
            if b + s >= med_level:                    # ignore thin levels
                if b >= 3 * max(s, 1):
                    imb.append((k, 1))
                elif s >= 3 * max(b, 1):
                    imb.append((k, -1))
        stacks, run = [], []
        for k, sd in imb:
            if run and sd == run[-1][1] and abs(levels.index(k) - levels.index(run[-1][0])) == 1:
                run.append((k, sd))
            else:
                if len(run) >= 3:
                    stacks.append([run[0][0], run[-1][0], "buyers" if run[0][1] > 0 else "sellers"])
                run = [(k, sd)]
        if len(run) >= 3:
            stacks.append([run[0][0], run[-1][0], "buyers" if run[0][1] > 0 else "sellers"])
        out = {"prints": len(self.tape), "buy_vol": round(buy), "sell_vol": round(sell), "delta": round(buy - sell),
               "cum_delta": round(self.cum), "buy_share": round(buy / (buy + sell), 3) if buy + sell else None,
               "large_prints": [x for x in self.tape if x[2] >= big][-8:],
               "imbalances": [[k, "buy" if sd > 0 else "sell"] for k, sd in imb][-10:], "stacked": stacks[-4:],
               "depth": self.depth, "events": self.events[-8:]}
        d = self.depth
        if d.get("bid_qty5") and d.get("ask_qty5"):
            out["book_ratio5"] = round(d["bid_qty5"] / d["ask_qty5"], 2)
        if d.get("total_buy") and d.get("total_sell"):
            out["pending_ratio"] = round(d["total_buy"] / d["total_sell"], 2)
        # divergence and exhaustion on the minute path
        p = self.path
        if len(p) >= 30:
            hi_i = max(range(len(p)), key=lambda i: p[i][1])
            lo_i = min(range(len(p)), key=lambda i: p[i][1])
            recent = p[-15:]
            if hi_i >= len(p) - 15 and max(x[2] for x in recent) < max(x[2] for x in p[:-15]):
                out["divergence"] = "bearish: price at the session high, cumulative delta below its earlier peak"
            elif lo_i >= len(p) - 15 and min(x[2] for x in recent) > min(x[2] for x in p[:-15]):
                out["divergence"] = "bullish: price at the session low, cumulative delta above its earlier low"
            last10 = [p[i][2] - p[i - 1][2] for i in range(len(p) - 10, len(p))]
            if hi_i >= len(p) - 3 and sum(last10[-5:]) < 0.3 * sum(max(x, 0) for x in last10[:5] or [0]):
                out["exhaustion"] = "buying is fading at the high"
            if lo_i >= len(p) - 3 and -sum(last10[-5:]) < 0.3 * sum(-min(x, 0) for x in last10[:5] or [0]):
                out["exhaustion"] = "selling is fading at the low"
            # trapped traders: the minute with the heaviest buying made a high, price now below that minute's price
            moves = [(p[i][2] - p[i - 1][2], i) for i in range(1, len(p))]
            top = max(moves)
            bot = min(moves)
            if top[0] > 0 and p[top[1]][1] >= 0.998 * p[hi_i][1] and p[-1][1] < p[top[1]][1] * 0.995 and top[1] < len(p) - 3:
                out["trapped"] = f"buyers trapped above {p[top[1]][1]:,} (heavy buying at the high, price now below)"
            elif bot[0] < 0 and p[bot[1]][1] <= 1.002 * p[lo_i][1] and p[-1][1] > p[bot[1]][1] * 1.005 and bot[1] < len(p) - 3:
                out["trapped"] = f"sellers trapped below {p[bot[1]][1]:,} (heavy selling at the low, price now above)"
        return out
