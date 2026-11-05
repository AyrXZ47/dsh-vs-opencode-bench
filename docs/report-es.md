> Versión para GitHub de la nota del vault. El original vive en Obsidian.

---
tags:
  - AI
  - benchmark
  - deepseek
  - opencode
  - dsh
---

# DSH vs OpenCode: ¿el proveedor o el harness?

> [!summary]
> Probé el mismo modelo, **DeepSeek V4.1 Flash en `max`**, en cuatro combinaciones de harness y proveedor. Dos suites, **40 sesiones oficiales**, tareas grandes y verificables. Resultado corto: **el gateway de OpenCode no hizo al modelo más tonto**. La diferencia real estuvo en el **tiempo y en las vueltas del harness**, no en la calidad.

## 1. Resumen en 30 segundos

- **Mismo cerebro:** DeepSeek V4.1 Flash, esfuerzo `max` en las cuatro celdas.
- **Cuatro trajes:** DSH y OpenCode, cada uno con DeepSeek directo y con OpenCode Go.
- **Dos suites:** coding, web, visión, skills; después webapp full-stack, 3D, bugfix, research y skills.
- **Calidad:** empate técnico. Solo hubo un fallo real, y fue del proveedor directo en un redondeo de `ledger`.
- **Velocidad:** `oc-ds` fue el más rápido; `dsh-oc` el más lento, por lejos.
- **Costo:** `oc-oc` es el más barato, incluso a precio nominal.
- **Conclusión:** OpenCode Go es una opción ganadora en valor. No es la más rápida, pero no degrada el modelo.

## 2. La pregunta

En Twitter se repite que DeepSeek V4.1 Flash “rinde más” en DSH que en OpenCode, y que la API de OpenCode lo sirve “más tonto” que la API directa de DeepSeek.

Hay tres variables mezcladas:

1. **El modelo** (el cerebro).
2. **El harness** (el piloto: prompt, herramientas, loop, skills).
3. **El proveedor** (la autopista: directo o gateway).

La pregunta real es: **¿cuál de las tres explica la diferencia que la gente percibe?**

## 3. Cómo se probó

Matriz 2×2:

| Celda | Harness | Proveedor |
|---|---|---|
| `dsh-ds` | DSH headless | DeepSeek directo |
| `dsh-oc` | DSH headless | OpenCode Go |
| `oc-ds` | OpenCode `run` | DeepSeek directo |
| `oc-oc` | OpenCode `run` | OpenCode Go |

### Verificación del modelo

- `GET https://api.deepseek.com/models` devuelve `id: deepseek-flash`, `name: "DeepSeek-V4.1-Flash"`.
- El gateway sirve `deepseek-v4.1-flash` con ese mismo nombre.
- DSH registra en el request: `reasoningEffort: max`.
- OpenCode registra en su DB: `variant: "max"`.

No comparé modelos distintos “por nombre”. Verifiqué que ambas rutas anuncian el mismo modelo y que las dos corren en `max`.

### Aislamiento

- Cuatro worktrees independientes.
- Cuatro `DSH_HOME` / `XDG_*` independientes.
- Cuatro vaults de prueba con notas sintéticas.
- Cada sesión dentro de bubblewrap: sin acceso al vault real, al harness, a las otras celdas ni a los tests ocultos.
- El worktree se resetea antes de cada fase.
- Sin commits: los cambios quedan en el working tree.

### Superficie

DSH se midió con `dsh headless --json`; OpenCode con `opencode run --standalone --format json`. **No es la TUI.** Mide el agent loop one-shot, no la experiencia interactiva.

## 4. Suite 1: coding, web, visión y skills

Cinco fases: smoke, coding (parser de telemetría con CRC16), investigación web (RDNA4 en Linux), visión (schematic NE555 + PDF) y skills (vault, dotpm, ponytail, security-audit).

### Calidad

| Celda | Coding oculto | Visión | Web (fuentes) | Auditoría |
|---|---:|---:|---|---:|
| `dsh-ds` | 10/10 | 5/5 | 12/14 verificadas | 2 hallazgos |
| `dsh-oc` | 10/10 | 5/5 | 6/6 | 4 hallazgos |
| `oc-ds` | 10/10 | 5/5 | 10/10 | 5 hallazgos |
| `oc-oc` | 10/10 | 5/5 | 10/10 | 5 hallazgos |

- Las cuatro resolvieron el coding one-shot y pasaron el test oculto.
- Las cuatro identificaron el NE555, `686 Hz`, `52.4 %` de duty y la inconsistencia del **RESET a GND**.
- En web, `dsh-ds` fue la más ambiciosa (14 fuentes), pero dos issues de GitLab quedaron detrás de un bot challenge. Las otras tres citaron menos fuentes y todas eran verificables.
- En skills, las cuatro crearon la nota y la tarea. `dsh-ds` fue la más concisa en la auditoría; las otras tres encontraron más problemas reales.

