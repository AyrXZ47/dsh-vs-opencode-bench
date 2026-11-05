# Benchmark: DSH vs OpenCode × DeepSeek directo vs OpenCode Go

**Fecha:** 2026-11-05  
**Host:** PC (NixOS, Ryzen 7 5700X, RX 7600)  
**Objetivo:** medir si la diferencia percibida entre DeepSeek servido directo y servido por OpenCode Go depende del harness, del proveedor o de ambos, y comparar DSH contra OpenCode con el mismo modelo.

## 1. Diseño

Matriz 2×2, una celda por combinación:

**Superficie ejecutada:** DSH se corrió con `dsh headless --json` (perfil `headless`), **no** con `dsh tui`. OpenCode se corrió con `opencode run --standalone --format json`, **no** con la TUI interactiva. Los perfiles TUI de DSH se prepararon y validaron con `--dump-config`, pero no se usaron para las corridas puntuadas. Los resultados miden el agent loop one-shot/headless, no la UX ni el bundle TUI.

| Celda | Harness / superficie | Proveedor | Modelo efectivo |
|---|---|---|---|
| `dsh-ds` | DSH `headless` | DeepSeek directo | `deepseek-official / deepseek-flash` |
| `dsh-oc` | DSH `headless` | OpenCode Go | `opencode-go / deepseek-v4.1-flash` |
| `oc-ds` | OpenCode `run --standalone` | DeepSeek directo | `deepseek/deepseek-flash#max` |
| `oc-oc` | OpenCode `run --standalone` | OpenCode Go | `opencode-go/deepseek-v4.1-flash#max` |

Las cuatro celdas corrieron las mismas cinco fases, en secuencia, sobre el mismo commit semilla (`1219392`):

0. smoke de autenticación;
1. coding one-shot con test de aceptación oculto;
2. investigación web con fuentes;
3. visión + PDF;
4. skills (`vault`, `ponytail`, `security-audit`) + MCP `dotpm`.

### Aislamiento

- Cuatro worktrees independientes: `~/repos/bench/{dsh-ds,dsh-oc,oc-ds,oc-oc}`.
- Cuatro entornos independientes: `env-dsh-*` con `DSH_HOME` propio; `env-oc-*` con `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME`, `XDG_STATE_HOME` y `XDG_RUNTIME_DIR` propios.
- OpenCode corrió siempre con `--standalone` y su propio store de auth importado; nunca usó el servicio de fondo global.
- Cuatro vaults de prueba dentro de cada worktree (`.bench-vault`), con servidores dotpm en puertos 27301–27304 y tokens distintos. El vault real `~/Sync/Notes` no se usó.
- Cada corrida se ejecutó dentro de bubblewrap: solo el worktree y el entorno de la celda eran escribibles; el vault real, el harness (tareas/tests ocultos), los otros worktrees/envs y el socket CLI de Obsidian estaban ocultos. En DSH, el sandbox interno se puso en `danger-full-access` porque el confinamiento real era el bubblewrap externo.
- Sin commits: los cambios quedaron en el working tree y se snapshottearon por fase.
- El vault real se verificó después: no existe `bench-result.md` ni tarea `Bench: revisar resultados` en él. El Obsidian de prueba se abrió en un `--user-data-dir` separado y se cerró al terminar; la app real se relanzó y su dotpm volvió a responder en 27201.

## 2. Fase 0 — Smoke

| Celda | Resultado | Wall | Input | Output+reasoning | Costo nominal |
|---|---|---:|---:|---:|---:|
| `dsh-ds` | `OK DSH-DS` | 5.7 s | 2 886 | 35 | $0.000976 |
| `dsh-oc` | `OK DSH-OC` | 8.9 s | 14 228 | 78 | $0.002181 |
| `oc-ds` | `OK OC-DS` | 2.7 s | 174 | 5 | $0.000106 |
| `oc-oc` | `OK OC-OC` | 4.4 s | 47 | 5 | $0.000034 |

Las cuatro autenticaciones y rutas de modelo funcionaron.

## 3. Fase 1 — Coding one-shot

Tarea: crear `packets/src/telemetry.rs` con `parse_packet`, `Packet`, `Endianness`, `ParseError`, CRC16/CCITT-FALSE y validaciones en orden. Test oculto: 10 casos (little/big, payload vacío, truncado, endianness inválida, length mismatch, CRC inválido, CRC sobre header+payload).

