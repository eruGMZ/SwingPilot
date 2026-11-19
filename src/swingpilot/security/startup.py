"""Comprobaciones de arranque contra fugas de credenciales (REQ-G-033, REQ-G-091, REQ-G-093;
INV-012 Fail-Closed). Una lista no vacía de violaciones impide arrancar.

- `.env` debe existir y no ser legible ni escribible por grupo u otros (permisos 600 o 400).
- Credenciales de Binance/Telegram no deben estar en el entorno del proceso.
- En modo Live, `ANTHROPIC_LOG` no puede estar en `debug` (los logs de depuración del SDK
  incluyen el contenido de los prompts).
"""
import os
import stat
from pathlib import Path
from typing import Mapping

from .credentials import process_env_violations

MODES = ("RESEARCH", "PAPER", "LIVE")  # REQ-G-080


def startup_violations(env_path: str | Path, mode: str,
                       environ: Mapping[str, str] | None = None) -> list[str]:
    if mode not in MODES:
        return [f"MODE_UNKNOWN:{mode}"]
    env = os.environ if environ is None else environ
    out: list[str] = []
    p = Path(env_path)
    try:
        st = p.stat()
    except OSError:
        out.append("ENV_FILE_MISSING")
    else:
        if not stat.S_ISREG(st.st_mode):
            out.append("ENV_FILE_NOT_REGULAR")
        elif st.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            out.append(f"ENV_FILE_PERMISSIONS:{oct(stat.S_IMODE(st.st_mode))}")
    out += [f"SECRET_IN_PROCESS_ENV:{n}" for n in process_env_violations(env)]
    if mode == "LIVE" and env.get("ANTHROPIC_LOG", "").strip().lower() == "debug":
        out.append("ANTHROPIC_DEBUG_LOG_IN_LIVE")
    return out
