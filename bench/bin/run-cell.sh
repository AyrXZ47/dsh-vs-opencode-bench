#!/usr/bin/env bash
# Run one benchmark phase for one cell inside the outer bubblewrap sandbox.
#
# Usage: run-cell.sh <dsh-ds|dsh-oc|oc-ds|oc-oc> <fase1-webapp|fase2-render3d|fase3-ledger|fase4-research|fase5-skills>
set -euo pipefail

BENCH="${BENCH_ROOT:-$HOME/repos/bench2}"
HARNESS="${HARNESS_ROOT:-$HOME/bench2-harness}"
cell="${1:?usage: run-cell.sh <cell> <phase>}"
phase="${2:?usage: run-cell.sh <cell> <phase>}"

case "$cell" in
  dsh-ds|dsh-oc) kind=dsh ;;
  oc-ds|oc-oc) kind=oc ;;
  *) echo "unknown cell: $cell" >&2; exit 2 ;;
esac

worktree="$BENCH/$cell"
root="$BENCH/env-$cell"
vault="$worktree/.bench-vault"
task_src="$HARNESS/tasks/$phase.md"
[ -d "$worktree" ] || { echo "missing worktree: $worktree" >&2; exit 2; }
[ -d "$root" ] || { echo "missing env: $root" >&2; exit 2; }
[ -f "$task_src" ] || { echo "missing task: $task_src" >&2; exit 2; }

stamp="$(date +%Y%m%d-%H%M%S)"
out="$HARNESS/results/$cell/$phase-$stamp"
mkdir -p "$out"

task_text="$(cat "$task_src")"
task_text="${task_text//'{{VAULT}}'/$vault}"
task_text="${task_text//'{{CELL}}'/${cell^^}}"
printf '%s\n' "$task_text" > "$out/task.md"

# Optional user-provided overrides. No keys are required here: keys.py reads
# the existing OpenCode auth store into the process environment.
unset DEEPSEEK_BASE_URL OPENCODE_GO_BASE_URL
if [ -f "$HARNESS/secrets.env" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$HARNESS/secrets.env"
  set +a
fi

export XDG_CONFIG_HOME="$root/config"
export XDG_DATA_HOME="$root/data"
export XDG_CACHE_HOME="$root/cache"
export XDG_STATE_HOME="$root/state"
export XDG_RUNTIME_DIR="$root/run"
export CARGO_HOME="$root/cargo"
export UV_CACHE_DIR="$root/uv-cache"
export UV_TOOL_DIR="$root/uv-tools"
export UV_PYTHON_INSTALL_DIR="$root/uv-python"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME" "$XDG_STATE_HOME" \
         "$XDG_RUNTIME_DIR" "$CARGO_HOME" "$UV_CACHE_DIR" "$UV_TOOL_DIR" "$UV_PYTHON_INSTALL_DIR"
chmod 700 "$XDG_RUNTIME_DIR" 2>/dev/null || true

cmd=()
provider=""
model=""
pricing=""

if [ "$kind" = dsh ]; then
  eval "$(python3 "$HARNESS/tools/keys.py" --cell "$cell" --format shell --only-missing)"
  export DSH_HOME="$root/dsh-home"
  export DSH_PERMISSION_MODE=danger-full-access
  cp "$HARNESS/patches/outer-sandbox.yml" "$root/outer-sandbox.yml"
  if [ "$cell" = dsh-ds ]; then
    : "${DEEPSEEK_API_KEY:?missing DEEPSEEK_API_KEY}"
    unset OPENCODE_GO_API_KEY
    if [ -n "${DEEPSEEK_BASE_URL:-}" ]; then export DEEPSEEK_BASE_URL; else unset DEEPSEEK_BASE_URL; fi
    provider="deepseek-official"
    model="deepseek-flash"
    pricing="direct"
  else
    : "${OPENCODE_GO_API_KEY:?missing OPENCODE_GO_API_KEY}"
    : "${DEEPSEEK_API_KEY:?missing DEEPSEEK_API_KEY for web search}"
    if [ -n "${OPENCODE_GO_BASE_URL:-}" ]; then export OPENCODE_GO_BASE_URL; else unset OPENCODE_GO_BASE_URL; fi
    unset DEEPSEEK_BASE_URL
    provider="opencode-go"
    model="deepseek-v4.1-flash"
    pricing="oc"
  fi
  cmd=(dsh headless --patch "$root/outer-sandbox.yml" --json "$task_text")
else
  if [ "$cell" = oc-ds ]; then
    model_flag="deepseek/deepseek-flash#max"
    provider="deepseek"
    model="deepseek-flash"
    pricing="direct"
  else
    model_flag="opencode-go/deepseek-v4.1-flash#max"
    provider="opencode-go"
    model="deepseek-v4.1-flash"
    pricing="oc"
  fi
  cmd=(opencode run --standalone --auto --format json -m "$model_flag" "$task_text")
fi

if [ "$phase" = fase5-skills ]; then
  "$HARNESS/bin/check-dotpm.sh" "$cell" || {
    echo "dotpm test vault is not ready for $cell; aborting phase 5" >&2
    exit 1
  }
fi

"$HARNESS/bin/reset-cell.sh" "$cell"
cd "$worktree"
git rev-parse HEAD > "$out/git-head.txt"
git status --porcelain > "$out/git-status-before.txt"

started="$(date -Iseconds)"
start_ms="$(date +%s%3N)"

set +e
timeout "${RUN_TIMEOUT:-3600}" "$HARNESS/bin/sandbox-run.sh" "$cell" "${cmd[@]}" \
  > "$out/events.jsonl" 2> "$out/stderr.log"
model_exit=$?
set -e

finished="$(date -Iseconds)"
end_ms="$(date +%s%3N)"
wall_ms=$((end_ms - start_ms))

git status --porcelain > "$out/git-status-after.txt"
git diff --stat > "$out/git-diff-stat-after.txt" 2>/dev/null || true

"$HARNESS/bin/snapshot.sh" "$cell" "$out" || true
python3 "$HARNESS/tools/collect.py" \
  --kind "$kind" \
  --events "$out/events.jsonl" \
  --out-dir "$out" \
  --cell "$cell" \
  --pricing "$pricing" \
  --wall-ms "$wall_ms" \
  --exit-code "$model_exit" \
  --started "$started" \
  --finished "$finished" \
  --provider "$provider" \
  --model "$model" > "$out/collect.out"

cat "$out/collect.out"
python3 "$HARNESS/graders/grade.py" \
  --phase "$phase" \
  --cell "$cell" \
  --worktree "$worktree" \
  --out "$out" \
  --vault "$vault" || true

echo "result_dir=$out"
echo "model_exit=$model_exit"
