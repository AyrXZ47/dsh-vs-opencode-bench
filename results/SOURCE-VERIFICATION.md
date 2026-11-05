# Verificación de fuentes de la fase 2

Método: HTTP directo con `curl` para docs, listas, GitHub, OpenCVE, Notebookcheck y Arch Wiki; Phoronix bloquea `curl` con 403, así que se verificó con Jina Reader (`https://r.jina.ai/http://...`) y se comprobó el título y el contenido. GitLab Freedesktop devuelve un bot challenge, no el work item.

## Verificado

| Fuente | Qué se verificó |
|---|---|
| `docs.kernel.org/gpu/amdgpu/userq.html` | Página de Linux 7.4.0-rc1; parámetro `user_queue` 0/1/2. |
| `docs.kernel.org/gpu/amdgpu/ring-buffer.html`, `gc/mes.html`, `driver-core.html`, `debugfs.html`, `module-parameters.html` | Documentación real de amdgpu/MES/TTM/ReBAR. |
| Phoronix `Linux-6.16-AMDGPU-User-Queues` | Título: “Initial AMDGPU User Mode Queues Support Prepped For Linux 6.16”; RDNA3/RDNA4, detrás de parámetro. |
| Phoronix `Linux-Patches-Fix-DRM-Fair` | Linux 7.2 revierte `fair` a FIFO por regresión en RX 9070 XT; parches para 7.3. |
| Phoronix `AMDGPU-Linux-7.1-Multi-SDMA` | TTM con múltiples SDMA para 7.1. |
| Phoronix `More-Aggressive-TTM-Linux-7.3` | TTM/DMEMCG de Valve para 7.3. |
| Phoronix `Linux-7-Fix-Idle-RDNA4-Compute` | Fix de idle power en RDNA4 para Linux 7.0; firmware MES nuevo en camino. |
| Phoronix `Linux-7.3-DRM` | DMEMCG eviction en 7.3. |
| Phoronix `old-amdgpu-eoy2025` | RDNA3/RDNA4 rinden mal en Linux 6.19. |
| OpenCVE `CVE-2026-89812` | `drm/amdgpu: force complete the MES ring fences on reset`; `no_scheduler = true`; versiones corregidas 6.12.114, 6.18.57, 7.2.5, 7.3. |
| OpenCVE `CVE-2026-89813` | `drm/amdgpu: force complete the KIQ ring fences on reset`; mismas versiones corregidas. |
| GitHub `ValveSoftware/SteamOS/issues/2811` | Issue abierto el 2026-09-13: RX 9070 XT pierde ~7.4 GiB de VRAM hacia GTT al suspender; 60→12 fps; sin fix confirmado. |
| Notebookcheck `Radeon-RX-9000-GPUs-officially-support-UEFI-systems-only...` | RX 9000 soporta oficialmente solo UEFI; CSM/legacy sin Smart Access Memory. |
| Arch Wiki `AMDGPU#User_queues` | UMQ experimental, RDNA3+, `AMD_USERQ=1`. |
| `lists.freedesktop.org/archives/amd-gfx/2026-January/137683.html` | `drm/amdgpu/gfx12.1: add support for disable_kq`; propone desactivar kernel queues por defecto. |
| `lists.freedesktop.org/archives/dri-devel/2024-August/465216.html` | `drm/amdgpu: Re-validate evicted buffers v2`; buffers VRAM+GTT podían quedarse en GTT. |
| `lists.freedesktop.org/archives/amd-gfx/2026-April/143210.html` y `lkml.iu.edu/2605.0/03211.html` | `drm/amdgpu: fix zero-size GDS range init on RDNA4`; GDS/GWS/OA de tamaño cero. |
| `github.com/torvalds/linux/.../gfx_v12_0.c` | `disable_uq` y `userq_funcs` para GFX12. |

## No verificado

- `gitlab.freedesktop.org/drm/amd/-/work_items/5821` y `/5663`: el servidor devuelve una página de verificación anti-bot. Las URLs existen, pero no se pudieron leer el título, estado, fecha de cierre ni los detalles que afirmó `dsh-ds`. El resto de la respuesta de `dsh-ds` sí está respaldado.
