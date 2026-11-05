#!/usr/bin/env bash
# Verify that the dotpm local API for a cell's test vault is reachable and
# that the Benchmark project is indexed.
set -euo pipefail

BENCH="${BENCH_ROOT:-$HOME/repos/bench2}"
cell="${1:?usage: check-dotpm.sh <cell>}"
vault="$BENCH/$cell/.bench-vault"

status="$(timeout 15 dotpm status --vault "$vault" 2>/dev/null || true)"
projects="$(timeout 20 dotpm projects --vault "$vault" 2>/dev/null || true)"

python3 - "$vault" "$status" "$projects" <<'PY'
import json, sys
vault, status_raw, projects_raw = sys.argv[1], sys.argv[2], sys.argv[3]
def first_json(raw):
    raw = raw.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        start = raw.find("{")
        if start == -1:
            start = raw.find("[")
        end = raw.rfind("}")
        if end == -1:
            end = raw.rfind("]")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end+1])
            except Exception:
                return None
    return None
status = first_json(status_raw)
projects = first_json(projects_raw)
ok = bool(isinstance(status, dict) and status.get("ok") is True and vault in status.get("source", ""))
bench = [p for p in projects if isinstance(p, dict) and "Bench 2" in p.get("title", "")] if isinstance(projects, list) else []
print(json.dumps({"vault": vault, "status_ok": ok, "benchmark_projects": bench}, ensure_ascii=False))
if not ok or not bench:
    raise SystemExit(1)
PY
