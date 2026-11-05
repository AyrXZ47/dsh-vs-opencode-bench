"""Reference implementation of the taskboard API (not shipped to agents)."""

import json
import re
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

STATUSES = ("todo", "doing", "done")
PRIORITIES = ("low", "medium", "high")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'todo',
    priority TEXT NOT NULL DEFAULT 'medium',
    created_at TEXT NOT NULL
)
"""

INDEX_HTML = """<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>Taskboard</title></head>
<body>
<h1>Taskboard</h1>
<form data-testid="new-task-form">
  <input name="title" required>
  <button type="submit">Crear</button>
</form>
<select data-testid="status-filter">
  <option value="">Todas</option>
  <option value="todo">Todo</option>
  <option value="doing">Doing</option>
  <option value="done">Done</option>
</select>
<ul data-testid="task-list"></ul>
<script src="/static/app.js"></script>
</body>
</html>
"""

APP_JS = """
const list = document.querySelector('[data-testid="task-list"]');
async function refresh() {
  const response = await fetch('/api/tasks');
  const tasks = await response.json();
  list.innerHTML = '';
  for (const task of tasks) {
    const item = document.createElement('li');
    item.textContent = task.title + ' [' + task.status + ']';
    list.appendChild(item);
  }
}
document.querySelector('[data-testid="new-task-form"]').addEventListener('submit', async (event) => {
  event.preventDefault();
  const title = event.target.elements.title.value;
  await fetch('/api/tasks', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({title}),
  });
  event.target.reset();
  refresh();
});
document.querySelector('[data-testid="status-filter"]').addEventListener('change', refresh);
refresh();
"""


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(db_path):
    conn = sqlite3.connect(db_path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path):
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def validate_title(value):
    if not isinstance(value, str):
        raise ValueError("title must be a string")
    value = value.strip()
    if not 1 <= len(value) <= 120:
        raise ValueError("title must be 1..120 characters")
    return value


def validate_description(value):
    if not isinstance(value, str):
        raise ValueError("description must be a string")
    if len(value) > 2000:
        raise ValueError("description must be at most 2000 characters")
    return value


def validate_status(value):
    if value not in STATUSES:
        raise ValueError("invalid status")
    return value


def validate_priority(value):
    if value not in PRIORITIES:
        raise ValueError("invalid priority")
    return value


def task_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "priority": row["priority"],
        "created_at": row["created_at"],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "BenchTaskboard/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    @property
    def db_path(self):
        return self.server.db_path

    def send_json(self, status, payload, headers=None):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status, message):
        self.send_json(status, {"error": message})

    def send_body(self, status, body, content_type, headers=None):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            raise ValueError("missing body")
        raw = self.rfile.read(length)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError("invalid JSON")
        if not isinstance(value, dict):
            raise ValueError("body must be a JSON object")
        return value

    def route(self):
        parsed = urlparse(self.path)
        path = parsed.path
        parts = [p for p in path.split("/") if p]
        return parsed, parts

    def do_GET(self):
        parsed, parts = self.route()
        if parts == []:
            self.send_body(200, INDEX_HTML, "text/html; charset=utf-8")
            return
        if parts == ["static", "app.js"]:
            self.send_body(200, APP_JS, "application/javascript")
            return
        if parts == ["api", "tasks"]:
            query = parse_qs(parsed.query)
            try:
                status = query.get("status", [None])[0]
                if status is not None:
                    validate_status(status)
                limit = self.parse_int(query.get("limit", ["20"])[0], "limit")
                offset = self.parse_int(query.get("offset", ["0"])[0], "offset")
                if not 1 <= limit <= 100:
                    raise ValueError("limit must be 1..100")
                if offset < 0:
                    raise ValueError("offset must be >= 0")
            except ValueError as exc:
                self.send_error_json(400, str(exc))
                return
            with connect(self.db_path) as conn:
                sql = "SELECT * FROM tasks"
                params = []
                if status is not None:
                    sql += " WHERE status = ?"
                    params.append(status)
                sql += " ORDER BY id ASC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                rows = conn.execute(sql, params).fetchall()
            self.send_json(200, [task_dict(row) for row in rows])
            return
        if len(parts) == 3 and parts[:2] == ["api", "tasks"]:
            task_id = self.parse_id(parts[2])
            if task_id is None:
                self.send_error_json(404, "not found")
                return
            with connect(self.db_path) as conn:
                row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if row is None:
                self.send_error_json(404, "not found")
            else:
                self.send_json(200, task_dict(row))
            return
        if parts == ["api", "stats"]:
            with connect(self.db_path) as conn:
                rows = conn.execute("SELECT status, COUNT(*) AS n FROM tasks GROUP BY status").fetchall()
            stats = {status: 0 for status in STATUSES}
            for row in rows:
                if row["status"] in stats:
                    stats[row["status"]] = row["n"]
            stats["total"] = sum(stats.values())
            self.send_json(200, stats)
            return
        if parts and parts[0] == "api":
            self.send_error_json(404, "not found")
            return
        self.send_error_json(404, "not found")

    def do_POST(self):
        parsed, parts = self.route()
        if parts == ["api", "tasks"]:
            try:
                body = self.read_json()
                title = validate_title(body.get("title"))
                description = validate_description(body.get("description", ""))
                status = validate_status(body.get("status", "todo"))
                priority = validate_priority(body.get("priority", "medium"))
            except ValueError as exc:
                self.send_error_json(400, str(exc))
                return
            created = now_iso()
            with connect(self.db_path) as conn:
                cursor = conn.execute(
                    "INSERT INTO tasks (title, description, status, priority, created_at) VALUES (?, ?, ?, ?, ?)",
                    (title, description, status, priority, created),
                )
                task_id = cursor.lastrowid
                conn.commit()
                row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            self.send_json(201, task_dict(row), {"Location": f"/api/tasks/{task_id}"})
            return
        if parts and parts[0] == "api":
            self.send_error_json(405, "method not allowed")
            return
        self.send_error_json(404, "not found")

    def do_PATCH(self):
        parsed, parts = self.route()
        if len(parts) == 3 and parts[:2] == ["api", "tasks"]:
            task_id = self.parse_id(parts[2])
            if task_id is None:
                self.send_error_json(404, "not found")
                return
            try:
                body = self.read_json()
                updates = {}
                if "title" in body:
                    updates["title"] = validate_title(body["title"])
                if "description" in body:
                    updates["description"] = validate_description(body["description"])
                if "status" in body:
                    updates["status"] = validate_status(body["status"])
                if "priority" in body:
                    updates["priority"] = validate_priority(body["priority"])
            except ValueError as exc:
                self.send_error_json(400, str(exc))
                return
            with connect(self.db_path) as conn:
                row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
                if row is None:
                    self.send_error_json(404, "not found")
                    return
                if updates:
                    assignments = ", ".join(f"{name} = ?" for name in updates)
                    conn.execute(f"UPDATE tasks SET {assignments} WHERE id = ?", (*updates.values(), task_id))
                    conn.commit()
                row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            self.send_json(200, task_dict(row))
            return
        if parts and parts[0] == "api":
            self.send_error_json(405, "method not allowed")
            return
        self.send_error_json(404, "not found")

    def do_DELETE(self):
        parsed, parts = self.route()
        if len(parts) == 3 and parts[:2] == ["api", "tasks"]:
            task_id = self.parse_id(parts[2])
            if task_id is None:
                self.send_error_json(404, "not found")
                return
            with connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                conn.commit()
            if cursor.rowcount:
                self.send_response(204)
                self.send_header("Content-Length", "0")
                self.end_headers()
            else:
                self.send_error_json(404, "not found")
            return
        if parts and parts[0] == "api":
            self.send_error_json(405, "method not allowed")
            return
        self.send_error_json(404, "not found")

    def do_PUT(self):
        parsed, parts = self.route()
        if parts and parts[0] == "api":
            self.send_error_json(405, "method not allowed")
            return
        self.send_error_json(404, "not found")

    do_PATCH_ALIAS = None

    @staticmethod
    def parse_int(value, name):
        if not re.fullmatch(r"-?\d+", value or ""):
            raise ValueError(f"{name} must be an integer")
        return int(value)

    @staticmethod
    def parse_id(value):
        if not re.fullmatch(r"\d+", value or ""):
            return None
        return int(value)


def make_server(host: str, port: int, db_path: str) -> ThreadingHTTPServer:
    init_db(db_path)
    server = ThreadingHTTPServer((host, port), Handler)
    server.db_path = db_path
    return server
