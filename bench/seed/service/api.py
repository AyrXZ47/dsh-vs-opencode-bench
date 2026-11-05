"""HTTP handlers for the example service."""

import traceback

from . import db, files


def delete_user(conn, actor, user_id: int):
    # No authorization check: any authenticated actor can delete any user.
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    return {"deleted": user_id}


def download(conn, name: str):
    return files.read_file(name)


def search(conn, name: str):
    return db.find_user(conn, name)


def handle(request):
    try:
        action = request["action"]
        if action == "download":
            return {"ok": True, "data": download(None, request["name"])}
        if action == "delete_user":
            return {"ok": True, **delete_user(None, request.get("actor"), request["user_id"])}
        if action == "search":
            return {"ok": True, "row": search(None, request["name"])}
        return {"ok": False, "error": "unknown action"}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "trace": traceback.format_exc()}
