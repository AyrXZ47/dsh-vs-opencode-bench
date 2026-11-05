"""Reference software rasterizer (not shipped to agents)."""

import math

from .scene import validate_scene


def _sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _length(v):
    return math.sqrt(_dot(v, v))


def _normalize(v):
    n = _length(v)
    if n < 1e-12:
        raise ValueError("zero-length vector")
    return [v[0] / n, v[1] / n, v[2] / n]


def _edge(a, b, p):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def _clamp(value):
    return max(0, min(255, int(value + 0.5)))


def render(scene: dict) -> bytes:
    validate_scene(scene)
    width = scene["width"]
    height = scene["height"]
    background = bytes(scene["background"])
    camera = scene["camera"]
    position = [float(v) for v in camera["position"]]
    target = [float(v) for v in camera["target"]]
    up = [float(v) for v in camera["up"]]
    fov = float(camera["fov_deg"])
    light = scene["light"]
    light_direction = _normalize([float(v) for v in light["direction"]])
    ambient = float(light["ambient"])
    diffuse = float(light["diffuse"])

    forward = _normalize(_sub(target, position))
    right = _normalize(_cross(forward, up))
    true_up = _cross(right, forward)
    aspect = width / height
    f = 1.0 / math.tan(math.radians(fov) / 2.0)

    def to_view(point):
        d = _sub(point, position)
        return [
            _dot(d, right),
            _dot(d, true_up),
            -_dot(d, forward),
        ]

    def project(view):
        x, y, z = view
        ndc_x = (f / aspect) * (x / -z)
        ndc_y = f * (y / -z)
        sx = (ndc_x * 0.5 + 0.5) * (width - 1)
        sy = (1.0 - (ndc_y * 0.5 + 0.5)) * (height - 1)
        return sx, sy

    color_buffer = bytearray(background * (width * height))
    depth_buffer = [float("inf")] * (width * height)
    light_dir = [-light_direction[0], -light_direction[1], -light_direction[2]]

    for triangle in scene["triangles"]:
        v0 = [float(v) for v in triangle["v0"]]
        v1 = [float(v) for v in triangle["v1"]]
        v2 = [float(v) for v in triangle["v2"]]
        normal = _normalize(_cross(_sub(v1, v0), _sub(v2, v0)))
        if _dot(normal, _sub(position, v0)) <= 0:
            continue
        view0, view1, view2 = to_view(v0), to_view(v1), to_view(v2)
        if any(view[2] >= -0.1 for view in (view0, view1, view2)):
            continue
        p0, p1, p2 = project(view0), project(view1), project(view2)
        area = _edge(p0, p1, p2)
        if abs(area) < 1e-9:
            continue
        intensity = ambient + diffuse * max(0.0, _dot(normal, light_dir))
        base = triangle["color"]
        r = _clamp(base[0] * intensity)
        g = _clamp(base[1] * intensity)
        b = _clamp(base[2] * intensity)

        min_x = max(0, int(math.floor(min(p0[0], p1[0], p2[0]))))
        max_x = min(width - 1, int(math.ceil(max(p0[0], p1[0], p2[0]))))
        min_y = max(0, int(math.floor(min(p0[1], p1[1], p2[1]))))
        max_y = min(height - 1, int(math.ceil(max(p0[1], p1[1], p2[1]))))

        for py in range(min_y, max_y + 1):
            for px in range(min_x, max_x + 1):
                sample = (px + 0.5, py + 0.5)
                w0 = _edge(p1, p2, sample)
                w1 = _edge(p2, p0, sample)
                w2 = _edge(p0, p1, sample)
                if area > 0:
                    if w0 < 0 or w1 < 0 or w2 < 0:
                        continue
                else:
                    if w0 > 0 or w1 > 0 or w2 > 0:
                        continue
                b0 = w0 / area
                b1 = w1 / area
                b2 = w2 / area
                depth = b0 * (-view0[2]) + b1 * (-view1[2]) + b2 * (-view2[2])
                index = py * width + px
                if depth < depth_buffer[index]:
                    depth_buffer[index] = depth
                    offset = index * 3
                    color_buffer[offset:offset + 3] = bytes((r, g, b))

    header = f"P6\n{width} {height}\n255\n".encode()
    return header + bytes(color_buffer)
