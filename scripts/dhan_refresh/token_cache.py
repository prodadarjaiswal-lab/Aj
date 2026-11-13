"""One Dhan login shared by every job for up to 23 hours.

Dhan allows one valid token per account and a new login cancels the old one, so
jobs that each logged in used to knock each other out. Now the token is kept,
encrypted, on the private 'dhan-token' branch. Each job reuses it while Dhan still
accepts it, and only logs in when it has expired or been revoked.

Encryption: a keystream from SHA-256 over a key derived from DHAN_TOTP_SECRET and
DHAN_PIN (which only the repository's Actions secrets hold), with an HMAC-SHA256
tag. Without those secrets the stored file is useless.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRANCH = "dhan-token"
MAX_AGE = 23 * 3600


def _keys(pin: str, sec: str) -> tuple:
    base = hashlib.sha256(f"dhan-token|{sec.strip().upper()}|{pin.strip()}".encode()).digest()
    return hashlib.sha256(base + b"enc").digest(), hashlib.sha256(base + b"mac").digest()


def _stream(key: bytes, nonce: bytes, n: int) -> bytes:
    out, i = b"", 0
    while len(out) < n:
        out += hashlib.sha256(key + nonce + i.to_bytes(4, "big")).digest()
        i += 1
    return out[:n]


def seal(token: str, pin: str, sec: str, issued: float | None = None) -> dict:
    ek, mk = _keys(pin, sec)
    nonce = os.urandom(16)
    pt = token.encode()
    ct = bytes(a ^ b for a, b in zip(pt, _stream(ek, nonce, len(pt))))
    issued = issued or time.time()
    mac = hmac.new(mk, nonce + ct + str(int(issued)).encode(), hashlib.sha256).hexdigest()
    return {"v": 1, "issued": int(issued), "nonce": base64.b64encode(nonce).decode(), "ct": base64.b64encode(ct).decode(), "mac": mac}


def unseal(blob: dict, pin: str, sec: str) -> str | None:
    try:
        ek, mk = _keys(pin, sec)
        nonce, ct = base64.b64decode(blob["nonce"]), base64.b64decode(blob["ct"])
        good = hmac.new(mk, nonce + ct + str(int(blob["issued"])).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(good, blob["mac"]):
            return None
        return bytes(a ^ b for a, b in zip(ct, _stream(ek, nonce, len(ct)))).decode()
    except Exception:
        return None


def _enabled() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def read(pin: str, sec: str) -> str | None:
    if not _enabled():
        return None
    try:
        subprocess.run(["git", "-C", str(ROOT), "fetch", "-q", "origin", BRANCH], check=True, capture_output=True, timeout=60)
        blob = json.loads(subprocess.run(["git", "-C", str(ROOT), "show", "FETCH_HEAD:token.json"],
                                         check=True, capture_output=True, text=True).stdout)
        if time.time() - blob.get("issued", 0) > MAX_AGE:
            return None
        return unseal(blob, pin, sec)
    except Exception:
        return None


def write(token: str, pin: str, sec: str) -> None:
    if not _enabled():
        return
    out = ROOT / "token-out"
    try:
        run = lambda *a: subprocess.run(["git", "-C", str(out), *a], check=True, capture_output=True, timeout=60)
        if not (out / ".git").exists():
            out.mkdir(exist_ok=True)
            url = subprocess.run(["git", "-C", str(ROOT), "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
            hdr = subprocess.run(["git", "-C", str(ROOT), "config", "--get-all", "http.https://github.com/.extraheader"],
                                 capture_output=True, text=True).stdout.strip()
            run("init", "-q")
            run("remote", "add", "origin", url)
            if hdr:
                run("config", "http.https://github.com/.extraheader", hdr)
            run("config", "user.name", "dhan-live-bot")
            run("config", "user.email", "dhan-live-bot@users.noreply.github.com")
            run("checkout", "-q", "--orphan", BRANCH)
        (out / "token.json").write_text(json.dumps(seal(token, pin, sec)), encoding="utf-8")
        run("add", "token.json")
        run("commit", "-q", "--allow-empty", "-m", "Dhan session (encrypted)")
        run("push", "-q", "-f", "origin", f"HEAD:refs/heads/{BRANCH}")
    except Exception as e:
        print(f"  token not shared: {str(e)[:80]}")