### Tiempo y costo

| Celda | Wall total | Tools | Costo nominal | Costo actual |
|---|---:|---:|---:|---:|
| `dsh-ds` | 825.1 s | 145 | $0.196140 | n/a |
| `dsh-oc` | 721.5 s | 151 | $0.102958 | n/a |
| `oc-ds` | **610.9 s** | 117 | $0.199287 | **$0.099644** |
| `oc-oc` | 927.5 s | 100 | $0.105187 | **$0.000000** (plan) |

`oc-ds` fue el más rápido y el de mejor costo medido. `oc-oc` fue el más lento de la suite 1, pero el más barato bajo el plan.

## 5. Suite 2: webapp, 3D, bugfix, research y skills

Cinco fases nuevas, más grandes y con tests automáticos:

1. **Webapp full-stack:** API REST + SQLite + frontend, solo stdlib. 13 tests ocultos.
2. **Rasterizador 3D:** proyección, culling, z-buffer, iluminación, PPM. 10 tests ocultos.
3. **Bugfix de ledger:** cuatro bugs sembrados, arreglar causa raíz y agregar regresiones.
4. **Research:** SQLite WAL, 400 palabras, fuentes verificables.
5. **Skills + MCP:** vault, dotpm, ponytail, security-audit.

### Puntaje (0–1)

| Celda | Webapp | 3D | Ledger | Research | Skills | Media |
|---|---:|---:|---:|---:|---:|---:|
| `dsh-ds` | 1.000 | 1.000 | **0.900** | 1.000 | 0.958 | **0.9717** |
| `dsh-oc` | 1.000 | 1.000 | 1.000 | 1.000 | 0.958 | **0.9917** |
| `oc-ds` | 1.000 | 1.000 | 1.000 | 1.000 | 0.958 | **0.9917** |
| `oc-oc` | 1.000 | 1.000 | 1.000 | 1.000 | 0.958 | **0.9917** |

### Tiempo

| Celda | Webapp | 3D | Ledger | Research | Skills | Total |
|---|---:|---:|---:|---:|---:|---:|
| `dsh-ds` | 365.0 | 255.7 | 147.5 | 64.3 | 123.2 | 955.7 s |
| `dsh-oc` | 1047.6 | 550.7 | 158.6 | 106.0 | 153.5 | **2016.4 s** |
| `oc-ds` | 208.6 | 136.3 | 94.1 | 145.3 | 84.8 | **669.1 s** |
| `oc-oc` | 318.0 | 316.4 | 218.6 | 46.2 | 85.3 | 984.5 s |

### Costo y tokens

| Celda | Input | Output+reasoning | Cache read | Costo nominal | Costo actual | Tools |
|---|---:|---:|---:|---:|---:|---:|
| `dsh-ds` | 93 466 | 156 547 | 3 534 463 | $0.237103 | n/a | 138 |
| `dsh-oc` | 327 665 | 192 466 | 6 211 456 | $0.183264 | n/a | 169 |
| `oc-ds` | 112 745 | 110 054 | 3 486 976 | $0.186809 | **$0.093405** | 110 |
| `oc-oc` | 317 728 | 126 192 | 4 530 176 | $0.136964 | **$0.000000** | 127 |

Los tokens **no son comparables 1:1** entre harnesses: DSH y OpenCode cuentan caché, pasos y títulos distinto. El costo nominal es de catálogo; el actual es el que reporta OpenCode. DSH no reporta costo.

## 6. El detalle que decidió la diferencia

En la suite 2, `dsh-ds` falló **un** test oculto de `ledger`:

```python
apply_discount(1001, 50)  # contrato: 501
# dsh-ds devolvió 500
```

Su implementación redondeó el descuento y después restó:

```python
discount = (1001 * 50 + 50) // 100  # 501
return 1001 - discount              # 500
```

Lo correcto era redondear el resultado final:

```python
return (1001 * (100 - 50) + 50) // 100  # 501
```

No es un problema de “inteligencia”: es un borde de redondeo. Pero cuenta, porque el test oculto sigue el contrato al pie de la letra. Las otras tres celdas lo resolvieron bien.

## 7. Qué significa

### El proveedor no hizo al modelo más tonto

En las dos suites, el gateway de OpenCode resolvió las mismas tareas que el directo:

- Webapp: 13/13 en las cuatro.
- 3D: 10/10 en las cuatro.
- Research: 1.0 en las cuatro, con fuentes reales.
- Skills: las cuatro crearon la nota y la tarea real en dotpm.

La única falla de corrección fue de `dsh-ds` (directo), no del gateway.

### El harness cambia la latencia y las vueltas

