# Fase 1 — Webapp full-stack

Trabajás en `webapp/`. No toques otras carpetas.

Implementá el contrato completo de `webapp/README.md`: API REST de tareas con
SQLite y frontend estático, solo stdlib de Python.

Requisitos:

- `make_server(host, port, db_path)` crea (sin arrancar) un `ThreadingHTTPServer`.
- Esquema, validaciones, paginación, filtros, stats, 404/400/405 y `Location`.
- SQL parametrizado; nada de concatenar input en queries.
- Concurrencia real: el servidor debe atender requests simultáneos.
- Persistencia en `db_path`.
- `GET /` con los `data-testid` pedidos y JS que use `fetch(`.
- `GET /static/app.js` sirve JavaScript válido.
- `python3 -m unittest discover -s webapp/tests -v` debe pasar.

No agregues dependencias. No hagas commit. Al terminar, resumí qué
implementaste y el resultado de los tests visibles.
