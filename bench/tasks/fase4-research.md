# Fase 4 — Investigación web: SQLite WAL

Investigá el modo WAL de SQLite y escribí un informe técnico en español de
**máximo 400 palabras**.

Cubrí:

1. Qué es WAL y por qué permite lectores y escritor concurrentes.
2. Archivos `-wal` y `-shm`, y cómo funciona un checkpoint.
3. Riesgos y limitaciones: crecimiento del WAL, checkpoint starvation, NFS o
   sistemas de archivos en red, y buenas prácticas (`busy_timeout`,
   `wal_autocheckpoint`, un solo escritor).
4. Una recomendación concreta para una app pequeña con SQLite y varios
   procesos.

Requisitos:

- Al menos 3 fuentes verificables con URL completa. No inventes fuentes.
- Citá la fuente de cada afirmación importante.
- Si no encontrás evidencia de algo, decilo explícitamente.
- No modifiques archivos del repo. La respuesta va en el mensaje final.