- `oc-ds` fue el más rápido: **669 s**.
- `dsh-oc` fue el más lento: **2016 s**, con **169 tool calls**.
- `dsh-oc` no tuvo errores de proveedor ni retries visibles: exploró más, corrió los tests muchas veces y consultó dotpm.
- `oc-oc` quedó en el medio: **984 s**, **127 tools**.

La diferencia de tiempo es real en esta muestra. La explicación más probable es el **tool loop** del harness, no una degradación del modelo.

### El costo depende de cómo lo mires

- Si pagás por token: `oc-oc` es el más barato a precio nominal ($0.137), y `oc-ds` el más barato medido ($0.093).
- Si tenés el plan prepago: `oc-oc` reporta **$0** por step.
- DSH no reporta costo; su nominal puede no coincidir con la factura.

## 8. Qué NO significa

- **No significa que las cuatro sean idénticas.** Es una muestra de una corrida por celda/fase.
- **No significa que OpenCode Go sea más rápido.** Fue más lento que el directo en las dos suites.
- **No significa que DSH sea malo.** Empató en calidad; el problema es el tiempo.
- **No significa que Mistral sea mejor o peor.** Mistral no se probó.
- **No hay significancia estadística.** n=1, efecto techo en 4 de 5 fases.
- **No es la TUI.** Es headless/one-shot. La experiencia interactiva puede cambiar.
- **El snapshot exacto del modelo no se expone.** Ambos se anuncian como V4.1 Flash; el build no se puede verificar por API.

## 9. Recomendación

Para tu caso:

1. **Default diario:** `oc-oc` (OpenCode + OpenCode Go). Mejor relación calidad/costo, y con tu plan el costo marginal es casi cero.
2. **Cuando la latencia importe:** `oc-ds` (OpenCode + DeepSeek directo). Fue el más rápido y el costo medido es bajo.
3. **Si querés DSH sí o sí:** `dsh-oc` antes que `dsh-ds` por costo, aceptando que es el más lento.
4. **No canceles Mistral/OC todavía por esto.** La suite no prueba Mistral. Si querés decidir con datos, corré la misma suite contra Mistral.

Frase para el video: **“El gateway no te hace al modelo más tonto; te puede hacer el harness más lento.”**

## 10. Guion para video

### 0:00 — Hook

“Mismo modelo. Cuatro combinaciones. 40 sesiones. La pregunta era si OpenCode me servía un DeepSeek más tonto. La respuesta me sorprendió.”

### 0:20 — La pregunta

“No es el modelo contra el modelo. Es el modelo, el harness y el proveedor. Tres variables, un solo cerebro.”

### 0:40 — El experimento

Mostrar la matriz 2×2. Explicar: DSH y OpenCode, directo y OpenCode Go, DeepSeek V4.1 Flash en `max`. Aislamiento con worktrees y bubblewrap. Tests ocultos.

### 1:20 — Suite 1

Mostrar la tabla de coding/visión/web/skills. “Las cuatro pasaron coding y visión. La diferencia apareció en tiempo y en cuántas fuentes verificaban.”

### 2:00 — Suite 2

Mostrar la tabla de scores. “Webapp 13/13, 3D 10/10, research 1.0 en las cuatro. Solo un fallo: un redondeo de `dsh-ds` en ledger.”

### 2:50 — El hallazgo

“El gateway no degradó el modelo. Pero `dsh-oc` tardó 2016 segundos y usó 169 herramientas. `oc-ds` tardó 669 y usó 110.”

### 3:30 — Los matices

“Una corrida por celda. Efecto techo. Tokens no comparables. Headless, no TUI. No es una sentencia final: es una señal fuerte.”

### 4:00 — Recomendación

“Para el día a día: `oc-oc`. Para latencia: `oc-ds`. Para DSH: `dsh-oc`. Y no canceles Mistral sin probarlo.”

### 4:30 — Cierre

“El modelo es el cerebro. El harness es el piloto. El proveedor es la autopista. Si la autopista es la misma, el cerebro no se vuelve más tonto: el viaje se hace más lento o más rápido.”

## 11. Transparencia

- **40 sesiones oficiales** (20 + 20), más una repetida.
- Una corrida de `oc-oc` en 3D listó `/tmp` y vio **nombres** de archivos de referencia que había dejado durante la validación. No leyó el contenido. La marqué como excluida, cerré `/tmp` en el sandbox y la repetí limpia. La repetida es la que cuenta.
- El vault real no se tocó durante las pruebas. Esta nota es la primera escritura deliberada en él.
- La instancia de Obsidian de prueba se cerró al terminar. El dotpm real sigue funcionando.
- Los tests ocultos y las soluciones de referencia viven fuera del sandbox; los agentes nunca los vieron.
