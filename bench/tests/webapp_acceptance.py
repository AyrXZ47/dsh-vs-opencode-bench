"""Hidden acceptance tests for the taskboard webapp phase."""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, os.getcwd())

from webapp.app import make_server


class Server:
    def __init__(self, db_path: str):
        self.server = make_server("127.0.0.1", 0, db_path)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, method, path, body=None, raw=None, content_type="application/json"):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        headers = {}
        if data is not None:
            headers["Content-Type"] = content_type
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                payload = resp.read()
                parsed = json.loads(payload) if payload else None
                return resp.status, dict(resp.headers), parsed
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            try:
                parsed = json.loads(payload) if payload else None
            except json.JSONDecodeError:
                parsed = payload
            return exc.code, dict(exc.headers), parsed


class TaskboardAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "tasks.db")
        self.srv = Server(self.db)

    def tearDown(self):
        self.srv.close()
        self.tmp.cleanup()

    def create(self, **fields):
        status, headers, task = self.srv.request("POST", "/api/tasks", fields)
        self.assertEqual(status, 201, task)
        return task, headers

    def test_defaults_and_fields(self):
        task, headers = self.create(title="  Comprar café  ")
        self.assertEqual(task["title"], "Comprar café")
        self.assertEqual(task["description"], "")
        self.assertEqual(task["status"], "todo")
        self.assertEqual(task["priority"], "medium")
        self.assertIsInstance(task["id"], int)
        self.assertRegex(task["created_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(headers.get("Location"), f"/api/tasks/{task['id']}")

    def test_validation(self):
        bad_bodies = [
            {},
            {"title": ""},
            {"title": "   "},
            {"title": "x" * 121},
            {"title": "ok", "description": "d" * 2001},
            {"title": "ok", "status": "pending"},
            {"title": "ok", "priority": "urgent"},
            {"title": 123},
        ]
        for body in bad_bodies:
            status, _, _ = self.srv.request("POST", "/api/tasks", body)
            self.assertEqual(status, 400, body)

        status, _, _ = self.srv.request("POST", "/api/tasks", raw=b"{not json")
        self.assertEqual(status, 400)
        status, _, _ = self.srv.request("POST", "/api/tasks", raw=b"[1,2,3]")
        self.assertEqual(status, 400)

    def test_unknown_fields_are_ignored(self):
        task, _ = self.create(title="ok", hacker="yes", id=999)
        self.assertNotEqual(task["id"], 999)
        self.assertNotIn("hacker", task)

    def test_list_order_and_pagination(self):
        ids = [self.create(title=f"t{i}")[0]["id"] for i in range(25)]
        status, _, tasks = self.srv.request("GET", "/api/tasks")
        self.assertEqual(status, 200)
        self.assertEqual([t["id"] for t in tasks], ids[:20])

        status, _, tasks = self.srv.request("GET", "/api/tasks?limit=5&offset=20")
        self.assertEqual(status, 200)
        self.assertEqual([t["id"] for t in tasks], ids[20:25])

        for query in ("limit=0", "limit=101", "offset=-1", "status=nope", "limit=x", "offset=y"):
            status, _, _ = self.srv.request("GET", f"/api/tasks?{query}")
            self.assertEqual(status, 400, query)

    def test_status_filter(self):
        self.create(title="a")
        b, _ = self.create(title="b")
        self.srv.request("PATCH", f"/api/tasks/{b['id']}", {"status": "done"})
        status, _, tasks = self.srv.request("GET", "/api/tasks?status=done")
        self.assertEqual(status, 200)
        self.assertEqual([t["title"] for t in tasks], ["b"])

    def test_get_patch_delete_not_found(self):
        for method in ("GET", "PATCH", "DELETE"):
            status, _, _ = self.srv.request(method, "/api/tasks/999999", {"status": "done"} if method == "PATCH" else None)
            self.assertEqual(status, 404, method)

    def test_patch_partial_and_validation(self):
        task, _ = self.create(title="base", description="d", priority="low")
        status, _, updated = self.srv.request("PATCH", f"/api/tasks/{task['id']}", {"status": "doing"})
        self.assertEqual(status, 200)
        self.assertEqual(updated["status"], "doing")
        self.assertEqual(updated["title"], "base")
        self.assertEqual(updated["description"], "d")
        self.assertEqual(updated["priority"], "low")

        status, _, _ = self.srv.request("PATCH", f"/api/tasks/{task['id']}", {"title": ""})
        self.assertEqual(status, 400)
        status, _, _ = self.srv.request("PATCH", f"/api/tasks/{task['id']}", {"priority": "nope"})
        self.assertEqual(status, 400)

    def test_delete_and_stats(self):
        a, _ = self.create(title="a")
        self.create(title="b")
        self.srv.request("PATCH", f"/api/tasks/{a['id']}", {"status": "done"})
        status, _, _ = self.srv.request("DELETE", f"/api/tasks/{a['id']}")
        self.assertEqual(status, 204)
        status, _, _ = self.srv.request("DELETE", f"/api/tasks/{a['id']}")
        self.assertEqual(status, 404)

        status, _, stats = self.srv.request("GET", "/api/stats")
        self.assertEqual(status, 200)
        self.assertEqual(stats, {"todo": 1, "doing": 0, "done": 0, "total": 1})

    def test_sql_injection_is_stored_literally(self):
        payload = "x'); DROP TABLE tasks; --"
        task, _ = self.create(title=payload)
        self.assertEqual(task["title"], payload)
        status, _, tasks = self.srv.request("GET", "/api/tasks")
        self.assertEqual(status, 200)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], payload)
        status, _, _ = self.srv.request("GET", "/api/tasks?status=todo'%20OR%20'1'='1")
        self.assertEqual(status, 400)

    def test_concurrent_creates(self):
        def worker(n):
            statuses = []
            for i in range(5):
                status, _, task = self.srv.request("POST", "/api/tasks", {"title": f"w{n}-{i}"})
                statuses.append((status, task.get("id") if isinstance(task, dict) else None))
            return statuses

        with ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(worker, range(16)))
        flat = [item for batch in results for item in batch]
        self.assertEqual(len(flat), 80)
        self.assertTrue(all(status == 201 for status, _ in flat))
        ids = [task_id for _, task_id in flat]
        self.assertEqual(len(set(ids)), 80)

    def test_persistence_across_servers(self):
        task, _ = self.create(title="persist")
        self.srv.close()
        self.srv = Server(self.db)
        status, _, fetched = self.srv.request("GET", f"/api/tasks/{task['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched["title"], "persist")

    def test_static_frontend(self):
        req = urllib.request.Request(self.srv.base + "/")
        with urllib.request.urlopen(req, timeout=10) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode()
        for marker in ('data-testid="task-list"', 'data-testid="new-task-form"', 'data-testid="status-filter"'):
            self.assertIn(marker, html)
        self.assertIn("<script", html)

        req = urllib.request.Request(self.srv.base + "/static/app.js")
        with urllib.request.urlopen(req, timeout=10) as resp:
            self.assertEqual(resp.status, 200)
            js = resp.read().decode()
        self.assertIn("fetch(", js)
        if "fetch(" not in html:
            self.assertIn("/static/app.js", html)

    def test_method_not_allowed(self):
        for method, path in (("PUT", "/api/tasks"), ("DELETE", "/api/tasks")):
            status, _, _ = self.srv.request(method, path)
            self.assertEqual(status, 405, (method, path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
