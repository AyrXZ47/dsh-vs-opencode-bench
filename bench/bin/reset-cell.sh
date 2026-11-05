#!/usr/bin/env bash
# Reset a cell's worktree to the seed commit. Keeps ignored files:
# .bench-vault/ (the test vault) and build targets.
set -euo pipefail

BENCH="${BENCH_ROOT:-$HOME/repos/bench2}"
cell="${1:?usage: reset-cell.sh <cell>}"
worktree="$BENCH/$cell"
[ -d "$worktree" ] || { echo "missing worktree: $worktree" >&2; exit 2; }

cd "$worktree"
git reset --hard HEAD >/dev/null
git clean -fd >/dev/null

# Remove generated artifacts but keep the test vault (ignored).
find . -path './.bench-vault' -prune -o -name '__pycache__' -type d -print0 \
  | xargs -0 -r rm -rf
find . -path './.bench-vault' -prune -o \
  \( -name '*.db' -o -name '*.db-wal' -o -name '*.db-shm' -o -name '*.ppm' -o -name '*.pyc' \) \
  -type f -print0 | xargs -0 -r rm -f

case "$cell" in
  dsh-*)
    root="$BENCH/env-$cell/dsh-home"
    rm -rf "$root/sessions" "$root/storages"
    mkdir -p "$root/sessions" "$root/storages"
    ;;
esac

echo "reset $cell"