| Celda | Test oculto | Tests propios | fmt | clippy | Líneas | Wall | Input | Out+rea | Cache read | Costo nominal | Costo actual | Tools |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `dsh-ds` | **10/10** | 9 | OK | OK | 176 | 62.5 s | 8 106 | 9 396 | 282 624 | $0.015403 | n/a | 13 |
| `dsh-oc` | **10/10** | 8 | OK | OK | 164 | 77.6 s | 31 795 | 7 399 | 129 408 | $0.009597 | n/a | 12 |
| `oc-ds` | **10/10** | 8 | OK | OK | 167 | 17.0 s | 4 138 | 3 095 | 45 312 | $0.005227 | $0.002614 | 5 |
| `oc-oc` | **10/10** | 9 | OK | OK | 182 | 63.5 s | 8 724 | 4 972 | 60 544 | $0.004473 | $0.000000 | 5 |

**Resultado:** las cuatro celdas resolvieron la tarea y pasaron el test oculto 10/10. No hubo diferencia de corrección. `oc-ds` fue claramente la más eficiente (17 s, 5 tool calls, costo actual más bajo); `dsh-ds` fue la más lenta y costosa; `dsh-oc` y `oc-oc` quedaron en el medio. El código de las cuatro pasó `cargo fmt --check` y `clippy -D warnings`.

## 4. Fase 2 — Web research

Tarea: estado de RDNA4 en Linux (scheduler, memoria, bug), máximo 400 palabras, ≥3 fuentes verificables.

| Celda | Palabras | URLs | Verificadas | No verificadas | Evaluación |
|---|---:|---:|---:|---|---|
| `dsh-ds` | 358 | 14 | 12/14 | GitLab #5821/#5663 (bot challenge) | Muy amplia y detallada; el 12/14 está soportado. Las fechas/estados de los dos work items de GitLab no se pudieron verificar. |
| `dsh-oc` | 351 | 6 | 6/6 | — | La más cauta: CVE-2026-89812, SteamOS #2811, Arch wiki, lists.freedesktop, notebookcheck y Phoronix; todas soportan lo afirmado. |
| `oc-ds` | 376 | 10 | 10/10 | — | Precisas: UMQ 6.16, fair→FIFO en 7.2, TTM/DMEMCG 7.3, GDS/GWS/OA cero, idle RDNA4; fuentes docs/lists/lkml/Phoronix. |
| `oc-oc` | 311 | 10 | 10/10 | — | Precisas: docs Linux 7.4-rc1, `user_queue`, ReBAR, CVE-2026-89813, Phoronix 6.19; fuentes soportan lo afirmado. |

Verificación destacada:

- UMQ inicial para RDNA3/RDNA4 en Linux 6.16, detrás de parámetro de módulo: Phoronix y docs.kernel.org.
- Política `fair` del DRM scheduler revertida a FIFO en Linux 7.2 por regresión en RX 9070 XT; parches para 7.3: Phoronix.
- TTM/DMEMCG más agresivo en 7.3, trabajo de Valve/Natalie Vock: Phoronix.
- CVE-2026-89812 (MES) y CVE-2026-89813 (KIQ): OpenCVE; confirman `no_scheduler`, force-completion y versiones corregidas 6.12.114 / 6.18.57 / 7.2.5 / 7.3.
- SteamOS #2811: real, abierto, RX 9070 XT pierde ~7.4 GiB de VRAM a GTT tras suspend; coincide con lo reportado por `dsh-oc`.
- GDS/GWS/OA de tamaño cero en RDNA4: parche de abril 2026 en lists.freedesktop/lkml.
- ReBAR/SAM solo UEFI en RX 9000: notebookcheck.

**Resultado:** las cuatro respuestas son técnicamente sólidas y dentro del límite de palabras. `dsh-oc`, `oc-ds` y `oc-oc` tienen todas sus fuentes verificables. `dsh-ds` es la más ambiciosa y detallada, pero su única debilidad es que las fechas/estados de los issues de GitLab no son verificables por la protección anti-bot; el resto de sus afirmaciones sí está respaldado. `dsh-oc` es la más cauta y la que mejor separa “soportado” de “no encontré evidencia”.

