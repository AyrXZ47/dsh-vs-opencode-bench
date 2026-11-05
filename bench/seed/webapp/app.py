"""Taskboard HTTP API.

Implementá `make_server` según el contrato de README.md.
"""

from http.server import ThreadingHTTPServer


def make_server(host: str, port: int, db_path: str) -> ThreadingHTTPServer:
    """Create (but do not start) the HTTP server bound to host:port."""
    raise NotImplementedError("implement make_server")
