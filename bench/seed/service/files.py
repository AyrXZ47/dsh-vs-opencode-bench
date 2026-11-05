"""File download helper for the example service."""

import os

BASE = "/srv/service/files"


def read_file(name: str) -> bytes:
    path = os.path.join(BASE, name)
    with open(path, "rb") as handle:
        return handle.read()
