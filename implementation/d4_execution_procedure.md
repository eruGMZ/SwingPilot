# Procedimiento futuro de D4 — descarga real con aislamiento de credenciales (NO EJECUTAR)

**Estado:** preparado en D4-IMPL (DEC-026). Requiere la autorización D del propietario, hoy **BLOQUEADA**, y D4-QA-SYNTHETIC aceptada.

**Fuente:** únicamente `https://data-api.binance.vision`, `GET /api/v3/time` y `GET /api/v3/klines` (BTC/USDT; 1d, 4h, 1h; `limit=1000`). Sin endpoints firmados ni cuentas.

## Precondiciones (verificar y registrar antes de ejecutar)
1. Autorización D explícita del propietario (referencia citable) y D4-QA-SYNTHETIC aceptada.
2. `git status` limpio; HEAD conocido; registro `research/experiments/registry.jsonl` con md5 anotado; `research/snapshots/SNAP-0001.json` y `var/snapshots/SNAP-0001/` inexistentes.
3. Ninguna ventana reservada activa que alcance D_dev (la fuente autoritativa se evalúa antes de descargar; Fail-Closed).
4. Reloj del sistema sincronizado (D_dev debe ser anterior a la hora del servidor).

## Ejecución (entorno sin credenciales)
```
env -i HOME="$HOME" PATH="$PATH" LANG=C.UTF-8 PYTHONPATH=src \
  python -I -m swingpilot.research.d4_build --id SNAP-0001 --confirm --authorization-ref <REF-AUTORIZACION-D>
```
- `env -i` descarta todas las variables heredadas (sin `.env`, claves, tokens ni proxies). El módulo no lee el entorno (regla de aislamiento de `tests/security`); el aislamiento es procedimental: verificar con `env -i … env` que no hay variables sensibles antes de lanzar.
- No exportar claves de Binance, Telegram ni de IA en esa shell; no usar sesiones con agentes cargados.
- `D_dev` queda fijado en el módulo (`2026-11-01`, exclusivo); no es parámetro.

## Durante y después
- Sin reintento manual automático: si el código de salida ≠ 0 la construcción está cancelada y revertida; revisar `var/diagnostics/d4/<run_id>.jsonl` (solo diagnóstico operativo) y decidir con el propietario antes de repetir.
- Éxito (exit 0): ejecutar `python -m swingpilot.research.cli verify-snapshot --id SNAP-0001`; comprobar md5 del registro (sin cambios), ausencia de `oos`/`lockbox`, permisos de sellado y que los diagnósticos no estén dentro de snapshots ni `research/`.
- 429/418: no repetir hasta que el propietario lo decida (posible bloqueo de IP).
- Registrar el resultado en `progress.md`/`session-handoff.md`; D4 no se cierra sin QA independiente y aceptación del propietario.
