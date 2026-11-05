# Bench2 — DSH vs OpenCode × DeepSeek directo vs OpenCode Go

**Fecha:** 2026-11-05  
**Host:** PC (NixOS, Ryzen 7 5700X, RX 7600)  
**Modelo único:** DeepSeek V4.1 Flash, esfuerzo `max` en las cuatro celdas.  
**Superficie:** `dsh headless --json` y `opencode run --standalone --format json` (no TUI).

## 1. Diseño

Matriz 2×2, cinco fases independientes. Cada fase arranca desde el mismo commit
semilla (`ca80d05`) y el worktree se resetea antes de correr.

| Celda | Harness / superficie | Proveedor | Modelo efectivo |
|---|---|---|---|
| `dsh-ds` | DSH `headless` | DeepSeek directo | `deepseek-official / deepseek-flash` |
| `dsh-oc` | DSH `headless` | OpenCode Go | `opencode-go / deepseek-v4.1-flash` |
| `oc-ds` | OpenCode `run --standalone` | DeepSeek directo | `deepseek/deepseek-flash#max` |
| `oc-oc` | OpenCode `run --standalone` | OpenCode Go | `opencode-go/deepseek-v4.1-flash#max` |

Fases:

1. **Webapp full-stack:** API REST + SQLite + frontend estático, solo stdlib.
2. **Rasterizador 3D:** proyección, culling, near clip, z-buffer, iluminación, PPM.
3. **Bugfix de ledger:** cuatro bugs sembrados, arreglar causa raíz y agregar regresiones.
4. **Investigación web:** SQLite WAL, 400 palabras, fuentes verificables.
5. **Skills + MCP:** `vault`, `dotpm`, `ponytail`, `security-audit`.

Cada fase tiene tests ocultos fuera del sandbox; el agente nunca los ve.

### Verificación del modelo y del esfuerzo

- `GET https://api.deepseek.com/models` devuelve `id: deepseek-flash`,
  `name: "DeepSeek-V4.1-Flash"`, `effort.supported_levels: low/high/max`.
- El gateway sirve `deepseek-v4.1-flash` con ese mismo nombre.
- DSH registra en el `request/header` de la sesión:
  - `dsh-ds`: `provider: deepseek-official`, `model: deepseek-flash`, `reasoningEffort: max`.
  - `dsh-oc`: `provider: opencode-go`, `model: deepseek-v4.1-flash`, `reasoningEffort: max`.
- OpenCode registra en su DB `{"id":"deepseek-flash","providerID":"deepseek","variant":"max"}`
  y `{"id":"deepseek-v4.1-flash","providerID":"opencode-go","variant":"max"}`.

## 2. Aislamiento

- Cuatro worktrees: `~/repos/bench2/{dsh-ds,dsh-oc,oc-ds,oc-oc}`.
- Cuatro entornos: `DSH_HOME` propio para DSH; `XDG_*` propio y `--standalone`
  para OpenCode. La auth se importó a cada store aislado desde el store global
  de OpenCode; el store global no se modificó.
- Cuatro vaults de prueba (`.bench-vault`) con notas sintéticas sobre “Orion”,
  puertos dotpm 27401–27404 y tokens distintos. El vault real `~/Sync/Notes`
  no se usó.
- Cada corrida dentro de bubblewrap: solo el worktree y el entorno de la celda
  son escribibles; se ocultan el vault real, `~/.dsh`, `~/.config/opencode`,
  `~/.local/share/opencode`, `~/.config/obsidian`, `/run/user/1000`, el harness,
  el bench anterior y las otras celdas. `/tmp` ahora es un tmpfs aislado.
- Sin commits: los cambios quedan en el working tree y se snapshottean.

### Incidente de contaminación (detectado y corregido)

Durante la validación previa dejé copias de la solución de referencia y de los
tests ocultos en `/tmp/bench2-ref.*`. Una corrida de `oc-oc` en la fase 2 hizo
`rg -l ... /tmp` y **listó los nombres** de esos archivos; no leyó su contenido.
La corrida se marcó como excluida y se repitió con `/tmp` aislado y sin copias
en `/tmp`. La corrida repetida dio 1.0 y es la que cuenta. Se escanearon las
otras 19 corridas: ninguna accedió a `bench2-ref` ni al harness.

## 3. Orden de ejecución

El orden de celdas se barajó por fase para reducir sesgo de orden/caché:

```
fase1-webapp    dsh-ds, oc-oc, oc-ds, dsh-oc
fase2-render3d  dsh-ds, oc-ds, oc-oc, dsh-oc
fase3-ledger    oc-ds, dsh-oc, oc-oc, dsh-ds
fase4-research  oc-oc, dsh-ds, dsh-oc, oc-ds
fase5-skills    oc-ds, dsh-ds, oc-oc, dsh-oc
```

## 4. Resultados por fase

### Puntaje (0–1)

