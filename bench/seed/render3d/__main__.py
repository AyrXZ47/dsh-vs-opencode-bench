"""Command line entry point: python3 -m render3d input.json output.ppm."""

import sys

from .render import render
from .scene import load_scene


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: python3 -m render3d input.json output.ppm", file=sys.stderr)
        return 2
    try:
        scene = load_scene(argv[1])
        data = render(scene)
    except (OSError, ValueError) as exc:
        print(f"render3d: {exc}", file=sys.stderr)
        return 2
    with open(argv[2], "wb") as handle:
        handle.write(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
