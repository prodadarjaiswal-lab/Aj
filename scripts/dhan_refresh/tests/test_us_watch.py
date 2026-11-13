import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import us_watch as U  # noqa: E402

CFG = {"NVDA": {"name": "Nvidia", "below": [150, 135], "above": [180], "move_pct": 3, "why": {"150": "Buy level"}}}


def q(p, prev=166.19):
    return {"price": p, "prev": prev, "high": max(p, prev), "low": min(p, prev), "t": 0}


import struct  # noqa: E402


def pkt(code, sid, body):
    n = 11 + len(body)
    return struct.pack("<BiiBB", 1, sid, sid, n, code) + body


def test_parse_dhan_packets():
    buf = (pkt(1, 777, struct.pack("<fiii", 161.88, 1000, 1794595674, 1794595675)) +
           pkt(3, 777, struct.pack("<ffff", 169.89, 161.5, 170.0, 158.39)) +
           pkt(32, 777, struct.pack("<f", 166.19)))
    p = U.parse(buf)
    assert [x["k"] for x in p] == ["trade", "ohlc", "prev"]
    assert abs(p[0]["ltp"] - 161.88) < 1e-3 and p[0]["sid"] == "777"
    assert abs(p[1]["high"] - 170.0) < 1e-3 and abs(p[2]["prev"] - 166.19) < 1e-3
    e = U.parse(pkt(50, 0, struct.pack("<h", 806)))
    assert e[0]["k"] == "error" and e[0]["code"] == 806


class FakeWS:
    def __init__(self, msgs):
        self.msgs = list(msgs)

    def recv(self, timeout=None):
        if not self.msgs:
            raise TimeoutError
        return self.msgs.pop(0)


def test_feed_builds_quote_and_raises_on_error():
    f = U.DhanUS("1", "t", {"NVDA": "777"})
    f.ws = FakeWS([pkt(32, 777, struct.pack("<f", 166.19)) + pkt(1, 777, struct.pack("<fiii", 161.88, 1, 0, 0)),
                   pkt(3, 777, struct.pack("<ffff", 169.89, 161.5, 170.0, 158.39))])
    f.pump(0.2)
    q = f.q["NVDA"]
    assert round(q["price"], 2) == 161.88 and round(q["prev"], 2) == 166.19 and round(q["low"], 2) == 158.39
    assert "-2.59%" in U.line("NVDA", {"name": "Nvidia"}, q)
    f.ws = FakeWS([pkt(50, 0, struct.pack("<h", 807))])
    try:
        f.pump(0.2)
        assert False
    except U.DhanError as e:
        assert "807" in str(e)


def test_levels_and_moves_fire_once():
    w = U.Watch(CFG)
    assert w.check("NVDA", q(162), "x") == []                 # -2.5%: nothing
    m = w.check("NVDA", q(160), "x")
    assert len(m) == 1 and "-3.7%" in m[0]                    # first 3% step
    m = w.check("NVDA", q(149), "x")
    assert any("$150" in x and "Buy level" in x for x in m) and any("-10.3%" in x for x in m)
    assert w.check("NVDA", q(149.5), "x") == []               # no repeats
    m = U.Watch(CFG).check("NVDA", q(181, 175), "x")
    assert any("$180" in x for x in m)


def test_restart_keeps_sent():
    w = U.Watch(CFG, ["NVDA:below:150", "NVDA:move:-9"])
    assert w.check("NVDA", q(149), "x") == []


def test_config_file_is_valid():
    c = U.config()
    assert "NVDA" in c and all(isinstance(x, (int, float)) for x in c["NVDA"]["below"])


def test_security_ids_from_dhan_list(monkeypatch):
    csv_text = ("EXCHANGE,SEGMENT,SCRIP_CODE,ISIN_CODE,SYMBOL,SYMBOL_NAME,EXCH_SYMBOL\n"
                "NASDAQ,E,4242,US67066G1040,NVDA,NVIDIA CORP,NVDA\n"
                "NYSE,E,99,US0000000000,NVD,OTHER,NVD\n")

    class R:
        text = csv_text
    monkeypatch.setattr(U.requests, "get", lambda *a, **k: R())
    assert U.security_ids(["NVDA"]) == {"NVDA": "4242"}
