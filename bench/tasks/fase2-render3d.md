# Fase 2 — Rasterizador 3D por software

Trabajás en `render3d/`. No toques otras carpetas.

Implementá el contrato completo de `render3d/README.md`: carga/validación de
escenas, proyección en perspectiva, culling por normal, near clip, z-buffer,
iluminación Lambert + ambiente y salida PPM P6. Solo stdlib de Python.

Requisitos:

- `validate_scene(scene)` y `load_scene(path)`.
- `render(scene) -> bytes`.
- `python3 -m render3d input.json output.ppm` funciona y sale con 2 si la
  escena es inválida.
- `python3 -m unittest discover -s render3d/tests -v` debe pasar.
- Respetá exactamente las convenciones del README (espacio de vista, `-Z`,
  proyección, culling, near clip, iluminación, redondeo).

No agregues dependencias. No hagas commit. Al terminar, resumí qué
implementaste y el resultado de los tests visibles.
