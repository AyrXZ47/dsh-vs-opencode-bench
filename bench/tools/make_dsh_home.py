#!/usr/bin/env python3
"""Create the two isolated DSH_HOME environments for the PC benchmark.

Cells:
  dsh-ds : DSH harness + DeepSeek official API (deepseek-official)
  dsh-oc : DSH harness + OpenCode Go gateway (opencode-go)

Each DSH_HOME has:
  - an isolated headless profile (provider/model pinned)
  - an isolated TUI profile (same provider/model, TUI provider pinned)
  - copied skills with the test-vault path substituted
  - a copied global AGENTS.md with a benchmark header
  - a root patch with MCP servers, the dotpm test-vault path, and a
    workspace-write permission preset that never asks
  - empty sessions/storages

Nothing under ~/.dsh is modified.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path
from textwrap import dedent

BENCH = Path(os.environ.get("BENCH_ROOT", Path.home() / "repos" / "bench2"))
REAL_DSH = Path(os.environ.get("DSH_SOURCE_HOME", Path.home() / ".dsh"))
REAL_VAULT = Path(os.environ.get("REAL_VAULT", Path.home() / "Sync" / "Notes"))
SKILLS = ("dotpm", "ponytail", "security-audit", "vault")

CELLS = {
    "dsh-ds": {
        "worktree": BENCH / "dsh-ds",
        "vault": BENCH / "dsh-ds" / ".bench-vault",
        "provider": "deepseek-official",
        "model": "deepseek-flash",
    },
    "dsh-oc": {
        "worktree": BENCH / "dsh-oc",
        "vault": BENCH / "dsh-oc" / ".bench-vault",
        "provider": "opencode-go",
        "model": "deepseek-v4.1-flash",
    },
}

HEADLESS_TEMPLATE = """\
# Your patch layer for this dsh profile, applied after every bundle layer:
# a top-level YAML array of loader patch entries (id-targeted config
# overrides, disables, and insert lists; `!!js` expressions allowed).
{body}
"""

DIRECT_PROVIDER = """\
- id: agent-default-model
  name: '@deepseek-ai/dsh-agent-default-model'
  config:
    provider: deepseek-official
    model: deepseek-flash
- id: llm-deepseek
  name: '@deepseek-ai/dsh-llm-deepseek-api-key'
  config:
    apiKeyEnv: DEEPSEEK_API_KEY
    baseURL: !!js process.env.DEEPSEEK_BASE_URL
    thinking: enabled
    reasoningEffort: max
"""

OC_PROVIDER = """\
- id: agent-default-model
  name: '@deepseek-ai/dsh-agent-default-model'
  config:
    provider: opencode-go
    model: deepseek-v4.1-flash
- id: llm-pi-ai
  name: '@deepseek-ai/dsh-llm-pi-ai'
  config:
    providers:
      opencode-go:
        apiKeyEnv: OPENCODE_GO_API_KEY
        baseURL: !!js process.env.OPENCODE_GO_BASE_URL
        reasoning: max
        models:
          - id: deepseek-v4.1-flash
        retryPolicy:
          mode: normal
          maxRetries: 5
          retryableCodes:
            - EMPTY_RESPONSE
            - RATE_LIMIT
            - SERVER
            - TIMEOUT
            - TRANSPORT
            - STREAM_CLOSED
"""

TUI_EXTRA = """\
- id: dsh-tui
  config:
    effort: max
    fullscreen: true
    launchpad: false
    notificationMethod: auto
    provider: {provider}
    scrollGutter: scrollbar
    terminalImages: true
    thinkingFold: preview
    turnUsageRow: true
    whale: true
    whaleIdle: true
"""

ROOT_PATCH = """\
- insert:
    - id: mcp-context7
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: context7
        transport: streamable-http
        url: https://mcp.context7.com/mcp
    - id: mcp-gh-grep
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: gh_grep
        transport: streamable-http
        url: https://mcp.grep.app
    - id: mcp-duckduckgo
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        args:
          - duckduckgo-mcp-server
        command: uvx
        serverName: duckduckgo
        transport: stdio
    - id: mcp-dotpm
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        args:
          - mcp
          - --vault
          - {vault}
        command: dotpm
        serverName: dotpm
        transport: stdio
    - id: worktree
      name: '@deepseek-ai/dsh-experimental-worktree'
    - id: tool-worktree
      name: '@deepseek-ai/dsh-experimental-tool-worktree'
