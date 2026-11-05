# bench — harness, tasks and graders

This directory is the executable part of the benchmark. It is designed to run
on a Linux host with DSH and OpenCode installed. The original run used NixOS
and `bubblewrap`; adapt the paths to your system.

## Requirements

- **DSH** (`dsh`) with a `headless` profile.
- **OpenCode** (`opencode`) with `--standalone`.
- **Python 3.14+** (stdlib only).
- **bubblewrap** (`bwrap`) for the outer sandbox.
- **dotpm** and an Obsidian vault with the `project-manager` plugin, for
  `fase5-skills`. If you skip phase 5, you can skip this.
- **uvx** on `PATH` for the DuckDuckGo MCP server used by the DSH profiles.
- `git` and `curl`.

The reference run used:

```text
DSH 0.2.1-rc.3
OpenCode 2.2.1
Python 3.14
bubblewrap 0.12
```

## Environment variables

| Variable | Meaning | Default |
|---|---|---|
| `BENCH_ROOT` | working root with `seed/`, worktrees, `env-*`, `vault-base/` | `~/repos/bench2` |
| `HARNESS_ROOT` | this `bench/` directory | `~/bench2-harness` |
| `REAL_VAULT` | real Obsidian vault (only read to copy the dotpm plugin and replace paths) | `~/Sync/Notes` |
| `DOTPM_PLUGIN_SRC` | path to the `project-manager` plugin inside a vault | `$REAL_VAULT/.obsidian/plugins/project-manager` |
| `DSH_SOURCE_HOME` | real `~/.dsh` used as the profile source | `~/.dsh` |
| `OPENCODE_SOURCE_CONFIG` | real `~/.config/opencode` used as the config source | `~/.config/opencode` |

Set `HARNESS_ROOT` to this directory when running:

```sh
export HARNESS_ROOT="$PWD/bench"
```

## Setup

```sh
export BENCH_ROOT="$HOME/bench-work"
export HARNESS_ROOT="$PWD/bench"
export REAL_VAULT="$HOME/Sync/Notes"

rm -rf "$BENCH_ROOT"
mkdir -p "$BENCH_ROOT"
cp -a bench/seed "$BENCH_ROOT/seed"

cd "$BENCH_ROOT/seed"
git init -b main
git add -A
git commit -m "chore: benchmark seed"

for cell in dsh-ds dsh-oc oc-ds oc-oc; do
  git worktree add -b "$cell" "$BENCH_ROOT/$cell" main
done
```

Build the isolated environments:

```sh
BENCH_ROOT="$BENCH_ROOT" python3 bench/tools/make_dsh_home.py
BENCH_ROOT="$BENCH_ROOT" python3 bench/tools/make_oc_home.py
BENCH_ROOT="$BENCH_ROOT" python3 bench/tools/make_vault.py
```

`make_oc_home.py` imports the credentials from your global OpenCode store into
each isolated store. It never writes the keys to the repository.

### Test vaults and dotpm

`make_vault.py` creates four copies of a synthetic Obsidian vault under
`$BENCH_ROOT/<cell>/.bench-vault`, with local API ports **27401–27404** and
different tokens.

To serve them, start a **separate** Obsidian instance (do not use your real
profile) with a `--user-data-dir` and an `obsidian.json` that lists the four
vaults and sets `"cli": true`. Then disable restricted mode per vault:

```sh
cd "$BENCH_ROOT/dsh-ds/.bench-vault"
obsidian-cli plugins:restrict off
```

Repeat for the four cells. Verify:

```sh
bench/bin/check-dotpm.sh dsh-ds
```

If you do not need phase 5, skip this section.

## Run

```sh
bench/bin/run-cell.sh <cell> <phase>
```

Cells: `dsh-ds`, `dsh-oc`, `oc-ds`, `oc-oc`.

Phases:

| Phase | Task |
|---|---|
| `fase0-smoke` | optional auth/routing smoke; not scored |
| `fase1-webapp` | REST + SQLite + static frontend |
| `fase2-render3d` | software rasterizer |
| `fase3-ledger` | seeded bugs + regression tests |
| `fase4-research` | SQLite WAL research |
| `fase5-skills` | vault, dotpm, ponytail, security-audit |

The runner:

1. resets the worktree to `HEAD`;
2. runs the model inside `bwrap` (only the worktree and its env are writable);
3. saves events, stderr, answer, summary and diff;
4. runs the hidden tests with `graders/grade.py`;
5. writes `grade.json` next to the run.

Results land in `$HARNESS_ROOT/results/<cell>/<phase>-<timestamp>/`.

Set `RUN_TIMEOUT` to change the default (3600 s).

## Credentials

`tools/keys.py` reads `opencode auth export` at runtime and exposes the key
that each cell needs:

- `dsh-ds` / `oc-ds`: `DEEPSEEK_API_KEY`
- `dsh-oc` / `oc-oc`: `OPENCODE_GO_API_KEY` and `DEEPSEEK_API_KEY` (DSH native
  web search still uses the DeepSeek key)

If you do not use OpenCode auth, create `$HARNESS_ROOT/secrets.env` with
`export` lines. It is gitignored. Never commit it.

## Warning about reuse

`bench/tests/` and `bench/reference/` are public. The hidden tests are no
longer hidden, and the reference implementations are visible. If you want to
reuse this benchmark for a new comparison, create new tasks/tests or remove
those directories from the agent environment.

## License

Code in this directory is Apache-2.0. See [`../LICENSE`](../LICENSE).