## 5. Fase 3 — Visión + PDF

Tarea: analizar un schematic NE555 y un PDF de especificaciones, calcular frecuencia/duty y detectar inconsistencia.

| Celda | Wall | Input | Out+rea | Cache read | Costo nominal | Costo actual | Corrección |
|---|---:|---:|---:|---:|---:|---:|---|
| `dsh-ds` | 102.8 s | 22 738 | 15 130 | 252 416 | $0.026492 | n/a | **5/5** |
| `dsh-oc` | 107.4 s | 21 302 | 12 420 | 235 392 | $0.011353 | n/a | **5/5** |
| `oc-ds` | 71.8 s | 8 990 | 10 786 | 111 872 | $0.016311 | $0.008156 | **5/5** |
| `oc-oc` | 92.4 s | 8 885 | 6 515 | 79 744 | $0.005481 | $0.000000 | **5/5** |

Las cuatro identificaron correctamente:

- NE555 astable, Vcc 9 V, R1 1 kΩ, R2 10 kΩ, C 100 nF, R3 330 Ω, C2 10 nF.
- `f = 1.44 / ((R1 + 2R2)C) ≈ 686 Hz`.
- `duty = (R1+R2)/(R1+2R2) ≈ 52.4 %`.
- La inconsistencia: pin 4 (RESET) atado a GND; el PDF dice que RESET es activo bajo y debe atarse a VCC. Efecto: el timer queda en reset, OUT bajo, C descargado, f = 0; corrección: pin 4 a VCC (directo o pull-up 10 kΩ).
- No modificaron archivos.

**Resultado:** empate técnico 5/5. Las respuestas DSH son algo más extensas; las de OpenCode más concisas. No hubo diferencia de capacidad.

## 6. Fase 4 — Skills + MCP

Tarea: buscar NixOS en el vault, crear nota con 8 bullets y fuentes, crear tarea en dotpm (`🧪 Benchmark`), revisar con ponytail y auditar `security-audit` en modo guidance.

| Celda | Nota | Bullets | Fuentes | Tarea dotpm | Ponytail | Hallazgos audit | Commit |
|---|---|---:|---:|---|---|---|---|
| `dsh-ds` | `Topics/bench-result.md` | 8 | 4 | Correcta | Sin hallazgos reales | 2/2 verificados | No |
| `dsh-oc` | `Topics/bench-result.md` | 8 | 6 | Correcta | Sin hallazgos reales | 4/4 verificados | No |
| `oc-ds` | `Topics/bench-result.md` | 8 | 12 | Correcta | Sin hallazgos reales | 5/5 verificados* | No |
| `oc-oc` | `Topics/bench-result.md` | 8 | 8 | Correcta | Sin hallazgos reales | 5/5 verificados | No |

La tarea creada en las cuatro fue exactamente `Bench: revisar resultados`, descripción `Comparar DSH+DeepSeek directo vs DSH+OpenCode Go.`, status `todo`, priority `medium`, tag `bench`, en el proyecto `🧪 Benchmark`. Ninguna se creó en `💻 Dev`.

Hallazgos de seguridad verificados contra el código:

1. **Descarga de materiales sin inscripción/pago:** `routes/html.rs:147` solo exige sesión; `services/storage.rs:69` lee por `file_id`; los ids salen en el catálogo/detalle público. Es el `shortcut` declarado en `docs/ARCHITECTURE.md:77-78`.
2. **Detalle público de cursos no publicados:** `routes/catalog.rs:22-27` llama a `services/catalog.rs:113-119`, que no filtra `published`; el listado sí filtra (`:99-101`).
3. **Catálogo público devuelve el curso completo:** `services/catalog.rs:40-41` copia `modules` (con `video_url`) y `materials` (con `file_id`); `routes/catalog.rs:18` lo sirve sin autenticación.
4. **Errores internos al cliente:** `error.rs:22` muestra el mensaje de `AppError::Db`; `db.rs:20` lo construye desde el driver. `services/auth.rs:68/72/76` también usa `AppError::Db` para errores de Argon2 (el hallazgo de `oc-ds` lo llamó “Mongo”; el problema de fondo es el mismo: detalle interno expuesto).
5. **Enumeración/timing de login:** `services/auth.rs:138` retorna antes de verificar Argon2 si el correo no existe; `routes/auth.rs:32` no tiene rate limit. `services/auth.rs:121-124` también revela si un correo ya existe en el registro.
6. **Pago sandbox confirmable por el propio alumno:** `routes/enrollment.rs:20-24` + `services/enrollment.rs:159-170`; es el flujo demo declarado, pero sería un bypass si se activa un gateway real sin retirarlo.

