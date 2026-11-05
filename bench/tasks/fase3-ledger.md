# Fase 3 — Bugfix de ledger

Trabajás en `ledger/`. No toques otras carpetas.

El paquete tiene bugs sembrados. Arreglá la causa raíz de cada uno sin cambiar
la API pública ni el contrato de `ledger/README.md`.

Requisitos:

- `sum_by_category` no debe arrastrar estado entre llamadas.
- `parse_amount` debe aceptar solo el formato documentado y devolver centavos
  exactos, sin pasar por float.
- `apply_discount` debe validar rango y redondear `.5` hacia arriba.
- `merge_intervals` debe fusionar intervalos que se tocan, sin mutar la entrada.
- Agregá tests de regresión en `ledger/tests/` para cada bug corregido.
- `python3 -m unittest discover -s ledger/tests -v` debe pasar.

No hagas commit. Al terminar, resumí cada bug, su causa raíz y el test que lo
cubre.
