"""Copy the bot's journal (branch 'bot') to docs/journal.md so the pinned chat can read it."""
from __future__ import annotations

import collections
import sys
from pathlib import Path

import bot as B


def render(j: list) -> str:
    L = ["# Stock journal", "", "Every stock asked about in the Telegram bot, newest first. Price is the live price when asked (blank outside market hours).", ""]
    cnt = collections.Counter(x["sym"] for x in j)
    if cnt:
        L += ["## Most asked", "", ", ".join(f"{s} ({n})" for s, n in cnt.most_common(15)), ""]
    L += ["## Log", "", "| When (IST) | Stock | Asked | Price | Bot said |", "|---|---|---|---|---|"]
    for x in reversed(j):
        said = str(x.get("said", "")).replace("|", "/")
        L.append(f"| {x['t']} | {x['sym']} | {x['cmd']} | {x.get('price') or ''} | {said} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../..")
    (root / "docs/journal.md").write_text(render(B.load_state().get("journal", [])), encoding="utf-8")
    print("journal written")
