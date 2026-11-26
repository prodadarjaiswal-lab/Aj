import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import page_feed  # noqa: E402

PAGE = ('<meta charset="utf-8"><script>const D=/*DATA*/{"today":{"asof":"2026-11-26"}}/*DATA*/||{};'
        'window.LAB=/*LAB*/{"a":1}/*LAB*/;const X="/*NOTE*/not json/*NOTE*/";'
        'fetch("d/"+n+".json")</script>')


def test_inject_wraps_blobs_and_adds_boot():
    h = page_feed.inject(PAGE, "2026-11-26 22:00")
    assert h.index("page_feed boot") < h.index("const D=")
    assert '(window.__AJ&&window.__AJ["DATA"])||/*DATA*/' in h
    assert '(window.__AJ&&window.__AJ["LAB"])||/*LAB*/' in h
    assert '"/*NOTE*/not json/*NOTE*/"' in h               # not JSON: left alone
    assert "window.ajFetchChunk(n)" in h
    assert page_feed.built_of(h) == "2026-11-26 22:00"
    assert page_feed.inject(h) == h                          # idempotent


def test_push_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(page_feed, "PIECE", 10)
    site, out = tmp_path / "site", tmp_path / "feed"
    (site / "d").mkdir(parents=True)
    (site / "index.html").write_text(page_feed.inject(PAGE, "2026-11-26 22:00"))
    (site / "d" / "A.json").write_text(json.dumps({"ABB": {"p": [1, 2, 3]}}))
    r = page_feed.push(site, out)
    assert r["built"] == "2026-11-26 22:00" and r["asof"] == "2026-11-26" and r["blobs"] == 2 and r["chunks"] == 1
    man = json.loads((out / "manifest.json").read_text())

    def join(names):
        parts = []
        for n in names:
            t = (out / n).read_text()
            assert t.startswith(page_feed.HEAD) and t.endswith(page_feed.TAIL)
            parts.append(t[len(page_feed.HEAD):-len(page_feed.TAIL)])
        return "".join(parts)
    assert json.loads(join(man["blobs"]["DATA"])) == {"today": {"asof": "2026-11-26"}}
    assert len(man["chunks"]["A"]) > 1 and json.loads(join(man["chunks"]["A"])) == {"ABB": {"p": [1, 2, 3]}}
