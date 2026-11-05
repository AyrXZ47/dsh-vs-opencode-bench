# Visual evidence

**The sessions were headless.** There is no screen recording and no live
screenshot of a model session. Everything below is a reconstruction from the
submitted code and the aggregate results, generated after the runs.

## Webapp (suite 2, phase 1)

| File | What it shows |
|---|---|
| `webapp-montage.png` | The four submitted frontends, same four tasks |
| `webapp-dsh-ds.png` | DSH + DeepSeek directo |
| `webapp-dsh-oc.png` | DSH + OpenCode Go |
| `webapp-oc-ds.png` | OpenCode + DeepSeek directo |
| `webapp-oc-oc.png` | OpenCode + OpenCode Go |

How they were generated: each cell's `fase1-webapp` patch was applied to a
clean copy of `bench/seed`; its `make_server()` was started on a random port;
four synthetic tasks were created via the API; Firefox headless took the
screenshot. They show the **submitted UI**, not a live model session.

**Aesthetic note:** these screenshots are not a design score. In this sample
`dsh-ds` looks more polished (cards, spacing, badges), but the hidden tests only
check function. Visual style is a model/harness choice, not a provider-quality
metric.

The functional evidence is the hidden test suite (`13/13` in every cell):
CRUD, validation, pagination, SQL injection, concurrency, persistence and
frontend markers.

## 3D renderer (suite 2, phase 2)

| File | What it shows |
|---|---|
| `render3d-montage.png` | The same octahedron rendered by the four submissions |
| `render3d-dsh-ds.png` | DSH + DeepSeek directo |
| `render3d-dsh-oc.png` | DSH + OpenCode Go |
| `render3d-oc-ds.png` | OpenCode + DeepSeek directo |
| `render3d-oc-oc.png` | OpenCode + OpenCode Go |

Each cell's `fase2-render3d` patch was applied to a clean seed and used to
render the same scene (perspective, culling, z-buffer, Lambert lighting, PPM).
The four images being identical is the expected result: all four implementations
passed the same `10/10` hidden tests.

## Charts

| File | What it shows |
|---|---|
| `suite2-scores.png` | Suite 2 score heatmap (4 cells × 5 phases + mean) |
| `suite2-time.png` | Suite 2 wall time, stacked by phase |
| `suite2-cost.png` | Suite 2 cost: catalog vs actual |
| `suite1-time.png` | Suite 1 wall time, 4 scored phases (smoke excluded) |
| `suite1-cost.png` | Suite 1 cost, 4 scored phases (smoke excluded) |

They are generated with matplotlib from `results/aggregate.json` and
`results/aggregate2.json`.

## Suite 1 vision asset

`vision-schematic.png` is the NE555 astable schematic used in the vision phase.
All four cells identified the astable, `686 Hz`, `52.4 %` duty and the
`RESET` tied to `GND` inconsistency.

## Text-based tests

Ledger, research and skills are better inspected as text:

- `results/REPORT2.md` — ledger failure and the `501 vs 500` rounding bug.
- `results/REPORT.md` — suite 1, including the web source verification.
- `results/SOURCE-VERIFICATION.md` — which URLs were checked and which were
  blocked.
- `results/aggregate2.csv` — per-run scores, tokens, time and cost.

## Reproduce the images

Requirements: Python 3.14, matplotlib, ImageMagick (`magick`), Firefox
headless, and the local run artifacts from `bench/bin/run-cell.sh`.

```sh
export RESULTS_ROOT="$HOME/bench2-harness"
export RESULTS1_ROOT="$HOME/bench-harness"
export BENCH_ROOT="$HOME/repos/bench2"
python3 visuals/make_visuals.py
```

The script applies each cell's saved `changes.patch`, starts the submitted
webapp, renders the 3D scene, and rebuilds the charts. It does not re-run any
model.
