"""Delete the owner's Telegram chat history with the bot, then re-pin the desk links.

Telegram lets a bot delete both its own and the user's messages in a private chat, but only messages
less than 48 hours old; older ones stay until the owner uses "Clear history" in the Telegram app.
Message ids in a chat are sequential, so the script sends one marker message to learn the latest id and
deletes downwards in batches of 100 (deleteMessages skips ids that cannot be deleted).
"""
from __future__ import annotations

import sys

import telegram as T


def main() -> int:
    if not T.enabled():
        print("telegram not set up")
        return 1
    m = T.call("sendMessage", chat_id=T.chat_id(), text="Clearing this chat…")
    top = m["message_id"]
    lo = max(1, top - int(sys.argv[sys.argv.index("--depth") + 1]) if "--depth" in sys.argv else top - 5000)
    batches = ok = 0
    for start in range(top, lo - 1, -100):
        ids = list(range(max(lo, start - 99), start + 1))
        try:
            T.call("deleteMessages", chat_id=T.chat_id(), message_ids=ids)
            ok += 1
        except Exception as e:
            print(f"  batch {ids[0]}-{ids[-1]}: {str(e)[:120]}")
        batches += 1
    print(f"deleteMessages: {ok} of {batches} batches accepted (ids {lo}-{top})")
    import bot as B
    print(B.pin_links())
    return 0


if __name__ == "__main__":
    sys.exit(main())
