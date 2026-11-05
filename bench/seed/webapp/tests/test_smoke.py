"""Visible smoke tests for the taskboard API."""

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from webapp.app import make_server


class TaskboardSmokeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "tasks.db")
        self.server = make_server("127.0.0.1", 0, self.db)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def request(self, method, path, body=None, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read()
                return resp.status, dict(resp.headers), json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            return exc.code, dict(exc.headers), json.loads(raw) if raw else None

    def test_create_and_get(self):
        status, headers, task = self.request(
            "POST", "/api/tasks", {"title": "Primera", "priority": "high"}
        )
        self.assertEqual(status, 201)
        self.assertEqual(task["title"], "Primera")
        self.assertEqual(task["status"], "todo")
        self.assertEqual(headers.get("Location"), f"/api/tasks/{task['id']}")

        status, _, fetched = self.request("GET", f"/api/tasks/{task['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched, task)

    def test_list_and_stats(self):
        for title in ("a", "b", "c"):
            self.request("POST", "/api/tasks", {"title": title})
        status, _, tasks = self.request("GET", "/api/tasks")
        self.assertEqual(status, 200)
        self.assertEqual([t["title"] for t in tasks], ["a", "b", "c"])

        status, _, stats = self.request("GET", "/api/stats")
        self.assertEqual(status, 200)
        self.assertEqual(stats, {"todo": 3, "doing": 0, "done": 0, "total": 3})

    def test_validation(self):
        status, _, _ = self.request("POST", "/api/tasks", {"title": ""})
        self.assertEqual(status, 400)
        status, _, _ = self.request("POST", "/api/tasks", {"title": "x", "status": "nope"})
        self.assertEqual(status, 400)

    def test_patch_and_delete(self):
        _, _, task = self.request("POST", "/api/tasks", {"title": "x"})
        status, _, updated = self.request(
            "PATCH", f"/api/tasks/{task['id']}", {"status": "done"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["status"], "done")
        self.assertEqual(updated["title"], "x")

        status, _, _ = self.request("DELETE", f"/api/tasks/{task['id']}")
        self.assertEqual(status, 204)
        status, _, _ = self.request("GET", f"/api/tasks/{task['id']}")
        self.assertEqual(status, 404)

    def test_static_page(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/")
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode()
        self.assertIn('data-testid="task-list"', html)
        self.assertIn('data-testid="new-task-form"', html)
        self.assertIn('data-testid="status-filter"', html)


if __name__ == "__main__":
    unittest.main()
