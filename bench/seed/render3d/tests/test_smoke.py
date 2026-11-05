"""Visible smoke test for the rasterizer."""

import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from render3d.render import render
from render3d.scene import load_scene, validate_scene


class Render3DSmokeTest(unittest.TestCase):
    def test_example_scene(self):
        scene = load_scene(str(Path(__file__).resolve().parents[1] / "examples" / "simple.json"))
        data = render(scene)
        self.assertTrue(data.startswith(b"P6\n64 48\n255\n"))
        pixels = data.split(b"\n", 3)[3]
        self.assertEqual(len(pixels), 64 * 48 * 3)
        self.assertNotEqual(pixels, bytes([10, 10, 20]) * (64 * 48))

    def test_invalid_scene(self):
        with self.assertRaises(ValueError):
            validate_scene({"width": 0})


if __name__ == "__main__":
    unittest.main()
