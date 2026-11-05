#!/usr/bin/env python3
"""Build the disposable Obsidian vault fixtures for bench2.

Writes only under <bench>/vault-base and <worktree>/.bench-vault.
The real vault is never modified.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path

BENCH = Path(os.environ.get("BENCH_ROOT", Path.home() / "repos" / "bench2"))
REAL_VAULT = Path(os.environ.get("REAL_VAULT", Path.home() / "Sync" / "Notes"))
BASE = BENCH / "vault-base"
PLUGIN_SRC = Path(os.environ.get("DOTPM_PLUGIN_SRC", REAL_VAULT / ".obsidian" / "plugins" / "project-manager"))

CELLS = {
    "dsh-ds": {"port": 27401, "worktree": BENCH / "dsh-ds"},
    "dsh-oc": {"port": 27402, "worktree": BENCH / "dsh-oc"},
    "oc-ds": {"port": 27403, "worktree": BENCH / "oc-ds"},
    "oc-oc": {"port": 27404, "worktree": BENCH / "oc-oc"},
}

VAULT_AGENTS = """# Vault de prueba (bench2)

Copia desechable para la suite bench2. No contiene datos reales ni se sincroniza.

- No tocar `.obsidian/`, `.smart-env/`, `copilot/`, `Calendar/` ni el frontmatter
  gestionado de `Projects/`.
- El backlog vive en `Projects/` y se escribe con la skill `dotpm` o el MCP
  `dotpm`, no a mano.
- Las notas y decisiones van en `Topics/`; usá `[[wikilinks]]`.
- Idioma: español.
"""

BENCH_PROJECT = """---
pm-project: true
id: "bench20000000001"
title: "🧪 Bench 2"
color: "#6ba8a0"
icon: "🧪"
taskIds: []
customFields: []
teamMembers: []
savedViews: []
createdAt: "{created}"
updatedAt: "{updated}"
---

# 🧪 Bench 2

## Tasks
"""

NOTES = {
    "Orion - overview.md": """---
tags: [orion, telemetry, architecture]
---

# Orion — overview

Orion es el pipeline de telemetría y alertas de Northwind Labs. Recibe eventos
por HTTP, los valida, los guarda y dispara alertas cuando una métrica cruza un
umbral.

- Ingesta HTTP en el puerto 8087, servicio `orion-ingest`.
- Retención caliente de 30 días en SQLite; después se exporta a Parquet.
- Un solo proceso escribe; varios procesos leen.
- Despliegue en NixOS con systemd.
- On-call: Maya; backup: Ivo.

Relacionado: [[Orion - storage]] · [[Orion - alerts]] · [[Orion - deployment]]
""",
    "Orion - storage.md": """---
tags: [orion, sqlite, wal]
---

# Orion — storage

Orion usa SQLite en modo WAL. El archivo principal es `orion.db`; al lado viven
`orion.db-wal` y `orion.db-shm`.

- `journal_mode=WAL`: los lectores no bloquean al escritor y viceversa.
- Un solo escritor a la vez; los lectores ven una foto consistente.
- `busy_timeout=5000` para esperar locks en vez de fallar.
- `wal_autocheckpoint=1000` páginas; los checkpoints mueven datos del WAL al
  archivo principal.
- Nunca se usa SQLite sobre NFS: los locks y el `-shm` no son confiables en red.

Ver [[Orion - incident-2026-09]].
""",
    "Orion - alerts.md": """---
tags: [orion, alerts, slo]
---

# Orion — alerts

- Alerta principal: p95 de latencia de ingesta > 250 ms durante 5 minutos.
- Alerta secundaria: más de 1% de eventos rechazados en 10 minutos.
- El reloj de los nodos debe estar sincronizado con NTP; si el skew supera
  2 segundos, se dispara `clock_skew_high`.
- Las alertas se enrutan a `#orion-oncall`.

Ver [[Orion - deployment]].
""",
    "Orion - deployment.md": """---
tags: [orion, nixos, systemd]
---

# Orion — deployment

- Host NixOS; el módulo vive en `modules/services/orion.nix`.
- Servicio systemd `orion-ingest`, puerto 8087, usuario `orion`.
- Estado en `/var/lib/orion`; logs en journald.
- El deploy se hace con `nixos-rebuild switch` y un healthcheck a `/healthz`.
- No se abre el puerto a internet; solo a la red interna.

Ver [[Orion - overview]].
""",
    "Orion - decisions.md": """---
tags: [orion, decisions]
---

# Orion — decisiones

## 2026-08-12 — spool en archivos, no Kafka

Se descartó Kafka para v1. El volumen es bajo y el equipo es chico; un spool de
archivos con rotación y un solo consumidor alcanza. Kafka se reevalúa si la
ingesta supera 5k eventos/s o si aparece más de un consumidor independiente.

## 2026-09-02 — SQLite antes que Postgres