| Celda | Webapp | Render3D | Ledger | Research | Skills | Media |
|---|---:|---:|---:|---:|---:|---:|
| `dsh-ds` | 1.000 | 1.000 | **0.900** | 1.000 | 0.958 | **0.9717** |
| `dsh-oc` | 1.000 | 1.000 | 1.000 | 1.000 | 0.958 | **0.9917** |
| `oc-ds` | 1.000 | 1.000 | 1.000 | 1.000 | 0.958 | **0.9917** |
| `oc-oc` | 1.000 | 1.000 | 1.000 | 1.000 | 0.958 | **0.9917** |

### Wall time por fase (segundos)

| Celda | Webapp | Render3D | Ledger | Research | Skills | Total |
|---|---:|---:|---:|---:|---:|---:|
| `dsh-ds` | 365.0 | 255.7 | 147.5 | 64.3 | 123.2 | **955.7** |
| `dsh-oc` | 1047.6 | 550.7 | 158.6 | 106.0 | 153.5 | **2016.4** |
| `oc-ds` | 208.6 | 136.3 | 94.1 | 145.3 | 84.8 | **669.1** |
| `oc-oc` | 318.0 | 316.4 | 218.6 | 46.2 | 85.3 | **984.5** |

### Tokens y costo (5 fases)

| Celda | Input | Output+reasoning | Cache read | Costo nominal | Costo actual | Tools |
|---|---:|---:|---:|---:|---:|---:|
| `dsh-ds` | 93 466 | 156 547 | 3 534 463 | $0.237103 | n/a | 138 |
| `dsh-oc` | 327 665 | 192 466 | 6 211 456 | $0.183264 | n/a | 169 |
| `oc-ds` | 112 745 | 110 054 | 3 486 976 | $0.186809 | **$0.093405** | 110 |
| `oc-oc` | 317 728 | 126 192 | 4 530 176 | $0.136964 | **$0.000000** | 127 |

- `nominal` usa tarifas de catálogo: directo $0.30/$1.20/$0.006 por 1M
  (input/output/cache read); OpenCode Go $0.15/$0.60/$0.003.
- OpenCode reporta su propio costo: `oc-ds` pagó ~$0.0934; `oc-oc` reporta 0
  porque el plan Go es prepago. DSH no reporta costo.
- Los tokens **no son comparables 1:1 entre harnesses**: DSH y OpenCode
  contabilizan caché y pasos distinto, y el total incluye arranque, MCP y
  generación de título.

## 5. Qué pasó en cada fase

### Fase 1 — Webapp

Las cuatro implementaron el contrato completo y pasaron **13/13** tests ocultos:
CRUD, validaciones, paginación, filtros, stats, 404/400/405, `Location`,
SQL injection literal, 80 creates concurrentes, persistencia entre servidores,
`data-testid` y JS con `fetch(`.

Tamaño: 550–753 líneas agregadas. Sin dependencias externas.

Diferencia observable: `dsh-oc` tardó **1047.6 s** y usó **55 tool calls**;
`oc-ds` tardó **208.6 s** con **34**. `dsh-oc` exploró más, corrió los tests
muchas veces y consultó dotpm; no hubo errores ni retries en stderr.

### Fase 2 — Render3D

Las cuatro pasaron **10/10** tests ocultos: header PPM, fondo, color exacto,
backface culling, z-buffer en ambos órdenes, perspectiva, iluminación,
near clip, validación y 1×1.

`dsh-oc` volvió a ser el más lento (550.7 s, 58 tool calls). `oc-ds` el más
rápido (136.3 s, 16 tool calls).

### Fase 3 — Ledger

`oc-ds`, `dsh-oc` y `oc-oc` pasaron **8/8**. `dsh-ds` pasó **7/8**.

Fallo real de `dsh-ds`:

```python
# contrato: apply_discount devuelve el monto final con .5 hacia arriba
apply_discount(1001, 50)  # esperado 501, obtenido 500
```

Su implementación redondeó el descuento y después restó:

```python
discount = (amount_cents * percent + 50) // 100  # 501
return amount_cents - discount                   # 500
```

Lo correcto es redondear el resultado final:

```python
return (amount_cents * (100 - percent) + 50) // 100  # 501
```

Su propio test de regresión codificó la expectativa equivocada
(`apply_discount(101, 50) == 50`); el test oculto usa el contrato.

### Fase 4 — Research

Las cuatro dieron **1.0** en el grader automático:

| Celda | Palabras | Fuentes | Fuentes verificadas |
|---|---:|---:|---|
| `dsh-ds` | 384 | 5 | 5/5 (`sqlite.org`) |
| `dsh-oc` | 373 | 5 | 5/5 (`sqlite.org`) |
| `oc-ds` | 394 | 4 | 4/4 (`sqlite.org`) |
| `oc-oc` | 334 | 4 | 4/4 (`sqlite.org`) |

Verificación manual: las cuatro explican WAL, `-wal`/`-shm`, checkpoint
PASSIVE, checkpoint starvation, NFS y `busy_timeout`. La afirmación repetida
“SQLite ≥ 3.51.3 corrige el WAL-reset bug” está confirmada en
`https://www.sqlite.org/wal.html` (“fixed in version 3.51.3 (2026-03-13)”).

### Fase 5 — Skills + MCP

