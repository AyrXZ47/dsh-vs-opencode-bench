# ledger

Paquete de contabilidad en centavos. Tiene bugs sembrados; hay que arreglar la
causa raíz sin cambiar la API pública.

## Contrato

```python
def sum_by_category(entries, category) -> dict[int, int]
def parse_amount(text: str) -> int
def apply_discount(amount_cents: int, percent: int) -> int
def merge_intervals(intervals) -> list[tuple[int, int]]
```

- `sum_by_category(entries, category)`: `entries` es una lista de dicts con
  `id`, `category`, `amount_cents`. Devuelve `{id: amount_cents}` solo para la
  categoría pedida. Llamadas sucesivas no deben arrastrar estado.
- `parse_amount(text)`: acepta `strip()`, signo opcional, dígitos, y punto con
  1 o 2 decimales. Devuelve centavos como int. Rechaza vacío, `.5`, `12.`,
  más de 2 decimales, letras y separadores raros.
- `apply_discount(amount_cents, percent)`: `amount_cents` int >= 0;
  `percent` int 0..100; devuelve int con redondeo `.5` hacia arriba.
  Fuera de rango: `ValueError`.
- `merge_intervals(intervals)`: lista de tuplas `(start, end)` con
  `start <= end`; devuelve lista ordenada de tuplas fusionando intervalos que
  se solapan **o se tocan**. No muta la entrada.

Tests visibles: `python3 -m unittest discover -s ledger/tests -v`.
