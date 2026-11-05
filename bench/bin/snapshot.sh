#!/usr/bin/env bash
# Save a phase snapshot without staging file contents.
# `git add -N` lets `git diff` include new files while keeping the changes
# unstaged, so later phases still see them as a working-tree diff.
set -euo pipefail

BENCH="${BENCH_ROOT:-$HOME/repos/bench2}"
cell="${1:?usage: snapshot.sh <cell> <out-dir>}"
out="${2:?usage: snapshot.sh <cell> <out-dir>}"
worktree="$BENCH/$cell"
[ -d "$worktree" ] || { echo "missing worktree: $worktree" >&2; exit 2; }
mkdir -p "$out"

cd "$worktree"
git add -N . >/dev/null 2>&1 || true
git diff --binary > "$out/changes.patch"
git diff --stat > "$out/changes.stat"
git diff --numstat > "$out/changes.numstat"
git status --porcelain=v1 > "$out/git-status.txt"
