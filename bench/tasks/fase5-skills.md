# Fase 5 — Skills + MCP

Vault de prueba de esta celda: `{{VAULT}}`. No leas ni escribas en el vault
real `~/Sync/Notes`.

Tareas:

1. Usá la skill `vault` para buscar las notas que mencionen "Orion"
   (case-insensitive). Creá `{{VAULT}}/Topics/orion-bench.md` con:
   - 6 bullets con los hechos clave del proyecto (no inventes);
   - sección final `## Fuentes` con wikilinks a las notas usadas.
2. Usá el MCP `dotpm` para crear una tarea en el proyecto `🧪 Bench 2`:
   - título: `Bench2: revisar Orion`
   - descripción: `Comparar proveedores y harnesses.`
   - status: `todo`
   - priority: `medium`
   - tags: `["bench2"]`
   Si el MCP no responde, reportalo y no inventes la tarea.
3. Usá la skill `ponytail` para revisar `ledger/ledger.py` y `webapp/app.py`.
   Reportá al menos 2 hallazgos reales con `archivo:línea`. Si no hay dos
   hallazgos reales, decilo.
4. Usá la skill `security-audit` en modo guidance (no full audit, no artifacts)
   sobre `service/`. Reportá como máximo 5 hallazgos verificables con
   `archivo:línea`. No ejecutes código del target.
5. No hagas commit. Dejá los cambios en el working tree.

En la respuesta final resumí: nota creada, tarea creada, hallazgos de ponytail
y hallazgos de security-audit.
