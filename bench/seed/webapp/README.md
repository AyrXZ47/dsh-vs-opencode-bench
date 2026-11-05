# webapp

API de tareas con SQLite y un frontend estático. Solo stdlib de Python.

## Contrato

`webapp/app.py` debe exponer:

```python
def make_server(host: str, port: int, db_path: str) -> ThreadingHTTPServer
```

El servidor se arranca desde los tests con `port=0`; `server.server_address[1]`
da el puerto real. Debe crear el esquema si la base no existe.

### Modelo

Tarea:

- `id`: entero autoincremental.
- `title`: string, 1..120 caracteres después de `strip()`.
- `description`: string, 0..2000 caracteres. Default `""`.
- `status`: `todo` | `doing` | `done`. Default `todo`.
- `priority`: `low` | `medium` | `high`. Default `medium`.
- `created_at`: ISO 8601 UTC, por ejemplo `2026-11-05T12:00:00Z`.

### Endpoints

- `GET /api/tasks?status=&limit=&offset=`
  - `status` opcional; si viene, debe ser válido, si no `400`.
  - `limit` default 20, rango 1..100; `offset` default 0, mínimo 0. Inválidos: `400`.
  - Devuelve un array JSON ordenado por `id ASC`.
- `POST /api/tasks`
  - `Content-Type: application/json`, cuerpo objeto.
  - Valida campos; campos desconocidos se ignoran.
  - `201` con la tarea y header `Location: /api/tasks/{id}`.
  - JSON inválido o campos inválidos: `400` con `{"error": "<mensaje>"}`.
- `GET /api/tasks/{id}` -> `200` tarea o `404` con `{"error": ...}`.
- `PATCH /api/tasks/{id}` -> actualización parcial; mismas validaciones; `200` o `404`/`400`.
- `DELETE /api/tasks/{id}` -> `204` sin cuerpo o `404`.
- `GET /api/stats` -> `{"todo": n, "doing": n, "done": n, "total": n}`.
- `GET /` -> HTML con `data-testid="task-list"`, `data-testid="new-task-form"`,
  `data-testid="status-filter"`, y un `<script>` (inline o con `src`) cuyo
  JavaScript use `fetch(`.
- `GET /static/app.js` -> JavaScript válido.

Métodos no soportados en rutas conocidas: `405`.

### Requisitos

- SQL parametrizado (nada de f-strings con input).
- Conexiones seguras entre threads; el servidor debe atender concurrencia.
- Persistencia real en `db_path`.
- Tests visibles: `python3 -m unittest discover -s webapp/tests -v`.
