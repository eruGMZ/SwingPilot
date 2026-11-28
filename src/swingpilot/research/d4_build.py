"""D4: construcción de la snapshot de desarrollo con reintentos HTTP opt-in y diagnóstico operativo aislado
(DEC-026; CR-023 §C.1; DEC-013).

Capa EXCLUSIVA de D4. No modifica `BinancePublicClient`, su transporte por defecto, la reconexión LIVE ni las rutas
de snapshots de evaluación: el reintento solo existe si quien llama construye explícitamente un
`D4RetryTransport` y lo inyecta en el cliente.

Política (DEC-026):
- Máximo 3 intentos totales por petición transitoria; espera de 1 s y luego 2 s. Sin reinicio automático de la
  construcción completa: agotados los reintentos, la construcción completa se cancela (el rollback y el sellado de
  `build_snapshot` no cambian).
- Solo se reintentan fallos explícitamente clasificados como transitorios (red/timeout, HTTP 500/502/503/504).
  Nunca: HTTP 429/418, permisos (401/403/451), otros 4xx, TLS, corrupción (JSON/UTF-8), integridad, fechas, límites
  ni ningún error no clasificado.
- Diagnóstico: líneas JSON bajo `var/diagnostics/` con campos de una lista cerrada; sin credenciales, cabeceras,
  cuerpos de respuesta, URL completas ni variables de entorno. Nunca dentro de snapshots, manifiestos, resultados
  experimentales ni entradas del motor de investigación. No es un estado ABORTED contractual ni un evento del registro.
"""
from __future__ import annotations

import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

from swingpilot.market_data.binance_public import (DEFAULT_BASE_URL, BinancePublicClient, PublicApiError,
                                                   _urllib_transport)

from .snapshot import SNAPSHOT_INTERVALS, SnapshotError, build_snapshot, valid_snapshot_id

D_DEV = "2026-11-01"                 # 2026-11-01T00:00:00Z exclusivo (DEC-026)
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (1.0, 2.0)         # tras el intento 1 y tras el intento 2
TRANSIENT_HTTP = frozenset({500, 502, 503, 504})
RATE_LIMIT_HTTP = frozenset({429, 418})
PERMISSION_HTTP = frozenset({401, 403, 451})

TRANSIENT_NETWORK = "TRANSIENT_NETWORK"
TRANSIENT_HTTP_5XX = "TRANSIENT_HTTP"
RATE_LIMITED = "RATE_LIMITED"
PERMISSION = "PERMISSION"
PERMANENT_HTTP = "PERMANENT_HTTP"
TLS_ERROR = "TLS_ERROR"
CORRUPTION = "CORRUPTION"
UNCLASSIFIED = "UNCLASSIFIED"
RETRIES_EXHAUSTED = "RETRIES_EXHAUSTED"
BUILD_REJECTED = "BUILD_REJECTED"
SEALING_ERROR = "SEALING_ERROR"
INTERRUPTED = "INTERRUPTED"
_TRANSIENT_CLASSES = frozenset({TRANSIENT_NETWORK, TRANSIENT_HTTP_5XX})
CLASSIFICATIONS = frozenset({TRANSIENT_NETWORK, TRANSIENT_HTTP_5XX, RATE_LIMITED, PERMISSION, PERMANENT_HTTP,
                             TLS_ERROR, CORRUPTION, UNCLASSIFIED, RETRIES_EXHAUSTED, BUILD_REJECTED,
                             SEALING_ERROR, INTERRUPTED})
EXIT_OK, EXIT_BUILD_FAILED, EXIT_REFUSED, EXIT_INTERRUPTED = 0, 1, 2, 130


class D4TransportError(PublicApiError):
    """Fallo de una petición ya clasificado. Su mensaje no contiene URL, cabeceras ni cuerpos."""

    def __init__(self, classification: str, http_status: int | None, attempts: int):
        self.classification = classification
        self.http_status = http_status
        self.attempts = attempts
        super().__init__(f"D4 {classification} status={http_status} attempts={attempts}")


