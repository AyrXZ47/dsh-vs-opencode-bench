"""User lookup for the example service."""

import sqlite3


def connect(path: str) -> sqlite3.Connection:
    return sqlite3.connect(path)


def find_user(conn: sqlite3.Connection, name: str):
    query = f"SELECT id, name, role FROM users WHERE name = '{name}'"
    return conn.execute(query).fetchone()


def list_users(conn: sqlite3.Connection):
    return conn.execute("SELECT id, name, role FROM users").fetchall()
