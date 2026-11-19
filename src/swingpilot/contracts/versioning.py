"""Compatibilidad de versiones de contrato (REQ-G-064, TC-MSG-002).

Regla (api_contracts.md §1): schema_version sigue semver; los cambios
incompatibles requieren nueva versión mayor. Un receptor acepta mensajes
de su misma versión mayor y rechaza cualquier otra (Fail-Closed): el
rechazo es la acción por defecto; la escalación a revisión la decide el
llamador al capturar SchemaVersionError.
"""
import re

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class SchemaVersionError(ValueError):
    pass


def parse_semver(v: str) -> tuple[int, int, int]:
    if not isinstance(v, str) or not (m := _SEMVER.match(v)):
        raise SchemaVersionError(f"schema_version no es semver válido: {v!r}")
    return int(m[1]), int(m[2]), int(m[3])


def check_compatibility(message_version: str, supported_version: str) -> None:
    """Lanza SchemaVersionError si la versión mayor difiere."""
    if parse_semver(message_version)[0] != parse_semver(supported_version)[0]:
        raise SchemaVersionError(
            f"versión mayor incompatible: mensaje {message_version}, "
            f"soportada {supported_version}"
        )
