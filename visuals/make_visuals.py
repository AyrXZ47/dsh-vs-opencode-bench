#!/usr/bin/env python3
"""Generate visual evidence from the bench2 artifacts.

The sessions were headless; these images are reconstructions from the
submitted code and the aggregate results, not screen recordings.

Outputs go to <repo>/visuals/.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

H = Path(os.environ.get("RESULTS_ROOT", Path.home() / "bench2-harness"))
H1 = Path(os.environ.get("RESULTS1_ROOT", Path.home() / "bench-harness"))
B = Path(os.environ.get("BENCH_ROOT", Path.home() / "repos" / "bench2"))
OUT = Path(os.environ.get("VISUALS_OUT", Path(__file__).resolve().parent))
OUT.mkdir(parents=True, exist_ok=True)

CELLS = ["dsh-ds", "dsh-oc", "oc-ds", "oc-oc"]
LABELS = {
    "dsh-ds": "dsh-ds · DSH + DeepSeek directo",
    "dsh-oc": "dsh-oc · DSH + OpenCode Go",
    "oc-ds": "oc-ds · OpenCode + DeepSeek directo",
    "oc-oc": "oc-oc · OpenCode + OpenCode Go",
}
SHORT = {c: c for c in CELLS}
PHASES = ["fase1-webapp", "fase2-render3d", "fase3-ledger", "fase4-research", "fase5-skills"]
PHASE_LABELS = {
    "fase1-webapp": "Webapp",
    "fase2-render3d": "3D",
    "fase3-ledger": "Ledger",
    "fase4-research": "Research",
    "fase5-skills": "Skills",
}
COLORS = {
    "dsh-ds": "#e45756",
    "dsh-oc": "#f2a541",
    "oc-ds": "#4c9f70",
    "oc-oc": "#4c78a8",
}


def latest_run(cell: str, phase: str) -> Path:
    dirs = [
        Path(d)
        for d in (H / "results" / cell).glob(f"{phase}-*")
        if "EXCLUDED" not in d.name
    ]
    if not dirs:
        raise SystemExit(f"missing run: {cell} {phase}")
    return max(dirs, key=lambda p: p.stat().st_mtime)


def apply_patch(cell: str, phase: str) -> Path:
    run = latest_run(cell, phase)
    patch = run / "changes.patch"
    tmp = Path(tempfile.mkdtemp(prefix=f"vis-{cell}-{phase}-"))
    subprocess.run(
        ["rsync", "-a", "--exclude=.git", "--exclude=.bench-vault", "--exclude=__pycache__",
         str(B / "seed") + "/", str(tmp) + "/"],
        check=True,
    )
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=bench", "-c", "user.email=bench@local", "commit", "-m", "seed"],
        cwd=tmp, check=True, capture_output=True,
    )
    subprocess.run(["git", "apply", "--whitespace=nowarn", str(patch)], cwd=tmp, check=True)
    return tmp


# ---------------------------------------------------------------- webapp shots

SERVER = r'''
import json, os, sys, threading, time, urllib.request, tempfile
root, portfile, keep = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, root)
from webapp.app import make_server
db = tempfile.mktemp(suffix=".db")
srv = make_server("127.0.0.1", 0, db)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
def post(title, status, priority):
    data = json.dumps({"title": title, "status": status, "priority": priority}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/tasks", data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        r.read()
post("Diseñar el dashboard", "done", "high")
post("Conectar SQLite", "doing", "medium")
post("Escribir tests", "todo", "high")
post("Documentar la API", "todo", "low")
time.sleep(0.4)
open(portfile, "w").write(str(port))
while os.path.exists(keep):
    time.sleep(0.2)
srv.shutdown()
'''


def webapp_shot(cell: str) -> Path:
    tmp = apply_patch(cell, "fase1-webapp")
    portfile = tmp / "port.txt"
    keep = tmp / "keep"
    keep.touch()
    script = tmp / "serve.py"
    script.write_text(SERVER)
    proc = subprocess.Popen(
        [sys.executable, str(script), str(tmp), str(portfile), str(keep)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            if portfile.exists() and portfile.read_text().strip():
                break
            time.sleep(0.1)
        else:
            raise RuntimeError(f"server did not start for {cell}")
        port = int(portfile.read_text().strip())
        profile = tempfile.mkdtemp(prefix="ff-profile-")
        out = OUT / f"webapp-{cell}.png"
        subprocess.run(
            ["firefox", "--headless", "--profile", profile,
             "--screenshot", str(out), "--window-size=1280,900",
             f"http://127.0.0.1:{port}/"],
            check=True, timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        shutil.rmtree(profile, ignore_errors=True)
        return out
    finally:
        keep.unlink(missing_ok=True)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 3D renders

def octahedron_scene() -> dict:
    top = (0.0, 1.5, 0.0)
    bottom = (0.0, -1.5, 0.0)
    ring = [(1.5, 0.0, 0.0), (0.0, 0.0, 1.5), (-1.5, 0.0, 0.0), (0.0, 0.0, -1.5)]
    colors = [
        [220, 70, 70], [70, 200, 120], [70, 120, 220], [230, 190, 70],
        [200, 90, 200], [70, 200, 200], [230, 130, 60], [150, 110, 230],
    ]
    triangles = []

    def normal(a, b, c):
        ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        return (
            ab[1] * ac[2] - ab[2] * ac[1],
            ab[2] * ac[0] - ab[0] * ac[2],
            ab[0] * ac[1] - ab[1] * ac[0],
        )

    def add(a, b, c, color):
        n = normal(a, b, c)
        centroid = ((a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3, (a[2] + b[2] + c[2]) / 3)
        if n[0] * centroid[0] + n[1] * centroid[1] + n[2] * centroid[2] < 0:
            b, c = c, b
        triangles.append({"v0": list(a), "v1": list(b), "v2": list(c), "color": color})

    index = 0
    for i in range(4):
        a = ring[i]
        b = ring[(i + 1) % 4]
        add(top, a, b, colors[index]); index += 1
        add(bottom, b, a, colors[index]); index += 1

    return {
        "width": 640,
        "height": 480,
        "background": [12, 12, 18],
        "camera": {"position": [0, 0, 6], "target": [0, 0, 0], "up": [0, 1, 0], "fov_deg": 45},
        "light": {"direction": [-0.4, -0.8, -0.6], "ambient": 0.15, "diffuse": 0.85},
        "triangles": triangles,
    }


RENDER = r'''
import json, sys
root, scene_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, root)
from render3d.render import render
from render3d.scene import validate_scene
scene = json.load(open(scene_path))
validate_scene(scene)
open(out_path, "wb").write(render(scene))
'''


def render3d_shot(cell: str) -> Path:
    tmp = apply_patch(cell, "fase2-render3d")
    scene_path = tmp / "scene.json"
    scene_path.write_text(json.dumps(octahedron_scene()))
    ppm = tmp / "out.ppm"
    script = tmp / "render.py"
    script.write_text(RENDER)
    subprocess.run(
        [sys.executable, str(script), str(tmp), str(scene_path), str(ppm)],
        check=True, timeout=60,
    )
    out = OUT / f"render3d-{cell}.png"
    label = LABELS[cell].replace(" · ", " | ")
    raw = tmp / "render.png"
    subprocess.run(["magick", str(ppm), str(raw)], check=True)
    banner = tmp / "banner.png"
    subprocess.run(
        ["magick", "-size", "640x48", "xc:#111111", "-font", "DejaVu-Sans",
         "-fill", "white", "-pointsize", "22", "-gravity", "center",
         "-annotate", "0", label, str(banner)],
        check=True,
    )
    subprocess.run(["magick", str(banner), str(raw), "-append", str(out)], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return out


# ---------------------------------------------------------------- charts

def load_suite2():
    data = json.loads((H / "results" / "aggregate2.json").read_text())
    rows = {(r["cell"], r["phase"]): r for r in data["rows"]}
    cells = {c["cell"]: c for c in data["cells"]}
    return rows, cells


def load_suite1():
    data = json.loads((H1 / "results" / "aggregate.json").read_text())
    rows = {(r["cell"], r["phase"]): r for r in data["rows"] if r["phase"] != "fase0-smoke"}
    return rows


def style():
    plt.style.use("dark_background")
    plt.rcParams.update({
        "figure.facecolor": "#0f1116",
        "axes.facecolor": "#0f1116",
        "savefig.facecolor": "#0f1116",
        "font.family": "DejaVu Sans",
        "axes.edgecolor": "#333842",
        "axes.labelcolor": "#e6e6e6",
        "xtick.color": "#cfcfcf",
        "ytick.color": "#cfcfcf",
        "text.color": "#f0f0f0",
    })


def chart_scores():
    rows, cells = load_suite2()
    matrix = np.array([[rows[(c, p)]["score"] for p in PHASES] + [cells[c]["score_mean"]] for c in CELLS])
    fig, ax = plt.subplots(figsize=(12, 5.2), dpi=160)
    im = ax.imshow(matrix, cmap="YlGn", vmin=0.85, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(PHASES) + 1))
    ax.set_xticklabels([PHASE_LABELS[p] for p in PHASES] + ["Mean"], fontsize=11)
    ax.set_yticks(range(len(CELLS)))
    ax.set_yticklabels(CELLS, fontsize=12)
    for i in range(len(CELLS)):
        for j in range(len(PHASES) + 1):
            value = matrix[i, j]
            ax.text(j, i, f"{value:.3f}", ha="center", va="center",
                    color="#f2fff2" if value >= 0.95 else "#1a1a1a", fontsize=11, fontweight="bold")
    ax.grid(False)
    ax.set_title("Suite 2 — score by phase (0–1)", fontsize=15, pad=14)
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    fig.tight_layout()
    fig.savefig(OUT / "suite2-scores.png")
    plt.close(fig)


def chart_suite2_time():
    rows, cells = load_suite2()
    phase_colors = ["#4c78a8", "#59a14f", "#e15759", "#f28e2b", "#b07aa1"]
    order = sorted(CELLS, key=lambda c: cells[c]["wall_s"])
    fig, ax = plt.subplots(figsize=(12, 5.8), dpi=160)
    left = np.zeros(len(order))
    for phase, color in zip(PHASES, phase_colors):
        values = np.array([rows[(c, phase)]["wall_s"] for c in order])
        ax.barh(order, values, left=left, color=color, label=PHASE_LABELS[phase], height=0.6)
        left += values
    for i, c in enumerate(order):
        total = cells[c]["wall_s"]
        ax.text(total + 25, i, f"{total:.0f} s", va="center", fontsize=11, fontweight="bold")
    ax.invert_yaxis()
    ax.set_xlabel("wall time (seconds)")
    ax.set_title("Suite 2 — wall time by phase", fontsize=15, pad=14)
    ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.14), frameon=False)
    ax.set_xlim(0, max(cells[c]["wall_s"] for c in CELLS) * 1.15)
    fig.subplots_adjust(left=0.14, right=0.98, top=0.88, bottom=0.20)
    fig.savefig(OUT / "suite2-time.png")
    plt.close(fig)


def chart_suite2_cost():
    rows, cells = load_suite2()
    x = np.arange(len(CELLS))
    nominal = [cells[c]["cost_nominal"] for c in CELLS]
    actual = [cells[c]["cost_actual_sum"] if cells[c]["cost_actual_sum"] is not None else 0 for c in CELLS]
    fig, ax = plt.subplots(figsize=(11, 5), dpi=160)
    ax.bar(x - 0.18, nominal, width=0.36, color="#4c78a8", label="nominal (catalog)")
    ax.bar(x + 0.18, actual, width=0.36, color="#59a14f", label="actual (OpenCode report)")
    for i, c in enumerate(CELLS):
        ax.text(i - 0.18, nominal[i] + 0.004, f"${nominal[i]:.3f}", ha="center", fontsize=9)
        if cells[c]["cost_actual_sum"] is None:
            ax.text(i + 0.18, 0.004, "n/a", ha="center", fontsize=10, color="#aaaaaa")
        else:
            ax.text(i + 0.18, actual[i] + 0.004, f"${actual[i]:.3f}", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(CELLS)
    ax.set_ylabel("USD for 5 phases")
    ax.set_title("Suite 2 — cost: catalog vs actual", fontsize=15, pad=12)
    ax.legend(frameon=False)
    ax.set_ylim(0, max(nominal) * 1.28)
    fig.tight_layout()
    fig.savefig(OUT / "suite2-cost.png")
    plt.close(fig)


def chart_suite1_time():
    rows = load_suite1()
    phases = ["fase1-codigo", "fase2-web", "fase3-vision", "fase4-skills"]
    labels = ["Coding", "Web", "Vision", "Skills"]
    phase_colors = ["#4c78a8", "#59a14f", "#e15759", "#f28e2b"]
    order = sorted(CELLS, key=lambda c: sum(rows[(c, p)]["wall_s"] for p in phases))
    totals = {c: sum(rows[(c, p)]["wall_s"] for p in phases) for c in order}
    fig, ax = plt.subplots(figsize=(12, 5.8), dpi=160)
    left = np.zeros(len(order))
    for phase, label, color in zip(phases, labels, phase_colors):
        values = np.array([rows[(c, phase)]["wall_s"] for c in order])
        ax.barh(order, values, left=left, color=color, label=label, height=0.6)
        left += values
    for i, c in enumerate(order):
        ax.text(totals[c] + 10, i, f"{totals[c]:.0f} s", va="center", fontsize=11, fontweight="bold")
    ax.invert_yaxis()
    ax.set_xlabel("wall time (seconds)")
    ax.set_title("Suite 1 — wall time by phase (smoke excluded)", fontsize=15, pad=14)
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.14), frameon=False)
    ax.set_xlim(0, max(totals.values()) * 1.15)
    fig.subplots_adjust(left=0.14, right=0.98, top=0.88, bottom=0.20)
    fig.savefig(OUT / "suite1-time.png")
    plt.close(fig)


def chart_suite1_cost():
    rows = load_suite1()
    phases = ["fase1-codigo", "fase2-web", "fase3-vision", "fase4-skills"]
    nominal = [sum(rows[(c, p)]["cost_nominal"] for p in phases) for c in CELLS]
    actual = [sum((rows[(c, p)]["cost_actual"] or 0) for p in phases) for c in CELLS]
    x = np.arange(len(CELLS))
    fig, ax = plt.subplots(figsize=(11, 5), dpi=160)
    ax.bar(x - 0.18, nominal, width=0.36, color="#4c78a8", label="nominal (catalog)")
    ax.bar(x + 0.18, actual, width=0.36, color="#59a14f", label="actual (OpenCode report)")
    for i, c in enumerate(CELLS):
        ax.text(i - 0.18, nominal[i] + 0.003, f"${nominal[i]:.3f}", ha="center", fontsize=9)
        if rows[(c, "fase1-codigo")]["cost_actual"] is None:
            ax.text(i + 0.18, 0.003, "n/a", ha="center", fontsize=10, color="#aaaaaa")
        else:
            ax.text(i + 0.18, actual[i] + 0.003, f"${actual[i]:.3f}", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(CELLS)
    ax.set_ylabel("USD for 4 scored phases")
    ax.set_title("Suite 1 — cost: 4 scored phases (smoke excluded)", fontsize=15, pad=12)
    ax.legend(frameon=False)
    ax.set_ylim(0, max(nominal) * 1.28)
    fig.tight_layout()
    fig.savefig(OUT / "suite1-cost.png")
    plt.close(fig)


def montage():
    web_args = []
    for c in CELLS:
        web_args += ["-label", LABELS[c].replace(" · ", " | "), str(OUT / f"webapp-{c}.png")]
    subprocess.run(
        ["montage", *web_args, "-tile", "2x2", "-geometry", "640x450+10+10",
         "-background", "#111111", "-font", "DejaVu-Sans", "-fill", "white",
         "-pointsize", "20", str(OUT / "webapp-montage.png")],
        check=True,
    )
    r3d = [OUT / f"render3d-{c}.png" for c in CELLS]
    subprocess.run(
        ["montage", *map(str, r3d), "-tile", "2x2", "-geometry", "640x528+10+10",
         "-background", "#111111", str(OUT / "render3d-montage.png")],
        check=True,
    )


def copy_vision():
    src = Path(os.environ.get("VISION_ASSET", Path.home() / "repos" / "bench" / "seed" / "assets" / "bench" / "test-circuit.png"))
    if src.exists():
        shutil.copy2(src, OUT / "vision-schematic.png")


def main():
    style()
    for cell in CELLS:
        print("webapp", cell)
        webapp_shot(cell)
        print("render3d", cell)
        render3d_shot(cell)
    chart_scores()
    chart_suite2_time()
    chart_suite2_cost()
    chart_suite1_time()
    chart_suite1_cost()
    montage()
    copy_vision()
    print("done", OUT)


if __name__ == "__main__":
    main()