Las cuatro crearon la nota `Topics/orion-bench.md` con 6 bullets y fuentes, y
la tarea `Bench2: revisar Orion` en `🧪 Bench 2` con descripción, `todo`,
`medium` y tag `bench2`. Las cuatro encontraron 4 hallazgos reales en
`ledger/ledger.py` (mutable default, float, rango de percent, merge de
intervalos que se tocan) y 5 de los 6 problemas sembrados en `service/`
(faltó el error verboso con `traceback`).

Puntaje: nota 1.0, dotpm 1.0, ponytail 1.0, security 0.8333 → **0.9583** en las
cuatro. Es una fase saturada: no discrimina proveedor ni harness.

## 6. Lectura

### Lo que los datos sostienen

- Las cuatro combinaciones completaron las cinco tareas sin fallos de auth,
  ruteo, sandbox ni MCP.
- **No apareció degradación del gateway**: `dsh-oc` y `oc-oc` pasaron webapp,
  render3D, research y skills igual que sus pares directos. La única falla de
  corrección fue de `dsh-ds` (directo), no del gateway.
- La diferencia de calidad más grande fue un detalle de redondeo en ledger, no
  una diferencia de “inteligencia” atribuible al proveedor.
- El gateway puede ser más lento: `dsh-oc` tardó 2016 s y usó 169 tool calls,
  contra 669 s y 110 de `oc-ds`. No hubo errores de proveedor; es el loop de
  herramientas/exploración del harness.

### Lo que no se sostiene

- Un ranking fino de costo: DSH no reporta costo y los tokens no son
  comparables entre harnesses. `oc-oc` reporta 0 por el plan prepago.
- “El gateway es igual de rápido”: `dsh-oc` fue 3× más lento que `oc-ds` en
  esta muestra, pero n=1 y el loop de tools no está normalizado.
- “Un harness es mejor que otro”: las tareas tuvieron efecto techo (4 de 5
  fases las pasaron las cuatro celdas). Solo ledger discriminó.
- Significancia estadística: una corrida por celda/fase, sin intervalos de
  confianza.

### Comparación con la suite anterior

La suite anterior (NE555, telemetry, RDNA4) también encontró paridad de
corrección y un `dsh-oc` relativamente lento. Esta suite agrega tareas más
grandes (webapp y 3D) y confirma el mismo patrón: **la diferencia observable
está en latencia/tool loop, no en corrección**. La única diferencia de
corrección apareció en un borde de redondeo de `dsh-ds`.

## 7. Sesgos y límites

1. **n=1 por celda/fase.** Sin repeticiones no hay significancia.
2. **Efecto techo.** Webapp, render3D y research las pasaron las cuatro;
   skills también quedó casi empatada. Solo ledger discriminó.
3. **Evaluación no ciega en research/skills.** Coding y 3D son tests
   automáticos; research y skills usan heurísticas de keywords + revisión
   manual. La revisión manual de research la hice yo, sabiendo la celda.
4. **Tokens no normalizados.** DSH y OpenCode cuentan caché/pasos distinto.
5. **Snapshot del modelo no expuesto.** Ambos se anuncian como V4.1 Flash,
   pero el build exacto no se puede verificar por API.
6. **Latencia incluye arranque, MCP, títulos y tool loops.** No es tiempo de
   primer token ni tiempo de cómputo puro.
7. **Headless, no TUI.** No mide la experiencia TUI de DSH ni de OpenCode.
8. **Incidente de `/tmp`.** Una corrida se excluyó y se repitió; las demás se
   escanearon y no accedieron a la referencia.

## 8. Artefactos

- Resultados crudos: `~/bench2-harness/results/<celda>/<fase>-<timestamp>/`
  - `events.jsonl`, `stderr.log`, `answer.md`, `summary.json`, `changes.patch`,
    `grade.json`, `grade.log`.
- Agregados: `~/bench2-harness/results/aggregate2.json` y `aggregate2.csv`.
- Orden: `~/bench2-harness/results/run-order.txt`.
- Corrida excluida: `~/bench2-harness/results/oc-oc/fase2-render3d-*-EXCLUDED-contaminated/`.
- Tests ocultos: `~/bench2-harness/tests/`.
- Referencia de validación: `~/bench2-harness/reference/` (nunca visible para
  los agentes; se usó para verificar que los tests fueran justos).
- Vaults de prueba con notas y tareas: `~/repos/bench2/<celda>/.bench-vault/`.

## 9. Recomendación

- No hay evidencia de que OpenCode Go sirva un modelo “más tonto” en esta
  muestra. La paridad de corrección es fuerte en tareas grandes y verificables.
- Si te importa la latencia, el punto a investigar es el tool loop de
  **DSH + OpenCode Go**: fue el más lento y el que más tools usó, sin errores
  de proveedor.
- Para volumen barato, `oc-ds` fue el mejor balance tiempo/costo real en esta
  suite; `oc-oc` es barato bajo el plan pero más lento.
- Antes de decidir cancelar algo, corré 3 repeticiones de webapp y ledger con
  temperatura/seed fijos y evaluación ciega. El efecto techo es el mayor
  problema de estas dos suites.
