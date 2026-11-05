# dsh-vs-opencode-bench

Contexto específico: ver `README.md` (diseño, resultados, límites) y
`bench/README.md` (cómo reproducir).

Reglas globales (commits, estilo, flujo de agentes): las inyecta el harness;
este archivo solo debe crecer con lo que sea distinto de este repo.

- No commitear credenciales, `auth.json`, `*.db`, `.env`, `.bench-vault/` ni
  logs crudos sin sanitizar.
- Un cambio lógico por commit, conventional commits, sin atribución de IA.
- Si tocás una tarea, actualizá su test oculto y la referencia juntos.
