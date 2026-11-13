"""Send messages to the owner's Telegram chat.

The bot token comes from the TELEGRAM_BOT_TOKEN secret. The chat id is found once
by `python telegram.py setup` (the owner taps Start in the bot first) and saved in
config/telegram.json, so nothing else needs to be configured.
"""
from __future__ import annotations

import html
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
CONF = ROOT / "config" / "telegram.json"
API = "https://api.telegram.org/bot{token}/{method}"


def _token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()


def chat_id() -> str:
    if os.environ.get("TELEGRAM_CHAT_ID"):
        return os.environ["TELEGRAM_CHAT_ID"].strip()
    if CONF.exists():
        return str(json.loads(CONF.read_text()).get("chat_id", ""))
    return ""


def enabled() -> bool:
    return bool(_token() and chat_id())


def esc(s) -> str:
    return html.escape(str(s), quote=False)


def call(method: str, **params) -> dict:
    r = requests.post(API.format(token=_token(), method=method), json=params, timeout=20)
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method} failed ({r.status_code}): {str(data.get('description', r.text))[:200]}")
    return data["result"]


def send(text: str) -> bool:
    """Send one HTML message (split if over Telegram's 4096-character limit). Never raises."""
    if not enabled():
        print("telegram: not set up, message skipped")
        return False
    try:
        parts, cur = [], ""
        for line in text.split("\n"):
            if len(cur) + len(line) + 1 > 3900:
                parts.append(cur)
                cur = ""
            cur += line + "\n"
        parts.append(cur)
        for p in parts:
            if p.strip():
                call("sendMessage", chat_id=chat_id(), text=p, parse_mode="HTML", disable_web_page_preview=True)
        return True
    except Exception as e:  # alerts must never stop the price feed
        print(f"telegram: {str(e)[:200]}")
        return False


def setup() -> int:
    """Find the chat that pressed Start, save its id, and send a test message."""
    if not _token():
        print("TELEGRAM_BOT_TOKEN secret is missing. Add it in GitHub: Settings > Secrets and variables > Actions.")
        return 1
    me = call("getMe")
    print(f"bot: @{me.get('username')}")
    chats = {}
    for u in call("getUpdates", timeout=0):
        m = u.get("message") or {}
        c = m.get("chat") or {}
        if c.get("type") == "private" and str(m.get("text", "")).startswith("/start"):
            chats[c["id"]] = c.get("first_name", "")
    if not chats:
        print(f"No one has pressed Start yet. Open @{me.get('username')} in Telegram, tap Start, then run this again.")
        return 1
    if len(chats) > 1:
        print(f"{len(chats)} chats pressed Start; using the first one.")
    cid = next(iter(chats))
    CONF.parent.mkdir(exist_ok=True)
    CONF.write_text(json.dumps({"chat_id": cid, "bot": me.get("username")}, indent=1) + "\n")
    os.environ["TELEGRAM_CHAT_ID"] = str(cid)
    send("<b>NSE alerts connected.</b>\nYou will get a brief before the open, alerts during the session, and a summary after the close, on trading days.")
    print(f"saved chat id to {CONF.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["setup"]:
        sys.exit(setup())
    if sys.argv[1:2] == ["test"]:
        sys.exit(0 if send(" ".join(sys.argv[2:]) or "Test message from your NSE alerts bot.") else 1)
    print("usage: telegram.py setup | test [text]")
