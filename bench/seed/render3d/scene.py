"""Scene loading and validation."""


def validate_scene(scene: dict) -> None:
    """Raise ValueError if the scene does not match the documented schema."""
    raise NotImplementedError("implement validate_scene")


def load_scene(path: str) -> dict:
    """Load a JSON scene and validate it."""
    raise NotImplementedError("implement load_scene")
