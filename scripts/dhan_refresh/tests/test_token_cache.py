import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import token_cache as TC  # noqa: E402


def test_seal_roundtrip_and_tamper():
    b = TC.seal("eyJ.token.value", "123456", "ABCDEFGH234567")
    assert "eyJ" not in str(b) and TC.unseal(b, "123456", "abcdefgh234567") == "eyJ.token.value"
    assert TC.unseal(b, "654321", "ABCDEFGH234567") is None                  # wrong secrets
    bad = dict(b, issued=b["issued"] + 1)
    assert TC.unseal(bad, "123456", "ABCDEFGH234567") is None                # tampered


def test_disabled_outside_actions(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    assert TC.read("1", "A") is None
    TC.write("x", "1", "A")                                                  # no git calls, no error
