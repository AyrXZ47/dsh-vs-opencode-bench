#!/usr/bin/env python3
"""Resolve benchmark API keys from the user's OpenCode auth store.

The keys are printed only in shell-export form for `eval`; they are never
written to disk by this script. Use --debug to print names and lengths only.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess


def load_records() -> list[dict]:
    # The caller (run-cell.sh) sets XDG_* to the cell environment. The key
    # source is the user's global OpenCode store, so remove those overrides
    # for this one read-only export.
    env = dict(os.environ)
    for name in (
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_CACHE_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
    ):
        env.pop(name, None)
    raw = subprocess.check_output(["opencode", "auth", "export"], text=True, env=env)
    data = json.loads(raw)
    if not isinstance(data, list):
        raise SystemExit("unexpected auth export shape")
    return data


def pick(records: list[dict], integration: str, active: bool = True) -> str | None:
    candidates = [
        r for r in records
        if r.get("integrationID") == integration and (not active or r.get("active") is True)
    ]
    # Prefer the active subscription record when several are stored.
    candidates.sort(key=lambda r: (r.get("label") != "OpenCode Go", r.get("label", "")))
    for r in candidates:
        key = (r.get("value") or {}).get("key")
        if isinstance(key, str) and key:
            return key
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell", required=True, choices=["dsh-ds", "dsh-oc", "oc-ds", "oc-oc"])
    parser.add_argument("--format", choices=["shell", "debug"], default="shell")
    parser.add_argument("--only-missing", action="store_true")
    args = parser.parse_args()

    records = load_records()
    deepseek = pick(records, "deepseek")
    opencode_go = pick(records, "opencode-go")

    wanted: dict[str, str | None] = {}
    if args.cell in ("dsh-ds", "oc-ds"):
        wanted["DEEPSEEK_API_KEY"] = deepseek
    else:
        wanted["OPENCODE_GO_API_KEY"] = opencode_go
        # DSH's native web search uses the DeepSeek key even on the OC route.
        wanted["DEEPSEEK_API_KEY"] = deepseek

    for name, value in wanted.items():
        if value is None:
            raise SystemExit(f"missing credential for {name}")
        if args.only_missing and os.environ.get(name):
            continue
        if args.format == "debug":
            print(f"{name}: len={len(value)} prefix={value[:3]}***")
        else:
            print(f"export {name}={shlex.quote(value)}")


if __name__ == "__main__":
    main()