Se eligió SQLite por simplicidad operativa. Postgres queda para cuando haya
múltiples writers o consultas analíticas pesadas.
""",
    "Orion - roadmap.md": """---
tags: [orion, roadmap]
---

# Orion — roadmap v2

- Compresión zstd de los archivos del spool (hoy son JSON plano).
- Batch de 500 eventos por transacción para bajar el overhead de fsync.
- Retención configurable por tenant.
- Dashboard mínimo de p95 y tasa de rechazo.
- Migrar el healthcheck a un endpoint con métricas Prometheus.

Ver [[Orion - storage]].
""",
    "Orion - incident-2026-09.md": """---
tags: [orion, incident, sqlite]
---

# Orion — incidente 2026-09-14

El disco creció sin control durante 6 horas. Causa: checkpoint starvation del
WAL. Un proceso de lectura de larga duración mantenía una transacción abierta y
el WAL no podía truncarse.

- Síntoma: `orion.db-wal` llegó a 18 GB.
- Mitigación: matar la lectura larga y forzar `PRAGMA wal_checkpoint(TRUNCATE)`.
- Fix permanente: `wal_autocheckpoint=1000` y límite de duración para lecturas
  analíticas.
- Lección: monitorear el tamaño del `-wal`, no solo el de la base.

Ver [[Orion - storage]].
""",
    "Orion - glossary.md": """---
tags: [orion, glossary]
---

# Orion — glosario

- **Evento**: medición con `tenant`, `metric`, `value`, `ts`.
- **Spool**: directorio donde se encolan eventos antes de persistirlos.
- **Checkpoint**: operación que copia páginas del WAL al archivo principal.
- **Skew**: diferencia entre el reloj del nodo y el reloj de referencia.

Ver [[Orion - overview]].
""",
    "Other/Unrelated.md": """---
tags: [vega, unrelated]
---

# Vega — notas sueltas

Vega es otro proyecto, sin relación con Orion. Usa Redis y un worker en Go.
""",
}


def base_data() -> dict:
    raw = json.loads((PLUGIN_SRC / "data.json").read_text(encoding="utf-8"))
    raw.update(
        {
            "projectsFolder": "Projects",
            "peopleFolder": "People",
            "excludedFolders": [],
            "notificationsEnabled": False,
            "showArchivedProjects": False,
            "showReleaseNotes": False,
            "lastSeenVersion": "2.6.0",
            "localApiEnabled": True,
            "localApiPort": 27400,
            "localApiToken": secrets.token_hex(16),
            "projectFilters": {},
            "scopeViews": {},
            "collapsedTasks": {},
            "collapsedProjects": [],
            "projectListViews": [],
            "projectList": {"filter": {}, "sort": [], "group": "none", "activeViewId": None},
        }
    )
    return raw


def write_data(vault: Path, port: int, token: str | None = None) -> None:
    data = base_data()
    data["localApiPort"] = port
    if token is not None:
        data["localApiToken"] = token
    plugin = vault / ".obsidian" / "plugins" / "project-manager"
    plugin.mkdir(parents=True, exist_ok=True)
    (plugin / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build_base() -> None:
    if BASE.exists():
        shutil.rmtree(BASE)
    (BASE / "Projects" / "🧪 Bench 2").mkdir(parents=True)
    (BASE / "Topics" / "Other").mkdir(parents=True)
    (BASE / "People").mkdir(parents=True)

    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    (BASE / "Projects" / "🧪 Bench 2" / "🧪 Bench 2.md").write_text(
        BENCH_PROJECT.format(created=now, updated=now), encoding="utf-8"
    )
    for name, text in NOTES.items():
        path = BASE / "Topics" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    (BASE / "AGENTS.md").write_text(VAULT_AGENTS, encoding="utf-8")

    obs = BASE / ".obsidian"
    plugin = obs / "plugins" / "project-manager"
    plugin.mkdir(parents=True, exist_ok=True)
    for name in ("manifest.json", "main.js", "styles.css"):
        shutil.copy2(PLUGIN_SRC / name, plugin / name)
    (obs / "community-plugins.json").write_text(
        json.dumps(["project-manager"], indent=2) + "\n", encoding="utf-8"
    )
    (obs / "app.json").write_text("{}\n", encoding="utf-8")
    write_data(BASE, 27400)


def install_cell(cell: str) -> None:
    meta = CELLS[cell]
    worktree: Path = meta["worktree"]
    if not worktree.is_dir():
        raise SystemExit(f"worktree missing: {worktree}")
    dst = worktree / ".bench-vault"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(BASE, dst, symlinks=True)
    write_data(dst, meta["port"], secrets.token_hex(16))
    print(f"{cell}: {dst} (dotpm port {meta['port']})")


if __name__ == "__main__":
    build_base()
    print(f"wrote {BASE}")
    for cell in CELLS:
        if CELLS[cell]["worktree"].is_dir():
            install_cell(cell)
