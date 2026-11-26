#!/usr/bin/env bash
# Build the terminal page and send its data to aj-live branch "page" (see page_feed.py).
# Needs PUBLIC_LIVE_TOKEN (Contents read/write on aj-live) and optionally PUBLIC_LIVE_REPO.
set -euo pipefail
REPO="${PUBLIC_LIVE_REPO:-prodadarjaiswal-lab/aj-live}"
[ -n "${PUBLIC_LIVE_TOKEN:-}" ] || { echo "::error::PUBLIC_LIVE_TOKEN missing: page data not sent"; exit 1; }
TMP="${RUNNER_TEMP:-/tmp}"
rm -rf "$TMP/site" "$TMP/feed"
cd "$(dirname "$0")"
python terminal_page.py --site "$TMP/site" > /dev/null
python page_feed.py push "$TMP/site" "$TMP/feed"
cd "$TMP/feed"
git init -q -b page && git add -A
git -c user.name="aj-bot" -c user.email="aj-bot@users.noreply.github.com" commit -q -m "Page data $(TZ=Asia/Kolkata date '+%F %H:%M') IST"
# one commit, replaced each night, so aj-live does not grow
git push -q -f "https://x-access-token:${PUBLIC_LIVE_TOKEN}@github.com/${REPO}.git" page
echo "page data sent to $REPO@page: $(head -c 100 manifest.json)"
