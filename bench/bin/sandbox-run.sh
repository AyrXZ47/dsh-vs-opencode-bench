#!/usr/bin/env bash
# Run one command inside the benchmark bubblewrap sandbox.
#
# Usage: sandbox-run.sh <cell> <command...>
#
# The sandbox exposes:
#   - the current worktree and the current env dir, writable
#   - the seed repo read-only (the worktree's .git file points into it)
#   - the pnpm/uv caches, writable, for MCP servers
#   - /tmp writable
# and hides:
#   - the real Obsidian vault, real DSH store, global OpenCode config/data
#   - the benchmark harness (tasks, hidden tests, results, reference)
#   - the other benchmark cells, the base vault, the old seed backup
#   - /run/user/1000 (the real Obsidian CLI socket)
set -euo pipefail

BENCH="${BENCH_ROOT:-$HOME/repos/bench2}"
HARNESS="${HARNESS_ROOT:-$HOME/bench2-harness}"
cell="${1:?usage: sandbox-run.sh <cell> <command...>}"
shift

case "$cell" in
  dsh-ds|dsh-oc|oc-ds|oc-oc) ;;
  *) echo "unknown cell: $cell" >&2; exit 2 ;;
esac

WORKTREE="$BENCH/$cell"
ROOT="$BENCH/env-$cell"
[ -d "$WORKTREE" ] || { echo "missing worktree: $WORKTREE" >&2; exit 2; }
[ -d "$ROOT" ] || { echo "missing env: $ROOT" >&2; exit 2; }

BWRAP="${BWRAP:-}"
if [ -z "$BWRAP" ]; then
  BWRAP="$(command -v bwrap || true)"
fi
if [ -z "$BWRAP" ]; then
  BWRAP="$(find /nix/store -maxdepth 3 -type f -name bwrap 2>/dev/null | head -n 1)"
fi
[ -n "$BWRAP" ] || { echo "bubblewrap not found" >&2; exit 2; }

EMPTY="$(mktemp -d /tmp/bench-bwrap-empty.XXXXXX)"
trap 'rm -rf "$EMPTY"' EXIT

mkdir -p \
  "$HOME/.cache/pnpm" "$HOME/.cache/uv" \
  "$HOME/.local/share/uv" "$HOME/.local/share/pnpm" \
  "$ROOT/run" "$ROOT/cargo" "$ROOT/uv-cache" "$ROOT/uv-tools" "$ROOT/uv-python"
chmod 700 "$ROOT/run" 2>/dev/null || true

args=(
  --die-with-parent
  --unshare-pid
  --ro-bind / /
  --dev /dev
  --proc /proc
  --tmpfs /dev/shm
  --tmpfs "$BENCH"
  --dir "$BENCH/seed"
  --ro-bind "$BENCH/seed" "$BENCH/seed"
  --dir "$WORKTREE"
  --bind "$WORKTREE" "$WORKTREE"
  --dir "$ROOT"
  --bind "$ROOT" "$ROOT"
  --tmpfs /tmp
  --ro-bind "$EMPTY" "$HOME/Sync/Notes"
  --ro-bind "$EMPTY" "$HOME/.dsh"
  --ro-bind "$EMPTY" "$HOME/.config/opencode"
  --ro-bind "$EMPTY" "$HOME/.local/share/opencode"
  --ro-bind "$EMPTY" "$HOME/.config/obsidian"
  --ro-bind "$EMPTY" "$HARNESS"
  --ro-bind "$EMPTY" "/run/user/1000"
  --bind "$HOME/.cache/pnpm" "$HOME/.cache/pnpm"
  --bind "$HOME/.cache/uv" "$HOME/.cache/uv"
  --bind "$HOME/.local/share/uv" "$HOME/.local/share/uv"
  --bind "$HOME/.local/share/pnpm" "$HOME/.local/share/pnpm"
)

for secret_dir in "$HOME/.ssh" "$HOME/.gnupg" "$HOME/.aws" "$HOME/.kube" \
                  "$HOME/.config/sops" "$HOME/.config/age" "$HOME/.config/gh" \
                  "$HOME/.docker"; do
  if [ -d "$secret_dir" ]; then
    args+=(--ro-bind "$EMPTY" "$secret_dir")
  fi
done

args+=(--chdir "$WORKTREE")
exec "$BWRAP" "${args[@]}" "$@"
