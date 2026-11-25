"""Almacén recuperable de preregistros (CR-023 §C.4.1, bloque B1).

Ruta: ``<root>/<experiment_id>/<sha256>.json``. El contenido son los bytes exactos
``canonical_json(content).encode("utf-8")`` cuyo SHA-256 es ``FrozenPreregistration.sha256``.

Reglas:
- Orden de escritura: creación exclusiva (O_EXCL, sin sobrescritura) → fsync del archivo →
  fsync de la cadena de directorios → relectura con un descriptor nuevo y comprobación
  SHA-256(bytes) = nombre.
- El nombre es el hash: cada lectura lo recalcula y lo compara (con el nombre y, si se pide,
  con el hash citado por PREREGISTERED).
- Frontera del almacén (revisión del propietario de B1): `root`, el directorio del experimento
  y el archivo se abren siempre con O_NOFOLLOW, y todo acceso por debajo de `root` es relativo a
  descriptores de directorio ya abiertos (`dir_fd`), nunca por ruta. Un enlace simbólico en
  `root`, en el directorio del experimento o en el archivo no puede desviar lecturas, escrituras
  ni inventarios fuera del almacén (→ Corrupt), y no hay carrera entre comprobación y uso: el
  objeto comprobado es el mismo que se usa. Los ancestros de `root` no forman parte de la
  frontera; el padre de `root` debe existir (no se crea).
- Durabilidad de directorios: tras escribir (o confirmar un archivo ya presente) se hace fsync
  del directorio del experimento, de `root` y del padre de `root`, siempre, no solo cuando esta
  llamada creó el directorio: un intento anterior pudo crearlo y fallar antes de su fsync.
- Preservación: este módulo NUNCA borra, renombra, reemplaza ni trunca. Un archivo parcial
  permanece y se lee después como corrupto; no hay reparación automática (Fail-Closed).
- Intervención manual: un fallo de escritura (archivo parcial, durabilidad no confirmada) exige
  la intervención del propietario, pero esa intervención NO autoriza por sí misma a borrar,
  sustituir ni reparar evidencia almacenada. Todo archivo del almacén, incluido un parcial o un
  huérfano, se conserva como evidencia; cualquier tratamiento posterior requiere una decisión
  expresa del propietario por el procedimiento de gobernanza aplicable.
- Un archivo sin PREREGISTERED que lo cite es huérfano: se conserva, sin autoridad.
- Todos los fallos son fallos técnicos de evidencia (independence_status INDETERMINATE).

No se integra aún con ``preregister()`` ni con el registro de experimentos.
"""
from __future__ import annotations

import contextlib
import errno
import hashlib
import json
import os
import re
import stat
from pathlib import Path

from swingpilot.research.experiments import valid_experiment_id

# Solo constante: ni la importación ni el constructor crean este directorio.
DEFAULT_ROOT = Path(__file__).resolve().parents[3] / "research" / "preregistrations"

_SHA256 = re.compile(r"[0-9a-f]{64}")
_FILE_NAME = re.compile(r"([0-9a-f]{64})\.json")
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW

CITED = "CITED"
ORPHAN = "ORPHAN"
INVALID_NAME = "INVALID_NAME"


class PreregStoreError(RuntimeError):
    """Base: fallo técnico de evidencia del almacén de preregistros."""


class PreregStoreRejected(PreregStoreError):
    """Entrada inválida; no se escribió nada."""


class PreregContentMissing(PreregStoreError):
    """Falta el archivo citado."""


class PreregContentCorrupt(PreregStoreError):
    """El archivo no coincide con su nombre, no es canónico, es de otro experimento, difiere
    del contenido que se intentó escribir, o la ruta del almacén atraviesa un enlace simbólico o
    un objeto que no es del tipo esperado (frontera del almacén)."""


class PreregContentConflict(PreregStoreError):
    """El contenido verificado tiene un hash distinto del citado por PREREGISTERED."""


class PreregStoreWriteUncertain(PreregStoreError):
    """Fallo tras abrir el archivo: el estado en disco es incierto. Puede quedar un archivo
    parcial, que se conserva y se lee como corrupto (sin reparación automática)."""


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _valid_sha(sha256) -> bool:
    return isinstance(sha256, str) and _SHA256.fullmatch(sha256) is not None


def _check_content(data: bytes, experiment_id: str, exc) -> dict:
    """Comprueba que `data` es un objeto JSON canónico del experimento. Lanza `exc` si no."""
    from swingpilot.research.preregistration import canonical_json  # local: evita ciclo futuro
    try:
        obj = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise exc(f"el contenido no es JSON válido: {e}") from e
    if not isinstance(obj, dict):
        raise exc("el contenido no es un objeto JSON")
    try:
        canonical = canonical_json(obj).encode("utf-8")
    except (TypeError, ValueError) as e:
        raise exc(f"el contenido no se puede canonizar: {e}") from e
    if canonical != data:
        raise exc("el contenido no es JSON canónico")
    if obj.get("experiment_id") != experiment_id:
        raise exc("el experiment_id del contenido no coincide con el del almacén")
    return obj