**Resultado:** las cuatro cumplieron la funcionalidad. `dsh-oc`, `oc-ds` y `oc-oc` hicieron una auditoría más profunda (4–5 hallazgos); `dsh-ds` fue más concisa (2 hallazgos, ambos válidos). Ninguna inventó hallazgos en ponytail: el código de `packets` pasó tests, fmt y clippy.

## 7. Métricas totales (5 fases)

| Celda | Wall total | Input | Out+reasoning | Cache read | Costo nominal | Costo actual | Tools | Steps |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `dsh-ds` | 825.1 s | 162 520 | 103 815 | 3 801 088 | $0.196140 | n/a | 145 | 82 |
| `dsh-oc` | 721.5 s | 314 893 | 77 303 | 3 114 368 | $0.102958 | n/a | 151 | 67 |
| `oc-ds` | **610.9 s** | 192 785 | 97 294 | 4 116 480 | $0.199287 | **$0.099644** | 117 | 63 |
| `oc-oc` | 927.5 s | 285 961 | 83 642 | 4 036 352 | $0.105187 | **$0.000000** | 100 | 61 |

Notas de costo:

- `nominal` usa las tarifas del catálogo pi-ai: DeepSeek directo $0.30/$1.20/$0.006 por 1M (input/output/cache read); OpenCode Go `deepseek-v4.1-flash` $0.15/$0.60/$0.003.
- OpenCode reporta su propio `cost` por step: en `oc-ds` usa efectivamente $0.15/$0.60; en `oc-oc` reporta 0 porque el plan OpenCode Go es prepago. El `nominal` de `oc-oc` es el valor de mercado, no lo que se paga con el plan.
- DSH no expone costo por step; el `nominal` de `dsh-ds` puede estar sobreestimado si la cuenta directa tiene otra tarifa. El `nominal` de `dsh-oc` es el valor de mercado del gateway.
- El total incluye las 5 fases y todos los tool loops; no es el costo de una sola tarea.

## 8. Lectura de los resultados

### ¿El proveedor hizo al modelo “más tonto”?

En esta muestra, **no**. DeepSeek directo y OpenCode Go resolvieron las cuatro tareas de coding/visión/skills con la misma corrección. Las respuestas web de ambos proveedores fueron técnicamente sólidas y con fuentes reales. No apareció un deterioro de calidad atribuible al gateway.

La diferencia visible fue de eficiencia y de comportamiento de tooling:

- `oc-ds` (OpenCode + directo) fue la celda más rápida y la de menor costo actual en coding y en total.
- `dsh-oc` (DSH + OpenCode Go) fue la más rápida en web y la más cauta con las fuentes.
- `dsh-ds` (DSH + directo) fue la más lenta y la más cara en nominal, y la única con fuentes no verificables (GitLab). No mostró una ventaja de calidad.
- `oc-oc` (OpenCode + OpenCode Go) fue correcta y barata bajo el plan, pero la más lenta en total por la fase web.

### ¿El harness importa?

Sí, pero en este benchmark importó sobre todo en **tool loops, latencia y verbosidad**, no en capacidad bruta:

- OpenCode directo fue el más eficiente en coding (17 s, 5 tool calls, 167 líneas, 10/10 oculto).
- DSH OpenCode Go fue el más eficiente en web (200 s, 6 fuentes, todas verificables) y el más cauto.
- DSH directo generó la respuesta web más amplia (14 fuentes), pero pagó con 355 s y el mayor costo nominal; además, sus dos issues de GitLab no son verificables.
- La “magia one-shot” de DSH no se tradujo en una ventaja de corrección: las cuatro celdas resolvieron one-shot; la diferencia fue de costo/tiempo/estilo.

### ¿Vale la pena cancelar OpenCode/Mistral?

