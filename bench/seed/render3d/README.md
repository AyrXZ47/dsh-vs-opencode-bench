# render3d

Rasterizador 3D por software, solo stdlib de Python.

## Contrato

`render3d/scene.py`:

```python
def validate_scene(scene: dict) -> None   # ValueError si es inválido
def load_scene(path: str) -> dict         # JSON + validate_scene
```

`render3d/render.py`:

```python
def render(scene: dict) -> bytes          # PPM binario P6
```

`python3 -m render3d input.json output.ppm` escribe el PPM; con escena inválida
sale con código 2.

### Escena JSON

```json
{
  "width": 320,
  "height": 240,
  "background": [0, 0, 0],
  "camera": {
    "position": [0, 0, 5],
    "target": [0, 0, 0],
    "up": [0, 1, 0],
    "fov_deg": 60
  },
  "light": {"direction": [-0.5, -1, -0.5], "ambient": 0.2, "diffuse": 0.8},
  "triangles": [
    {"v0": [-1, -1, 0], "v1": [1, -1, 0], "v2": [0, 1, 0], "color": [200, 40, 40]}
  ]
}
```

Reglas de validación:

- `width` y `height` enteros positivos, máximo 2048.
- `background` y `color` son listas de 3 enteros 0..255.
- `camera.position` y `camera.target` listas de 3 números; no pueden coincidir.
- `camera.up` lista de 3 números no nula.
- `fov_deg` número en (1, 179).
- `light.direction` vector no nulo; `ambient` y `diffuse` números >= 0.
- Cada triángulo tiene `v0`, `v1`, `v2` (listas de 3 números) y `color`.
- Lista de triángulos puede estar vacía.

### Render

- Cámara en `position`, mirando a `target`, con `up`. Espacio de vista: la
  cámara mira hacia `-Z`.
- `aspect = width / height`, `f = 1 / tan(fov_deg/2)`.
- Proyección:
  `ndc_x = (f / aspect) * (x_view / -z_view)`,
  `ndc_y = f * (y_view / -z_view)`.
- Pantalla:
  `sx = (ndc_x * 0.5 + 0.5) * (width - 1)`,
  `sy = (1 - (ndc_y * 0.5 + 0.5)) * (height - 1)`.
- Culling: el triángulo es front-facing si
  `dot(cross(v1-v0, v2-v0), camera.position - v0) > 0`. Si no, se descarta.
- Near clip: si algún vértice tiene `z_view >= -0.1`, se descarta el triángulo.
- Z-buffer con profundidad `-z_view`; menor gana.
- Iluminación: normal normalizada; `L = normalize(-light.direction)`;
  `intensity = ambient + diffuse * max(0, dot(normal, L))`; píxel =
  `clamp(color * intensity)` con redondeo al entero más cercano, `.5` hacia
  arriba.
- Fondo: `background` en todos los píxeles no cubiertos.
- PPM P6: `P6\n{width} {height}\n255\n` seguido de RGB binario.
