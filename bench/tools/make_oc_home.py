#!/usr/bin/env python3
"""Create the two isolated OpenCode environments for the PC benchmark.

Cells:
  oc-ds : OpenCode harness + DeepSeek official API (deepseek/deepseek-flash)
  oc-oc : OpenCode harness + OpenCode Go gateway (opencode-go/deepseek-v4.1-flash)

Each cell gets its own XDG_CONFIG_HOME, XDG_DATA_HOME, XDG_CACHE_HOME and
XDG_STATE_HOME. Credentials are exported from the user's global OpenCode store
and imported into the cell's private --standalone store; nothing is shared with
the background OpenCode service. The global store is never modified.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

BENCH = Path(os.environ.get("BENCH_ROOT", Path.home() / "repos" / "bench2"))
REAL_CONFIG = Path(os.environ.get("OPENCODE_SOURCE_CONFIG", Path.home() / ".config" / "opencode"))
REAL_VAULT = Path(os.environ.get("REAL_VAULT", Path.home() / "Sync" / "Notes"))
SKILLS = ("dotpm", "ponytail", "security-audit", "vault")

CELLS = {
    "oc-ds": {
        "worktree": BENCH / "oc-ds",
        "vault": BENCH / "oc-ds" / ".bench-vault",
        "provider": "deepseek",
        "model": "deepseek-flash",
        "variant": "max",
    },
    "oc-oc": {
        "worktree": BENCH / "oc-oc",
        "vault": BENCH / "oc-oc" / ".bench-vault",
        "provider": "opencode-go",
        "model": "deepseek-v4.1-flash",
        "variant": "max",
    },
}

HEADER = """\
# Benchmark OpenCode (PC) — instrucciones de la celda

- Worktree de esta sesión: `{worktree}`
- Vault de prueba permitido: `{vault}`
- No leas ni escribas en `~/Sync/Notes` (vault real) durante esta prueba.
- No uses subagentes ni worktrees anidados: resolvé la tarea en esta única
  sesión.
- No hagas commits: dejá los cambios en el working tree para el snapshot.
- El MCP `dotpm` apunta al vault de prueba. Si no responde, no inventes un
  backlog paralelo; reportalo.

"""

MCP_DUCKDUCKGO = {
    "command": [
        "uvx",
        "duckduckgo-mcp-server",
    ],
    "timeout": {"startup": 120000},
    "type": "local",
}


def copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, symlinks=False, dirs_exist_ok=True)
    subprocess.run(["chmod", "-R", "u+w", str(dst)], check=False)


def replace_text_in_tree(root: Path, old: str, new: str) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if old in text:
            path.chmod(path.stat().st_mode | 0o200)
            path.write_text(text.replace(old, new), encoding="utf-8")


def make_config(cell: str, meta: dict, root: Path) -> None:
    config = root / "config" / "opencode"
    config.mkdir(parents=True, exist_ok=True)

    opencode = {
        "$schema": "https://opencode.ai/config.json",
        "model": {
            "model": meta["model"],
            "providerID": meta["provider"],
            "variant": meta["variant"],
        },
        "mcp": {
            "servers": {
                "context7": {
                    "type": "remote",
                    "url": "https://mcp.context7.com/mcp",
                },
                "gh_grep": {
                    "type": "remote",
                    "url": "https://mcp.grep.app",
                },
                "duckduckgo": dict(MCP_DUCKDUCKGO),
                "dotpm": {
                    "command": [
                        "dotpm",
                        "mcp",
                        "--vault",
                        str(meta["vault"]),
                    ],
                    "timeout": {"startup": 180000},
                    "type": "local",
                },
            }
        },
        "experimental": {"todo": True},
        "websearch": False,
    }
    (config / "opencode.json").write_text(
        json.dumps(opencode, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    cli = {
        "$schema": "https://opencode.ai/v2/cli.json",
        "session": {"permissions": "autoaccept"},
        "animations": False,
        "diffs": {"wrap": "word"},
    }
    (config / "cli.json").write_text(
        json.dumps(cli, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Global AGENTS with the test-vault path and a per-cell header.
    agents_src = REAL_CONFIG / "AGENTS.md"
    agents = agents_src.read_text(encoding="utf-8")
    agents = agents.replace("~/Sync/Notes", str(meta["vault"]))
    agents = agents.replace(str(REAL_VAULT), str(meta["vault"]))
    agents = HEADER.format(worktree=meta["worktree"], vault=meta["vault"]) + agents
    (config / "AGENTS.md").write_text(agents, encoding="utf-8")

    # Skills, with the test-vault path substituted.
    for skill in SKILLS:
        src = REAL_CONFIG / "skills" / skill
        dst = config / "skills" / skill
        copy_tree(src, dst)
    replace_text_in_tree(config / "skills", "~/Sync/Notes", str(meta["vault"]))
    replace_text_in_tree(config / "skills", str(REAL_VAULT), str(meta["vault"]))

    # An isolated anonymous identity is not required by OpenCode, but keeping
    # the cell directory unique makes cleanup and auditing obvious.
    (config / ".bench-cell").write_text(cell + "\n", encoding="utf-8")


def import_auth(root: Path) -> None:
    data = root / "data"
    config = root / "config"
    cache = root / "cache"
    state = root / "state"
    for d in (data, config, cache, state):
        d.mkdir(parents=True, exist_ok=True)

    # Export in memory, never to a file on disk.
    exported = subprocess.check_output(["opencode", "auth", "export"], text=True)
    env = dict(os.environ)
    env.update(
        {
            "XDG_CONFIG_HOME": str(config),
            "XDG_DATA_HOME": str(data),
            "XDG_CACHE_HOME": str(cache),
            "XDG_STATE_HOME": str(state),
        }
    )
    result = subprocess.run(
        ["opencode", "auth", "import", "--standalone"],
        input=exported,
        text=True,
        env=env,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"auth import failed: {result.stderr.strip()[:200]}")
    print(result.stdout.strip() or "auth import: ok")
    subprocess.run(["chmod", "-R", "u+rwX,go-rwx", str(data)], check=False)


def build_cell(cell: str, meta: dict) -> None:
    root = BENCH / f"env-{cell}"
    if root.exists():
        subprocess.run(["chmod", "-R", "u+rwX", str(root)], check=False)
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for d in ("config", "data", "cache", "state"):
        (root / d).mkdir(parents=True, exist_ok=True)
    make_config(cell, meta, root)
    import_auth(root)
    print(f"{cell}: {root} provider={meta['provider']} model={meta['model']}")


def main() -> None:
    for cell, meta in CELLS.items():
        build_cell(cell, meta)


if __name__ == "__main__":
    main()