Con este tamaño de muestra, **no hay evidencia para cancelar OpenCode Go por calidad**. El gateway sirvió el mismo modelo sin degradación observable y fue competitivo en costo/velocidad. Si el plan de Mistral a $5.99 ofrece el mismo modelo con tool calling/visión equivalentes, es un reemplazo económicamente atractivo; pero conviene verificar límites, tool calling, imágenes y estabilidad antes de cancelar.

Recomendación práctica:

1. No canceles nada todavía.
2. Corre 3 repeticiones de fase 1 y fase 2 con tu tarea real más difícil; una sola corrida no da significancia.
3. Usa el gateway barato para volumen y el directo para casos de máxima criticidad si querés independencia del gateway.
4. Si tenés que elegir un default para one-shot coding en esta PC: **OpenCode directo** fue el mejor balance velocidad/corrección/costo en esta muestra. Si priorizás investigación web cauto y verificable: **DSH + OpenCode Go** fue el mejor.
5. Verificá a mano los issues de GitLab que citó `dsh-ds` antes de confiar en sus estados/fechas.

## 9. Limitaciones

- Una corrida por celda/fase; los modelos son estocásticos y no hay intervalo de confianza.
- **No se probó la TUI interactiva.** DSH se midió con `dsh headless` (perfil `headless`, que habilita `tool-web` y tiene otro bundle/prompt que `dsh tui`); OpenCode se midió con `opencode run --standalone` (one-shot), no con la TUI interactiva. El bundle TUI de DSH deshabilita `tool-web` y cambia el prompt/persona; si la hipótesis es que la “magia” está específicamente en la TUI de DSH, estos resultados no la confirman ni la refutan. Los perfiles TUI quedaron preparados y validados con `--dump-config`, listos para una tanda TUI separada.
- Las tareas son sintéticas y acotadas; no reemplazan tu proyecto real.
- La fase web depende de buscadores y de la fecha (noviembre 2026); algunas fuentes (Phoronix, GitLab) bloquean scrapers. Phoronix se verificó vía Jina Reader; GitLab quedó detrás de un bot challenge.
- El test oculto solo cubre coding; visión y skills se evaluaron a mano contra el resultado esperado y el código.
- Los costos DSH son nominales (pi-ai), no una factura; los de OpenCode son los que reporta su propio JSON. El plan OpenCode Go es prepago y reporta 0 por step.
- El confinamiento externo (bubblewrap) y el `danger-full-access` interno de DSH son una decisión de aislamiento de esta prueba; no es exactamente la configuración de tu TUI diaria. Afecta tool loops, no el modelo.
- El vault real no fue escrito; los vaults de prueba quedaron en los worktrees. El Obsidian de prueba se cerró y la app real se relanzó.

## 10. Reproducción

- Resultados crudos: `~/bench-harness/results/<celda>/<fase>-<timestamp>/`
  - `events.jsonl`, `stderr.log`, `answer.md`, `summary.json`, `changes.patch`, `hidden-test.log`.
- Agregados: `~/bench-harness/results/aggregate.json`, `aggregate.csv`.
- Test oculto: `~/bench-harness/tests/telemetry_acceptance.rs`.
- Runner: `~/bench-harness/bin/run-cell.sh <celda> <fase>`.
- Sandbox: `~/bench-harness/bin/sandbox-run.sh`.
- Setup de entornos: `~/bench-harness/tools/make_dsh_home.py`, `make_oc_home.py`, `make_vault.py`.
- Las claves se leyeron del store de OpenCode en runtime; no se escribieron en los scripts ni en los worktrees.

## 11. Sesgos y qué conclusiones no se sostienen

La ejecución fue real y verificable, pero el diseño tiene sesgos que limitan lo que se puede concluir.

### Verificado (sin sesgo de procedencia)

