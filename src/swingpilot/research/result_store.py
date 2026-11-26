"""Almacén inmutable de resultados de ventana (CR-024 v1.12 §B.3, bloque CR24-I2a).

Ruta: ``<root>/<EXP-NNNN>/<partition>.result.json`` (partition ∈ {oos, lockbox}); almacén distinto del de
preregistros. Contenido: bytes canónicos de B.1 (lectura estricta con round-trip byte a byte).

Protocolo de `prereg_store` (reutiliza su frontera de descriptores): creación exclusiva O_EXCL|O_NOFOLLOW,
fsync del archivo y de la cadena de directorios, relectura con descriptor nuevo y comprobación de bytes y
``evaluation_hash``. Sin sobrescritura, borrado, renombrado ni reparación. Bytes idénticos sobre un archivo
presente → idempotente (con nuevo fsync); distintos → ``ResultStoreConflict``. Sin integración con el registro.
"""
from __future__ import annotations

import contextlib
import os
from pathlib import Path

from swingpilot.research import prereg_store as P
from swingpilot.research.experiments import valid_experiment_id
from swingpilot.research.result_serialization import ResultSerializationError, evaluation_hash, parse_strict

PARTITIONS = ("oos", "lockbox")   # contrato B.1: minúsculas, idénticas a snapshot.SEALED; sin alias


class ResultStoreError(RuntimeError):
    """Base: fallo técnico de evidencia del almacén de resultados."""


class ResultStoreRejected(ResultStoreError):
    """Entrada inválida o no canónica; nada escrito."""


class ResultStoreMissing(ResultStoreError):
    """Falta el archivo."""


class ResultStoreCorrupt(ResultStoreError):
    """Frontera (enlace simbólico/objeto no regular), ilegible o no canónico."""


class ResultStoreConflict(ResultStoreError):
    """Archivo presente con bytes distintos a los que se intentan escribir (incoherente; sin reemplazo)."""


class ResultStoreWriteUncertain(ResultStoreError):
    """Fallo tras abrir el archivo o durabilidad no confirmada; lo escrito se conserva."""


RESULTS_DIRNAME = "window_results"


def for_registry(registry) -> "ResultStore":
    """Almacén de resultados ligado a un registro: ``<dir del registro>/window_results`` (distinto del almacén
    de preregistros). Única fuente para las lecturas autoritativas de ET-4/5/6, `resolve_lockbox` y el CLI."""
    path = getattr(registry, "path", None)
    if path is None:
        raise ResultStoreRejected("sin registro: el almacén de resultados no es localizable")
    return ResultStore(Path(path).parent / RESULTS_DIRNAME)


class ResultStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self._dirs = P.PreregistrationStore(self.root)   # solo para la frontera de descriptores

    @staticmethod
    def _name(experiment_id, partition) -> str:
        if not valid_experiment_id(experiment_id):
            raise ResultStoreRejected(f"experiment_id inválido: {experiment_id!r}")
        if type(partition) is not str or partition not in PARTITIONS:
            raise ResultStoreRejected(f"partition inválida: {partition!r}")
        return f"{partition}.result.json"

    def path_for(self, experiment_id: str, partition: str) -> Path:
        """Ruta informativa; ningún acceso se hace por ella."""
        return self.root / experiment_id / self._name(experiment_id, partition)

    @contextlib.contextmanager
    def _open(self, experiment_id, *, create):
        try:
            with self._dirs._open_dirs(experiment_id, create=create) as fds:
                yield fds
        except P.PreregContentCorrupt as e:
            raise ResultStoreCorrupt(str(e)) from e
        except P.PreregStoreError as e:
            raise ResultStoreError(str(e)) from e

    @staticmethod
    def _read(name, exp_fd, path) -> bytes:
        try:
            return P._read_all(name, exp_fd)
        except FileNotFoundError as e:
            raise ResultStoreMissing(f"falta el archivo {path}") from e
        except OSError as e:
            raise ResultStoreCorrupt(f"{path}: enlace simbólico, objeto no válido o ilegible ({e!r})") from e

    def write(self, experiment_id: str, partition: str, data: bytes) -> Path:
        name = self._name(experiment_id, partition)
        if not isinstance(data, (bytes, bytearray)):
            raise ResultStoreRejected("los datos deben ser bytes")
        data = bytes(data)
        try:
            parse_strict(data)
        except ResultSerializationError as e:
            raise ResultStoreRejected(f"bytes no canónicos: {e}") from e
        digest = evaluation_hash(data)
        path = self.path_for(experiment_id, partition)
        with self._open(experiment_id, create=True) as fds:
            exp_fd = fds[-1]
            try:
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444, dir_fd=exp_fd)
            except FileExistsError:
                return self._existing(path, name, fds, data)
            except OSError as e:
                raise ResultStoreError(f"no se pudo crear {path}: {e!r}") from e
            try:
                try:
                    view = memoryview(data)
                    while view:
                        view = view[os.write(fd, view):]
                    os.fsync(fd)
                finally:
                    os.close(fd)
                self._dirs._fsync_chain(fds)
                reread = P._read_all(name, exp_fd)       # descriptor nuevo
            except BaseException as e:
                raise ResultStoreWriteUncertain(f"escritura incierta de {path}: {e!r}") from e
            if reread != data or evaluation_hash(reread) != digest:
                raise ResultStoreWriteUncertain(f"la relectura de {path} no coincide con los bytes escritos")
            return path

    def _existing(self, path, name, fds, data) -> Path:
        existing = self._read(name, fds[-1], path)
        if existing != data:
            raise ResultStoreConflict(f"el archivo existente difiere de los bytes a escribir: {path}")
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fds[-1])
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            self._dirs._fsync_chain(fds)
        except BaseException as e:
            raise ResultStoreWriteUncertain(f"durabilidad no confirmada de {path}: {e!r}") from e
        return path

    def revalidate(self, experiment_id: str, partition: str, expected: bytes) -> None:
        """CR-024 B.6 (EVIDENCE_ONLY, solo CLI): revalida la durabilidad de la evidencia YA presente sin
        escribirla: relectura con descriptor nuevo, nuevo fsync del archivo y de la cadena de directorios y
        segunda relectura. Cualquier fallo o discrepancia → ResultStoreWriteUncertain (o Missing/Corrupt)."""
        name = self._name(experiment_id, partition)
        path = self.path_for(experiment_id, partition)
        with self._open(experiment_id, create=False) as fds:
            if fds is None:
                raise ResultStoreMissing(f"falta el archivo {path}")
            if self._read(name, fds[-1], path) != expected:
                raise ResultStoreWriteUncertain(f"la evidencia de {path} no coincide con la conciliada")
            try:
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fds[-1])
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
                self._dirs._fsync_chain(fds)
                again = P._read_all(name, fds[-1])          # descriptor nuevo tras el fsync
            except BaseException as e:
                raise ResultStoreWriteUncertain(f"durabilidad no revalidada de {path}: {e!r}") from e
            if again != expected:
                raise ResultStoreWriteUncertain(f"la relectura de {path} no coincide tras el fsync")

    def read(self, experiment_id: str, partition: str) -> bytes:
        name = self._name(experiment_id, partition)
        path = self.path_for(experiment_id, partition)
        with self._open(experiment_id, create=False) as fds:
            if fds is None:
                raise ResultStoreMissing(f"falta el archivo {path}")
            data = self._read(name, fds[-1], path)
        try:
            parse_strict(data)
        except ResultSerializationError as e:
            raise ResultStoreCorrupt(f"{path} no es canónico: {e}") from e
        return data
