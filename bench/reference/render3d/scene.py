"""Reference scene validation (not shipped to agents)."""

import json
import math


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _vector(value, name, length=3):
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValueError(f"{name} must be a list of {length} numbers")
    if not all(_is_number(item) for item in value):
        raise ValueError(f"{name} must contain finite numbers")
    return list(value)


def _color(value, name):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{name} must be a list of 3 integers")
    if not all(isinstance(item, int) and not isinstance(item, bool) and 0 <= item <= 255 for item in value):
        raise ValueError(f"{name} must contain integers 0..255")
    return list(value)


def validate_scene(scene: dict) -> None:
    if not isinstance(scene, dict):
        raise ValueError("scene must be an object")
    width = scene.get("width")
    height = scene.get("height")
    if not isinstance(width, int) or isinstance(width, bool) or not 1 <= width <= 2048:
        raise ValueError("width must be an integer 1..2048")
    if not isinstance(height, int) or isinstance(height, bool) or not 1 <= height <= 2048:
        raise ValueError("height must be an integer 1..2048")
    _color(scene.get("background"), "background")

    camera = scene.get("camera")
    if not isinstance(camera, dict):
        raise ValueError("camera must be an object")
    position = _vector(camera.get("position"), "camera.position")
    target = _vector(camera.get("target"), "camera.target")
    up = _vector(camera.get("up"), "camera.up")
    if position == target:
        raise ValueError("camera.position and camera.target must differ")
    if all(abs(item) < 1e-12 for item in up):
        raise ValueError("camera.up must be non-zero")
    fov = camera.get("fov_deg")
    if not _is_number(fov) or not 1 < fov < 179:
        raise ValueError("camera.fov_deg must be in (1, 179)")

    light = scene.get("light")
    if not isinstance(light, dict):
        raise ValueError("light must be an object")
    direction = _vector(light.get("direction"), "light.direction")
    if all(abs(item) < 1e-12 for item in direction):
        raise ValueError("light.direction must be non-zero")
    for key in ("ambient", "diffuse"):
        value = light.get(key)
        if not _is_number(value) or value < 0:
            raise ValueError(f"light.{key} must be a number >= 0")

    triangles = scene.get("triangles")
    if not isinstance(triangles, list):
        raise ValueError("triangles must be a list")
    for index, triangle in enumerate(triangles):
        if not isinstance(triangle, dict):
            raise ValueError(f"triangle {index} must be an object")
        for key in ("v0", "v1", "v2"):
            _vector(triangle.get(key), f"triangle {index}.{key}")
        _color(triangle.get("color"), f"triangle {index}.color")


def load_scene(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        scene = json.load(handle)
    validate_scene(scene)
    return scene