- Las cuatro celdas usaron los proveedores declarados: el session log de DSH registra `provider: deepseek-official / model: deepseek-flash` y `provider: opencode-go / model: deepseek-v4.1-flash`; la DB de OpenCode registra el mismo `model` por sesión.
- El modelo directo `deepseek-flash` se llama **DeepSeek-V4.1-Flash** en `GET https://api.deepseek.com/models`; el gateway sirve `deepseek-v4.1-flash` con el mismo nombre. La identidad de modelo está confirmada; el snapshot/build exacto no se expone.
- Las sumas de tokens del reporte coinciden exactamente con la fuente: en DSH, suma de `assistant/message.usage` del session log; en OpenCode, suma de `session_message` assistant de la DB. La diferencia del agregado de OpenCode es la llamada de título de sesión, que no forma parte del stream.
- Una prueba en vivo con nonce aleatorio respondió el nonce exacto en las cuatro celdas.

### Sesgos presentes

1. **Sesgo de confirmación por el framing de Qwen.** El protocolo de 4 celdas, las fases y las hipótesis (“DSH+directo gana por poco”, “OC proxy pierde por system prompt”, “empate en web/visión”, “sorpresa en skills”) vinieron de esa conversación. No ajusté configuraciones para confirmarlas, pero elegí tareas e interpreté resultados con ese prior. El reporte repite ese marco.
2. **Evaluación no ciega.** Yo sabía qué celda produjo cada respuesta al calificar web, visión y skills. Los tests de coding son automáticos y no tienen este sesgo; las etiquetas cualitativas (“más cauta”, “más amplia”) sí.
3. **n=1 por celda/fase.** Sin repeticiones no hay intervalo de confianza. Las diferencias de tiempo/costo pueden ser ruido o caché, no efecto de proveedor.
4. **Efecto techo.** Coding y visión las resolvieron las cuatro; una tarea que todas pasan no discrimina. La “ausencia de diferencia” es evidencia débil de equivalencia.
5. **Orden y caché.** Las corridas fueron secuenciales y en orden fijo (`dsh-ds`, `dsh-oc`, `oc-ds`, `oc-oc`). `oc-ds` corrió después de `dsh-ds` contra el mismo proveedor directo y arrancó con caché caliente; `dsh-ds` corrió primero, en frío. Eso puede explicar parte de la ventaja de costo/velocidad de `oc-ds` y parte del sobrecosto de `dsh-ds`.
6. **Asimetrías entre harnesses.** DSH usa búsqueda web nativa; OpenCode usa el MCP `duckduckgo`. DSH reporta tokens con otra convención de caché que OpenCode. El tiempo incluye arranque del harness y, en OpenCode, la generación de título. Nada de eso es comparable 1:1 entre harnesses.
7. **El factor “proveedor” no es una sola variable.** Dentro de DSH, directo usa el adaptador nativo `anthropic-messages` y OpenCode Go usa `openai-completions` vía pi-ai; además cambian retry policy y catálogo. La diferencia medida mezcla proveedor + protocolo + adaptador.

### Qué conclusiones no se sostienen

- El ranking fino de velocidad y costo entre celdas.
- “`dsh-ds` es el más caro” como propiedad del harness/proveedor: puede ser caché fría + orden.
- “`oc-ds` es el mejor balance” como resultado robusto: puede ser orden/caché.
- “El gateway no degrada el modelo” como equivalencia demostrada: solo hay ausencia de degradación en 5 tareas con efecto techo y n=1.
- Cualquier afirmación de que un harness es mejor que otro en capacidad.

### Qué sí se sostiene

- La infraestructura, el aislamiento y la procedencia de los datos.
- Que las cuatro combinaciones completaron las tareas sin fallos de autenticación ni de ruteo.
- Que no se observó una degradación grosera atribuible al gateway en esta muestra.
- Que el modelo servido por ambas rutas se identifica como DeepSeek-V4.1-Flash.

### Cómo des-sesgar

1. 3+ repeticiones por celda, orden aleatorizado o intercalado, y temperatura/seed fijos si el proveedor lo permite.
2. Evaluación ciega: renombrar salidas, calificar sin saber la celda; tests automáticos para coding y rúbrica con verificación scriptada de URLs para web.
3. Mismo backend de búsqueda en ambos harnesses (o una ablación separada de búsqueda).
4. Normalizar contabilidad: medir tiempo desde el primer token hasta el `turn_end`, excluir título y arranque, y reportar tokens por convención de cada proveedor sin sumarlos entre harnesses.
5. Preregistrar hipótesis y análisis antes de correr.
6. Tareas más difíciles, con puntaje parcial, que no las pase todo el mundo.
