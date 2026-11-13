#!/usr/bin/env bash
# Copy one talk page to the Penn web server and make it world-readable.
# Usage: bash bin/publish-talk-to-penn.sh [talk-folder-name] [source.html]
#   talk-folder-name  default: 2026-11-13-cornell-tech
#   source.html       default: this repo's talks/<talk>/index.html (the copy without speaker notes).
#                     Pass another file to publish that instead, e.g. the local deck with notes.
set -euo pipefail
talk="${1:-2026-11-13-cornell-tech}"
src="${2:-$(cd "$(dirname "$0")/.." && pwd)/talks/$talk/index.html}"
[ -f "$src" ] || { echo "Not found: $src" >&2; exit 1; }
dest="~/www/talks/$talk"
ssh ccb@eniac.seas.upenn.edu "mkdir -p $dest && chmod 755 ~/www/talks $dest && cat > $dest/index.html && chmod 644 $dest/index.html" < "$src"
echo "Copied $src"
echo "to https://www.cis.upenn.edu/~ccb/talks/$talk/"
