# bench2 seed

Repositorio semilla de la segunda suite de evaluación de harnesses/proveedores.

Cinco fases independientes, cada una arranca desde este mismo commit:

1. `webapp/`: API REST + SQLite + frontend estático, solo stdlib de Python.
2. `render3d/`: rasterizador 3D por software, solo stdlib de Python.
3. `ledger/`: paquete con bugs sembrados; hay que arreglar la causa raíz.
4. Investigación web sobre SQLite WAL.
5. Skills (`vault`, `ponytail`, `security-audit`) + MCP `dotpm` sobre el vault de prueba.

`service/` es un módulo pequeño con problemas de seguridad sembrados para la
fase de auditoría. No se ejecuta en ninguna fase.

Reglas:

- No agregues dependencias externas. Todo corre con Python 3.14 estándar.
- No toques archivos fuera de la carpeta que indica cada tarea.
- No hagas commits: los cambios quedan en el working tree.