- id: permission
  name: '@deepseek-ai/dsh-permission-presets'
  config:
    defaultPreset: bench-workspace
    presets:
      bench-workspace:
        approval: never
        sandbox: workspace-write
        name: Bench workspace
        description: Write only inside this worktree; never ask.
      read-only:
        approval: ask
        sandbox: read-only
        name: Read only
        description: Observe without mutations.
"""

BENCH_HEADER = """\
# Benchmark DSH (PC) — instrucciones de la celda

- Worktree de esta sesión: `{worktree}`
- Vault de prueba permitido: `{vault}`
- No leas ni escribas en `~/Sync/Notes` (vault real) durante esta prueba.
- No uses subagentes, `subagent_fork`, workflows ni worktrees anidados:
  resolvé la tarea en esta única sesión.
- No hagas commits: dejá los cambios en el working tree para el snapshot.
- El MCP `dotpm` apunta al vault de prueba. Si no responde, no inventes un
  backlog paralelo; reportalo.

"""


def copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, symlinks=False, dirs_exist_ok=True)


def force_chmod(root: Path) -> None:
    subprocess.run(["chmod", "-R", "u+w", str(root)], check=False)


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


def write_profile_patch(home: Path, profile: str, body: str) -> None:
    path = home / "profiles" / profile / "cordis.patch.yml"
    if path.exists() or path.is_symlink():
        path.unlink()
    path.write_text(HEADLESS_TEMPLATE.format(body=body), encoding="utf-8")


def build_cell(cell: str, meta: dict) -> None:
    home = BENCH / f"env-{cell}" / "dsh-home"
    if home.exists():
        force_chmod(home)
        shutil.rmtree(home)

    (home / "profiles" / "headless").mkdir(parents=True)
    (home / "profiles" / "tui").mkdir(parents=True)
    (home / "skills").mkdir(parents=True)
    (home / "sessions").mkdir(parents=True)
    (home / "storages").mkdir(parents=True)

    # Headless profile: tiny, installation-provided bundles.
    for name in ("package.json", "pnpm-workspace.yaml", "cordis.yml"):
        src = REAL_DSH / "profiles" / "headless" / name
        shutil.copy2(src, home / "profiles" / "headless" / name)

    # TUI profile: copy the working profile, then replace only its patch layer.
    copy_tree(REAL_DSH / "profiles" / "tui", home / "profiles" / "tui")

    # Skills: copy contents and substitute the test-vault path.
    for skill in SKILLS:
        src = REAL_DSH / "skills" / skill
        dst = home / "skills" / skill
        copy_tree(src, dst)
    force_chmod(home / "skills")
    replace_text_in_tree(home / "skills", "~/Sync/Notes", str(meta["vault"]))
    replace_text_in_tree(home / "skills", str(REAL_VAULT), str(meta["vault"]))

    # Global AGENTS: same as the real DSH, plus a per-cell benchmark header.
    agents = (REAL_DSH / "AGENTS.md").read_text(encoding="utf-8")
    agents = agents.replace("~/Sync/Notes", str(meta["vault"]))
    agents = agents.replace(str(REAL_VAULT), str(meta["vault"]))
    agents = BENCH_HEADER.format(worktree=meta["worktree"], vault=meta["vault"]) + agents
    (home / "AGENTS.md").write_text(agents, encoding="utf-8")

    # Root patch: MCP servers, dotpm vault, permission preset.
    (home / "cordis.patch.yml").write_text(
        ROOT_PATCH.format(vault=meta["vault"]), encoding="utf-8"
    )

    # Provider patch for headless.
    provider_body = DIRECT_PROVIDER if cell == "dsh-ds" else OC_PROVIDER
    write_profile_patch(home, "headless", provider_body)

    # Provider patch for TUI, plus the TUI provider preference.
    tui_body = provider_body + "\n" + TUI_EXTRA.format(provider=meta["provider"])
    write_profile_patch(home, "tui", tui_body)

    (home / ".anonymous-user-id").write_text(str(uuid.uuid4()), encoding="utf-8")
    (home / ".env").write_text("", encoding="utf-8")

    print(f"{cell}: {home}")
    print(f"  provider={meta['provider']} model={meta['model']} vault={meta['vault']}")


def main() -> None:
    for cell, meta in CELLS.items():
        build_cell(cell, meta)


if __name__ == "__main__":
    main()