def _read_all(name: str, dir_fd: int) -> bytes:
    """Lee `name` relativo a `dir_fd`, sin seguir enlaces simbólicos; solo archivos regulares."""
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dir_fd)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(errno.EINVAL, "no es un archivo regular")
        chunks = []
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _boundary(what: str, e: OSError) -> PreregContentCorrupt:
    return PreregContentCorrupt(f"{what}: enlace simbólico, objeto no válido o ilegible en la ruta del "
                                f"almacén ({e!r}); frontera del almacén (CR-023 §C.4.1)")


class PreregistrationStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    # --- validación y rutas -------------------------------------------------------------
    @staticmethod
    def _validate_ids(experiment_id, sha256) -> None:
        if not valid_experiment_id(experiment_id):
            raise PreregStoreRejected(f"experiment_id inválido: {experiment_id!r}")
        if not _valid_sha(sha256):
            raise PreregStoreRejected(f"sha256 inválido: {sha256!r}")

    def path_for(self, experiment_id: str, sha256: str) -> Path:
        """Ruta informativa. Ningún acceso se hace por esta ruta (ver frontera del almacén)."""
        self._validate_ids(experiment_id, sha256)
        return self.root / experiment_id / f"{sha256}.json"

    # --- descriptores de directorio (frontera) --------------------------------------------
    @contextlib.contextmanager
    def _open_dirs(self, experiment_id: str, *, create: bool):
        """Produce (fd del padre de root, fd de root, fd del experimento) abiertos sin seguir
        enlaces simbólicos. Con `create`, crea root y el directorio del experimento si faltan
        (mkdir relativo a descriptores). Sin `create`, un componente ausente → None."""
        fds: list[int] = []
        try:
            try:
                parent_fd = os.open(self.root.parent, os.O_RDONLY | os.O_DIRECTORY)
            except FileNotFoundError as e:
                if not create:
                    yield None
                    return
                raise PreregStoreError(f"el padre de root no existe: {self.root.parent}") from e
            except OSError as e:
                raise PreregStoreError(f"no se puede abrir el padre de root {self.root.parent}: {e!r}") from e
            fds.append(parent_fd)
            current = parent_fd
            for name, what in ((self.root.name, "root"), (experiment_id, "directorio del experimento")):
                if create:
                    try:
                        os.mkdir(name, 0o755, dir_fd=current)
                    except FileExistsError:
                        pass                         # existente: se valida al abrirlo sin seguir enlaces
                    except OSError as e:
                        raise PreregStoreError(f"no se pudo crear {what}: {e!r}") from e
                try:
                    current = os.open(name, _DIR_FLAGS, dir_fd=current)
                except FileNotFoundError:
                    if create:
                        raise PreregStoreError(f"{what} desapareció durante la creación")
                    yield None
                    return
                except OSError as e:
                    raise _boundary(what, e) from e
                fds.append(current)
            yield tuple(fds)
        finally:
            for fd in reversed(fds):
                os.close(fd)

    @staticmethod
    def _fsync_chain(fds) -> None:
        """fsync del directorio del experimento, de root y del padre de root (en ese orden)."""
        for fd in reversed(fds):
            os.fsync(fd)

    # --- escritura ------------------------------------------------------------------------
    def write_frozen(self, frozen) -> Path:
        from swingpilot.research.preregistration import canonical_json  # local: evita ciclo
        data = canonical_json(frozen.content).encode("utf-8")
        return self.write(frozen.experiment_id, data, frozen.sha256)

    def write(self, experiment_id: str, data: bytes, sha256: str) -> Path:
        self._validate_ids(experiment_id, sha256)
        if not isinstance(data, (bytes, bytearray)):
            raise PreregStoreRejected("los datos deben ser bytes")
        data = bytes(data)
        if _sha256_hex(data) != sha256:
            raise PreregStoreRejected("SHA-256(bytes) no coincide con el sha256 indicado")
        _check_content(data, experiment_id, PreregStoreRejected)

        name = f"{sha256}.json"
        path = self.path_for(experiment_id, sha256)
        with self._open_dirs(experiment_id, create=True) as fds:
            exp_fd = fds[-1]
            try:
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444, dir_fd=exp_fd)
            except FileExistsError:
                # Ya presente (reintento o carrera; también un enlace simbólico con ese nombre).
                return self._existing(path, name, fds, experiment_id, sha256, data)
            except OSError as e:
                raise PreregStoreError(f"no se pudo crear {path}: {e!r}") from e
            # A partir de aquí cualquier fallo deja el estado incierto; nada se borra ni se repara.
            try:
                try:
                    view = memoryview(data)
                    while view:
                        n = os.write(fd, view)
                        view = view[n:]
                    os.fsync(fd)
                finally:
                    os.close(fd)
                self._fsync_chain(fds)
                reread = _read_all(name, exp_fd)  # descriptor nuevo
            except BaseException as e:
                raise PreregStoreWriteUncertain(f"escritura incierta de {path}: {e!r}") from e
            if _sha256_hex(reread) != sha256:
                raise PreregStoreWriteUncertain(f"la relectura de {path} no coincide con su nombre")
            return path

    def _existing(self, path: Path, name: str, fds, experiment_id: str, sha256: str, data: bytes) -> Path:
        """Archivo ya presente (reintento o carrera). Mismos bytes verificados → se vuelve a hacer
        fsync del archivo y de la cadena de directorios antes de informar éxito: un intento
        anterior pudo fallar en un fsync y dejar los bytes o las entradas solo en caché. Bytes
        distintos → Corrupt (sin reparación)."""
        existing = self._read_verified(name, fds[-1], path, sha256)
        if existing != data:
            raise PreregContentCorrupt(f"el archivo existente difiere de los bytes a escribir: {path}")
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fds[-1])
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            self._fsync_chain(fds)
        except BaseException as e:
            raise PreregStoreWriteUncertain(f"durabilidad no confirmada de {path}: {e!r}") from e
        return path  # idempotente: mismos bytes, sin escribir

    # --- lectura --------------------------------------------------------------------------
    @staticmethod
    def _read_verified(name: str, exp_fd: int, path: Path, sha256: str) -> bytes:
        """Lee y comprueba hash == nombre. Falta → Missing; no coincide o frontera → Corrupt."""
        try:
            data = _read_all(name, exp_fd)
        except FileNotFoundError as e:
            raise PreregContentMissing(f"falta el archivo {path}") from e
        except OSError as e:
            raise _boundary(f"archivo {path}", e) from e
        if _sha256_hex(data) != sha256:
            raise PreregContentCorrupt(f"el contenido de {path} no coincide con su nombre")
        return data

    def read(self, experiment_id: str, sha256: str) -> bytes:
        path = self.path_for(experiment_id, sha256)
        with self._open_dirs(experiment_id, create=False) as fds:
            if fds is None:
                raise PreregContentMissing(f"falta el archivo {path}")
            return self._read_verified(f"{sha256}.json", fds[-1], path, sha256)

    def load(self, experiment_id: str, sha256: str) -> dict:
        data = self.read(experiment_id, sha256)
        return _check_content(data, experiment_id, PreregContentCorrupt)

    def verify_cited(self, experiment_id: str, cited_sha256: str, expected_sha256: str | None = None) -> dict:
        """Verifica el contenido citado por PREREGISTERED (CR-023 §C.4.1.3). El archivo se nombra
        con el hash citado, así que un contenido distinto de su nombre es corrupción (Corrupt, igual
        que `read`/`load`). `expected_sha256` (p. ej. el de un preregistro en memoria) distinto del
        citado → dos contenidos para el mismo PREREGISTERED: Conflict. Falta → Missing."""
        self._validate_ids(experiment_id, cited_sha256)
        if expected_sha256 is not None and expected_sha256 != cited_sha256:
            raise PreregContentConflict(
                f"el hash esperado {expected_sha256!r} difiere del citado por PREREGISTERED {cited_sha256}")
        return self.load(experiment_id, cited_sha256)

    # --- inventario -----------------------------------------------------------------------
    def entries(self, experiment_id: str, cited_sha256s: set[str]) -> list[dict]:
        """Clasifica cada entrada del directorio: CITED / ORPHAN / INVALID_NAME. Solo lectura.
        Directorio ausente → lista vacía; enlace simbólico en la ruta → Corrupt."""
        if not valid_experiment_id(experiment_id):
            raise PreregStoreRejected(f"experiment_id inválido: {experiment_id!r}")
        with self._open_dirs(experiment_id, create=False) as fds:
            if fds is None:
                return []
            exp_fd = fds[-1]
            out = []
            for name in sorted(os.listdir(exp_fd)):
                m = _FILE_NAME.fullmatch(name)
                is_file = stat.S_ISREG(os.stat(name, dir_fd=exp_fd, follow_symlinks=False).st_mode)
                if m is None or not is_file:
                    out.append({"name": name, "status": INVALID_NAME, "sha256": None})
                elif m.group(1) in cited_sha256s:
                    out.append({"name": name, "status": CITED, "sha256": m.group(1)})
                else:
                    out.append({"name": name, "status": ORPHAN, "sha256": m.group(1)})
            return out
