"""Hidden acceptance tests for the render3d phase."""

import os
import sys
import unittest

sys.path.insert(0, os.getcwd())

from render3d.render import render
from render3d.scene import validate_scene


def parse_ppm(data: bytes):
    header, pixels = data.split(b"\n", 3)[0:3], data.split(b"\n", 3)[3]
    assert header[0] == b"P6", header
    width, height = map(int, header[1].split())
    assert header[2] == b"255", header
    assert len(pixels) == width * height * 3, (len(pixels), width, height)
    return width, height, pixels


def pixel(data: bytes, x: int, y: int):
    width, height, pixels = parse_ppm(data)
    index = (y * width + x) * 3
    return tuple(pixels[index:index + 3])


def base_scene(**overrides):
    scene = {
        "width": 64,
        "height": 48,
        "background": [10, 10, 20],
        "camera": {"position": [0, 0, 4], "target": [0, 0, 0], "up": [0, 1, 0], "fov_deg": 90},
        "light": {"direction": [0, 0, -1], "ambient": 0.2, "diffuse": 0.8},
        "triangles": [
            {"v0": [-1, -1, 0], "v1": [1, -1, 0], "v2": [0, 1, 0], "color": [200, 40, 40]}
        ],
    }
    scene.update(overrides)
    return scene


class Render3DAcceptance(unittest.TestCase):
    def test_header_and_background_only(self):
        scene = base_scene(triangles=[])
        width, height, pixels = parse_ppm(render(scene))
        self.assertEqual((width, height), (64, 48))
        self.assertEqual(pixels, bytes([10, 10, 20]) * (64 * 48))

    def test_front_face_exact_color(self):
        data = render(base_scene())
        self.assertEqual(pixel(data, 32, 24), (200, 40, 40))

    def test_backface_is_culled(self):
        scene = base_scene()
        tri = scene["triangles"][0]
        tri["v1"], tri["v2"] = tri["v2"], tri["v1"]
        data = render(scene)
        self.assertEqual(pixel(data, 32, 24), (10, 10, 20))

    def test_depth_buffer_near_wins(self):
        near = {"v0": [-0.8, -0.8, 1], "v1": [0.8, -0.8, 1], "v2": [0, 0.8, 1], "color": [220, 20, 20]}
        far = {"v0": [-0.8, -0.8, -1], "v1": [0.8, -0.8, -1], "v2": [0, 0.8, -1], "color": [20, 20, 220]}
        for order in ((near, far), (far, near)):
            data = render(base_scene(triangles=list(order)))
            self.assertEqual(pixel(data, 32, 24), (220, 20, 20), order)

    def test_perspective_size(self):
        def count_non_background(z):
            tri = {"v0": [-0.5, -0.5, z], "v1": [0.5, -0.5, z], "v2": [0, 0.5, z], "color": [200, 200, 200]}
            data = render(base_scene(camera={"position": [0, 0, 5], "target": [0, 0, 0], "up": [0, 1, 0], "fov_deg": 60}, triangles=[tri]))
            _, _, pixels = parse_ppm(data)
            return sum(1 for i in range(0, len(pixels), 3) if tuple(pixels[i:i + 3]) != (10, 10, 20))
        self.assertGreater(count_non_background(2), count_non_background(0))

    def test_lighting_direction(self):
        bright = render(base_scene(light={"direction": [0, 0, -1], "ambient": 0.2, "diffuse": 0.8}))
        dark = render(base_scene(light={"direction": [0, 0, 1], "ambient": 0.2, "diffuse": 0.8}))
        self.assertEqual(pixel(bright, 32, 24), (200, 40, 40))
        self.assertEqual(pixel(dark, 32, 24), (40, 8, 8))

    def test_ambient_only(self):
        data = render(base_scene(light={"direction": [0, 0, 1], "ambient": 0.5, "diffuse": 0.5}))
        self.assertEqual(pixel(data, 32, 24), (100, 20, 20))

    def test_near_clip_discards_triangle(self):
        tri = {"v0": [-1, -1, 4], "v1": [1, -1, 4], "v2": [0, 1, 4], "color": [200, 40, 40]}
        data = render(base_scene(triangles=[tri]))
        self.assertEqual(pixel(data, 32, 24), (10, 10, 20))

    def test_validation(self):
        bad = [
            base_scene(width=0),
            base_scene(height=-1),
            base_scene(background=[1, 2]),
            base_scene(background=[1, 2, 300]),
            base_scene(camera={"position": [0, 0, 0], "target": [0, 0, 0], "up": [0, 1, 0], "fov_deg": 60}),
            base_scene(camera={"position": [0, 0, 4], "target": [0, 0, 0], "up": [0, 0, 0], "fov_deg": 60}),
            base_scene(camera={"position": [0, 0, 4], "target": [0, 0, 0], "up": [0, 1, 0], "fov_deg": 0}),
            base_scene(camera={"position": [0, 0, 4], "target": [0, 0, 0], "up": [0, 1, 0], "fov_deg": 180}),
            base_scene(light={"direction": [0, 0, 0], "ambient": 0.2, "diffuse": 0.8}),
            base_scene(light={"direction": [0, 0, -1], "ambient": -0.1, "diffuse": 0.8}),
            base_scene(triangles=[{"v0": [0, 0, 0], "v1": [1, 0, 0], "color": [1, 2, 3]}]),
            base_scene(triangles=[{"v0": [0, 0, 0], "v1": [1, 0, 0], "v2": [0, 1, 0], "color": [1, 2, 3, 4]}]),
            base_scene(triangles=[{"v0": [0, 0, 0], "v1": [1, 0, 0], "v2": [0, 1], "color": [1, 2, 3]}]),
        ]
        for scene in bad:
            with self.assertRaises(ValueError, msg=str(scene)[:120]):
                validate_scene(scene)

    def test_one_by_one(self):
        scene = base_scene(width=1, height=1, triangles=[])
        width, height, pixels = parse_ppm(render(scene))
        self.assertEqual((width, height), (1, 1))
        self.assertEqual(pixels, bytes([10, 10, 20]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