def classify(exc: BaseException) -> tuple[str, int | None]:
    """Clasificación cerrada de una excepción de transporte → (clase, estado HTTP o None)."""
    if isinstance(exc, urllib.error.HTTPError):
        code = int(exc.code)
        if code in RATE_LIMIT_HTTP:
            return RATE_LIMITED, code
        if code in PERMISSION_HTTP:
            return PERMISSION, code
        if code in TRANSIENT_HTTP:
            return TRANSIENT_HTTP_5XX, code
        return PERMANENT_HTTP, code
    if isinstance(exc, (json.JSONDecodeError, UnicodeDecodeError)):
        return CORRUPTION, None
    if isinstance(exc, ssl.SSLError) or (isinstance(exc, urllib.error.URLError)
                                         and isinstance(exc.reason, ssl.SSLError)):
        return TLS_ERROR, None
    if isinstance(exc, (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError)):
        return TRANSIENT_NETWORK, None
    return UNCLASSIFIED, None


def stage_from_url(url: str) -> str:
    """Etapa de una petición sin conservar la URL: `server_time` o `klines:<intervalo>` (lista cerrada)."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.path == "/api/v3/time":
            return "server_time"
        if parsed.path == "/api/v3/klines":
            iv = urllib.parse.parse_qs(parsed.query).get("interval", [""])[0]
            return f"klines:{iv}" if iv in SNAPSHOT_INTERVALS else "klines"
    except Exception:
        pass
    return "request"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class DiagnosticsRecorder:
    """Diagnóstico operativo aislado: JSON Lines con campos de lista cerrada, en `diagnostics_dir/<run_id>.jsonl`.
    Rechaza ubicaciones dentro de las raíces prohibidas (snapshots, manifiestos, investigación). Un fallo de escritura
    no altera el resultado de la construcción."""
    FIELDS = ("run_id", "snapshot_id", "d_dev", "timestamp_utc", "event", "stage", "attempt", "classification",
              "http_status", "elapsed_ms", "exit_code")

    def __init__(self, diagnostics_dir: Path, run_id: str, snapshot_id: str, d_dev: str, *,
                 forbidden_roots: Sequence[Path] = (), clock: Callable[[], float] = time.monotonic,
                 timestamp: Callable[[], str] = _utc_now_iso):
        if not valid_snapshot_id(snapshot_id):
            raise SnapshotError(f"identificador de snapshot no válido: {snapshot_id!r}")
        directory = Path(diagnostics_dir).resolve()
        for root in forbidden_roots:
            r = Path(root).resolve()
            if directory == r or r in directory.parents:
                raise SnapshotError("el diagnóstico no puede residir dentro de snapshots, manifiestos ni investigación")
        self.path = directory / f"{run_id}.jsonl"
        self._directory = directory
        self.run_id, self.snapshot_id, self.d_dev = run_id, snapshot_id, d_dev
        self._clock, self._timestamp, self._t0 = clock, timestamp, clock()
        self.write_errors = 0

    def record(self, event: str, *, stage: str, attempt: int | None = None, classification: str | None = None,
               http_status: int | None = None, exit_code: int | None = None) -> None:
        if classification is not None and classification not in CLASSIFICATIONS:
            classification = UNCLASSIFIED
        row = {"run_id": self.run_id, "snapshot_id": self.snapshot_id, "d_dev": self.d_dev,
               "timestamp_utc": self._timestamp(), "event": event, "stage": stage, "attempt": attempt,
               "classification": classification, "http_status": http_status,
               "elapsed_ms": int((self._clock() - self._t0) * 1000), "exit_code": exit_code}
        try:
            self._directory.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({k: row[k] for k in self.FIELDS}, sort_keys=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        except OSError:
            self.write_errors += 1


class D4RetryTransport:
    """Transporte opt-in con reintentos acotados. Envuelve un transporte `url -> JSON`; no reinicia nada fuera de la
    petición individual (la paginación se recupera porque cada página es una petición)."""

    def __init__(self, inner: Callable, *, recorder: DiagnosticsRecorder | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        if not callable(inner):
            raise TypeError("D4RetryTransport requiere un transporte invocable")
        self._inner, self._recorder, self._sleep = inner, recorder, sleep

    def __call__(self, url: str, *args, **kwargs) -> object:
        stage = stage_from_url(url)
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                return self._inner(url, *args, **kwargs)
            except D4TransportError:
                raise
            except Exception as exc:
                cls, status = classify(exc)
                if self._recorder:
                    self._recorder.record("ATTEMPT_FAILED", stage=stage, attempt=attempt, classification=cls,
                                          http_status=status)
                if cls not in _TRANSIENT_CLASSES:
                    raise D4TransportError(cls, status, attempt) from exc
                if attempt == MAX_ATTEMPTS:
                    raise D4TransportError(RETRIES_EXHAUSTED, status, attempt) from exc
                self._sleep(BACKOFF_SECONDS[attempt - 1])
        raise AssertionError("inalcanzable")  # pragma: no cover


def _find_transport_error(exc: BaseException) -> D4TransportError | None:
    seen = 0
    while exc is not None and seen < 20:
        if isinstance(exc, D4TransportError):
            return exc
        exc, seen = exc.__cause__ or exc.__context__, seen + 1
    return None


def run_d4_build(*, snapshot_id: str, data_root: Path, manifest_dir: Path, diagnostics_dir: Path,
                 inner_transport: Callable, reserved_windows_source: Callable, d_dev: str = D_DEV,
                 base_url: str = DEFAULT_BASE_URL, forbidden_roots: Sequence[Path] | None = None,
                 sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic,
                 run_id: str | None = None, now=lambda: datetime.now(timezone.utc)) -> int:
    """Construye la snapshot de desarrollo con reintentos D4 y diagnóstico. Devuelve el código de salida."""
    run_id = run_id or f"D4-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    forbidden = [data_root, manifest_dir] if forbidden_roots is None else list(forbidden_roots)
    rec = DiagnosticsRecorder(diagnostics_dir, run_id, snapshot_id, d_dev, forbidden_roots=forbidden, clock=clock)
    client = BinancePublicClient(base_url, transport=D4RetryTransport(inner_transport, recorder=rec, sleep=sleep))
    rec.record("BUILD_START", stage="build")
    try:
        build_snapshot(client, snapshot_id, data_root, manifest_dir, d_dev=d_dev, reserved_windows=[],
                       reserved_windows_source=reserved_windows_source, now=now)
    except KeyboardInterrupt:
        rec.record("BUILD_FAILED", stage="build", classification=INTERRUPTED, exit_code=EXIT_INTERRUPTED)
        raise
    except Exception as exc:
        terr = _find_transport_error(exc)
        if terr is not None:
            cls, status, stage = terr.classification, terr.http_status, "download"
        else:
            from .snapshot import SealingError
            cls = SEALING_ERROR if isinstance(exc, SealingError) else BUILD_REJECTED
            status, stage = None, "build"
        rec.record("BUILD_FAILED", stage=stage, classification=cls, http_status=status, exit_code=EXIT_BUILD_FAILED)
        return EXIT_BUILD_FAILED
    rec.record("BUILD_OK", stage="build", exit_code=EXIT_OK)
    return EXIT_OK


def main(argv=None) -> int:
    """Punto de entrada de la descarga real de D4. BLOQUEADO: exige `--confirm` y una referencia de autorización
    explícita del propietario. El aislamiento de credenciales es procedimental (`env -i`, ver
    implementation/d4_execution_procedure.md): el módulo no lee el entorno. No lo ejecuta ninguna prueba."""
    import argparse
    p = argparse.ArgumentParser(prog="python -m swingpilot.research.d4_build")
    p.add_argument("--id", required=True)
    p.add_argument("--confirm", action="store_true")
    p.add_argument("--authorization-ref", default="", dest="auth_ref",
                   help="referencia a la autorización explícita del propietario (D, hoy BLOQUEADA)")
    a = p.parse_args(argv)
    if not a.confirm or not a.auth_ref.strip():
        print("D4 real: se requiere --confirm y --authorization-ref (autorización D del propietario)", file=sys.stderr)
        return EXIT_REFUSED
    from . import cli
    diag = cli.REPO / "var" / "diagnostics" / "d4"
    windows = cli.reserved_windows_provider()                       # fuente autoritativa; antes de cualquier descarga
    forbidden = [cli.DATA_ROOT, cli.MANIFEST_DIR, cli.REPO / "research"]
    return run_d4_build(snapshot_id=a.id, data_root=cli.DATA_ROOT, manifest_dir=cli.MANIFEST_DIR, diagnostics_dir=diag,
                        inner_transport=_urllib_transport, reserved_windows_source=lambda: windows,
                        forbidden_roots=forbidden)


if __name__ == "__main__":
    sys.exit(main())
