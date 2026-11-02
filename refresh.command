#!/bin/bash
# Shelf Pulse - one-shot data refresh.
# Scrapes live Blinkit data (needs a residential IP - run on your Mac),
# regenerates the static site data, and pushes to GitHub so
# snishantflick2know.github.io/Private-Darkstore-quick-commerce/ updates.
#
# Run it either by double-clicking this file in Finder, or:
#   cd "/Users/nishant/Desktop/DArk Store-quic commerce/haldiram_oos_tracker" && ./refresh.command

cd "$(dirname "$0")" || exit 1
source .venv/bin/activate

python3 scripts/export_static_site.py || { echo "Scrape/export failed - see output above."; exit 1; }

# Push only if the scrape actually changed something (timestamps change
# every run, so there is almost always a diff - but don't fail on an
# empty one).
git add data/stock_tracker.db docs/data
if git diff --cached --quiet; then
  echo "Nothing new to commit - data unchanged."
else
  git commit -m "Manual data refresh (local scrape)" -m "Generated with Devin (https://devin.ai)" -m "Co-Authored-By: Devin <158243242+devin-ai-integration[bot]@users.noreply.github.com>" >/dev/null
  # "-X theirs" auto-resolves conflicts in favor of the fresh local commit
  # (in a rebase, "theirs" = the local commit being replayed) so a scheduled
  # auto-commit on the remote can't stall the push the way it did before.
  git pull --rebase -X theirs || { echo "Sync with remote failed - run this file again or ask for help."; exit 1; }
  git push || { echo "Push failed - see output above."; exit 1; }
  echo "Pushed. Live site updates within ~10 min (hard-refresh to see it sooner)."
fi
