#!/usr/bin/env python3
"""Emisor ZIP determinista y streaming para snapshots compartidos v1.

Sólo escribe ZIP_STORED con dos entradas estructurales iniciales
(manifest.json e index.json). No extrae archivos ni crea temporales.
"""
from __future__ import annotations

import hashlib
import os
import stat
import struct
import unicodedata
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Callable, Iterator

MAX_ENTRIES = 10_000
MAX_ZIP_BYTES = 512 * 1024 * 1024
MAX_NAME_BYTES = 1024
DEFAULT_CHUNK_SIZE = 1024 * 1024
UINT32_MAX = (1 << 32) - 1
UTF8_FLAG = 0x0800
ZIP_STORED = 0
DOS_DATE_1980_01_01 = 0x21


class SharedBackupZipError(Exception):
    """Error seguro de estructura, límite o lectura del ZIP."""


def validate_logical_path(name: str) -> bytes:
    if not isinstance(name, str) or not name or "\x00" in name or "\\" in name:
        raise SharedBackupZipError("nombre lógico vacío o con separador/NUL no permitido")
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in name):
        raise SharedBackupZipError("nombre lógico contiene caracteres de control")
    if unicodedata.normalize("NFC", name) != name:
        raise SharedBackupZipError("nombre lógico no está normalizado en Unicode NFC")
    if ":" in name or name.startswith("/"):
        raise SharedBackupZipError("ruta lógica absoluta o con prefijo de unidad")
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise SharedBackupZipError("ruta lógica insegura")
    if path.as_posix() != name or any(part.endswith((".", " ")) for part in path.parts):
        raise SharedBackupZipError("ruta lógica no normalizada")
    encoded = name.encode("utf-8", "strict")
    if len(encoded) > MAX_NAME_BYTES:
        raise SharedBackupZipError("nombre lógico excede el máximo de bytes")
    return encoded


def _stat_identity(st: os.stat_result) -> tuple[int, ...]:
    return (
        st.st_dev, st.st_ino, st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode),
        st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns,
    )


def _open_root_regular(
    path: Path, allowed_root: Path, expected: tuple[int, ...] | None = None
) -> tuple[BinaryIO, tuple[int, ...]]:
    path = Path(path)
    if not path.is_absolute():
        path = Path.cwd() / path
    allowed_root = Path(allowed_root)
    if not allowed_root.is_absolute():
        allowed_root = Path.cwd() / allowed_root
    if ".." in path.parts or ".." in allowed_root.parts or not path.name:
        raise SharedBackupZipError("ruta de origen no normalizada")
    try:
        relative = path.relative_to(allowed_root)
    except ValueError as exc:
        raise SharedBackupZipError("origen fuera del directorio autorizado") from exc
    if not relative.parts:
        raise SharedBackupZipError("el origen no puede ser el propio directorio autorizado")
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    directory_fd = -1
    try:
        directory_fd = os.open(path.anchor, directory_flags)
        for component in path.parts[1:-1]:
            next_fd = os.open(component, directory_flags, dir_fd=directory_fd)
            directory_stat = os.fstat(next_fd)
            if not stat.S_ISDIR(directory_stat.st_mode) or directory_stat.st_uid != 0 or directory_stat.st_gid != 0:
                os.close(next_fd)
                raise SharedBackupZipError("directorio padre no es root:root o no es directorio real")
            os.close(directory_fd)
            directory_fd = next_fd
        before = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
        identity = _stat_identity(before)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_ISLNK(before.st_mode)
            or before.st_uid != 0
            or before.st_gid != 0
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1
            or before.st_size > MAX_ZIP_BYTES
        ):
            raise SharedBackupZipError("miembro de origen no es archivo regular root:root 0600")
        if expected is not None and identity != expected:
            raise SharedBackupZipError("miembro de origen cambió desde el preflight")
        fd = os.open(path.name, file_flags, dir_fd=directory_fd)
        stream = os.fdopen(fd, "rb")
        opened = os.fstat(stream.fileno())
        if _stat_identity(opened) != identity:
            stream.close()
            raise SharedBackupZipError("miembro de origen cambió durante la apertura")
        return stream, identity
    except SharedBackupZipError:
        raise
    except OSError as exc:
        raise SharedBackupZipError("no se pudo abrir el miembro sin seguir symlinks") from exc
    finally:
        if directory_fd >= 0:
            os.close(directory_fd)


def read_root_regular(path: Path, allowed_root: Path, *, limit: int) -> bytes:
    """Lee un archivo regular root:root 0600 bajo allowed_root con TOCTOU checks."""
    if type(limit) is not int or not 0 <= limit <= MAX_ZIP_BYTES:
        raise SharedBackupZipError("límite de lectura inválido")
    stream, identity = _open_root_regular(Path(path), Path(allowed_root))
    try:
        data = stream.read(limit + 1)
        if len(data) > limit or len(data) != identity[6]:
            raise SharedBackupZipError("archivo excede el límite o cambió durante lectura")
        if _stat_identity(os.fstat(stream.fileno())) != identity:
            raise SharedBackupZipError("archivo cambió durante lectura")
        return data
    finally:
        stream.close()


@dataclass(frozen=True)
class ZipMember:
    """Miembro preflighted; source es bytes o ruta regular root:root 0600."""

    name: str
    size: int
    crc32: int
    sha256: str
    source: bytes | Path | Callable[[], BinaryIO]
    source_identity: tuple[int, ...] | None = None
    allowed_root: Path | None = None

    @classmethod
    def from_bytes(cls, name: str, data: bytes) -> "ZipMember":
        validate_logical_path(name)
        if not isinstance(data, bytes):
            raise SharedBackupZipError("el miembro generado debe ser bytes")
        if len(data) > MAX_ZIP_BYTES:
            raise SharedBackupZipError("miembro excede el límite del ZIP")
        return cls(
            name=name,
            size=len(data),
            crc32=zlib.crc32(data) & UINT32_MAX,
            sha256=hashlib.sha256(data).hexdigest(),
            source=data,
        )

    @classmethod
    def from_factory(
        cls,
        name: str,
        opener: Callable[[], BinaryIO],
        *,
        max_size: int = MAX_ZIP_BYTES,
    ) -> "ZipMember":
        """Preflight de una fuente regenerable; se reabre y revalida al emitir."""
        validate_logical_path(name)
        if not callable(opener) or type(max_size) is not int or not 0 <= max_size <= MAX_ZIP_BYTES:
            raise SharedBackupZipError("factory o límite de miembro inválido")
        stream = opener()
        if not hasattr(stream, "read"):
            raise SharedBackupZipError("factory no devolvió un flujo binario")
        digest = hashlib.sha256()
        crc = 0
        size = 0
        try:
            while True:
                block = stream.read(DEFAULT_CHUNK_SIZE)
                if not isinstance(block, (bytes, bytearray, memoryview)):
                    raise SharedBackupZipError("factory devolvió datos no binarios")
                if not block:
                    break
                if len(block) > DEFAULT_CHUNK_SIZE:
                    raise SharedBackupZipError("factory excedió el bloque solicitado")
                size += len(block)
                if size > max_size:
                    raise SharedBackupZipError("miembro generado excede su límite")
                digest.update(block)
                crc = zlib.crc32(block, crc)
        finally:
            close = getattr(stream, "close", None)
            if callable(close):
                close()
        return cls(
            name=name,
            size=size,
            crc32=crc & UINT32_MAX,
            sha256=digest.hexdigest(),
            source=opener,
        )

    @classmethod
    def from_path(cls, name: str, path: Path, *, allowed_root: Path) -> "ZipMember":
        validate_logical_path(name)
        absolute_path = Path(path).absolute()
        absolute_root = Path(allowed_root).absolute()
        stream, identity = _open_root_regular(absolute_path, absolute_root)
        digest = hashlib.sha256()
        crc = 0
        size = 0
        try:
            while True:
                block = stream.read(DEFAULT_CHUNK_SIZE)
                if not block:
                    break
                size += len(block)
                if size > MAX_ZIP_BYTES:
                    raise SharedBackupZipError("miembro excede el límite del ZIP")
                digest.update(block)
                crc = zlib.crc32(block, crc)
            if _stat_identity(os.fstat(stream.fileno())) != identity or size != identity[6]:
                raise SharedBackupZipError("miembro cambió durante el preflight")
        finally:
            stream.close()
        return cls(
            name=name,
            size=size,
            crc32=crc & UINT32_MAX,
            sha256=digest.hexdigest(),
            source=absolute_path,
            source_identity=identity,
            allowed_root=absolute_root,
        )

    def iter_chunks(self, chunk_size: int = DEFAULT_CHUNK_SIZE) -> Iterator[bytes]:
        if type(chunk_size) is not int or not 1 <= chunk_size <= 16 * 1024 * 1024:
            raise SharedBackupZipError("tamaño de bloque inválido")
        if isinstance(self.source, bytes):
            for offset in range(0, len(self.source), chunk_size):
                yield self.source[offset : offset + chunk_size]
            return
        if callable(self.source):
            stream = self.source()
            digest = hashlib.sha256()
            crc = 0
            size = 0
            try:
                while True:
                    block = stream.read(chunk_size)
                    if not isinstance(block, (bytes, bytearray, memoryview)):
                        raise SharedBackupZipError("factory devolvió datos no binarios durante emisión")
                    if not block:
                        break
                    if len(block) > chunk_size:
                        raise SharedBackupZipError("factory excedió el bloque solicitado durante emisión")
                    size += len(block)
                    if size > self.size:
                        raise SharedBackupZipError("miembro generado creció desde el preflight")
                    digest.update(block)
                    crc = zlib.crc32(block, crc)
                    yield bytes(block)
                if size != self.size or (crc & UINT32_MAX) != self.crc32 or digest.hexdigest() != self.sha256:
                    raise SharedBackupZipError("miembro generado cambió desde el preflight")
            finally:
                close = getattr(stream, "close", None)
                if callable(close):
                    close()
            return
        if self.allowed_root is None:
            raise SharedBackupZipError("miembro de ruta sin directorio autorizado")
        stream, identity = _open_root_regular(Path(self.source), self.allowed_root, self.source_identity)
        digest = hashlib.sha256()
        crc = 0
        size = 0
        try:
            while True:
                block = stream.read(chunk_size)
                if not block:
                    break
                size += len(block)
                if size > self.size:
                    raise SharedBackupZipError("miembro creció durante la emisión ZIP")
                digest.update(block)
                crc = zlib.crc32(block, crc)
                yield block
            if (
                _stat_identity(os.fstat(stream.fileno())) != identity
                or size != self.size
                or (crc & UINT32_MAX) != self.crc32
                or digest.hexdigest() != self.sha256
            ):
                raise SharedBackupZipError("miembro cambió o su hash no coincide durante emisión ZIP")
        finally:
            stream.close()


def _write_all(destination: Any, data: bytes) -> int:
    view = memoryview(data)
    total = 0
    while view:
        written = destination.write(view)
        if not isinstance(written, int) or written <= 0:
            raise SharedBackupZipError("destino no confirmó la escritura completa del ZIP")
        if written > len(view):
            raise SharedBackupZipError("destino reportó una escritura incoherente")
        total += written
        view = view[written:]
    return total


def _validate_members(members: list[ZipMember]) -> tuple[list[tuple[ZipMember, bytes]], int]:
    if not isinstance(members, list) or len(members) < 2:
        raise SharedBackupZipError("ZIP requiere manifest.json e index.json")
    if len(members) > MAX_ENTRIES:
        raise SharedBackupZipError("ZIP excede el máximo de 10.000 entradas")
    if members[0].name != "manifest.json" or members[1].name != "index.json":
        raise SharedBackupZipError("manifest.json e index.json deben ser las dos primeras entradas raíz")
    names: set[str] = set()
    folded: set[str] = set()
    prepared: list[tuple[ZipMember, bytes]] = []
    for index, member in enumerate(members):
        if not isinstance(member, ZipMember):
            raise SharedBackupZipError("tipo de miembro ZIP inválido")
        if not isinstance(member.source, (bytes, Path)) and not callable(member.source):
            raise SharedBackupZipError("fuente de miembro ZIP inválida")
        encoded = validate_logical_path(member.name)
        if member.name in names or member.name.casefold() in folded:
            raise SharedBackupZipError("nombre duplicado o colisión normalizada en ZIP")
        names.add(member.name)
        folded.add(member.name.casefold())
        if index >= 3 and member.name <= members[index - 1].name:
            raise SharedBackupZipError("miembros de datos deben estar ordenados lexicográficamente")
        if (
            type(member.size) is not int
            or not 0 <= member.size <= MAX_ZIP_BYTES
            or type(member.crc32) is not int
            or not 0 <= member.crc32 <= UINT32_MAX
            or not isinstance(member.sha256, str)
            or len(member.sha256) != 64
            or any(char not in "0123456789abcdef" for char in member.sha256)
        ):
            raise SharedBackupZipError("metadatos de miembro ZIP inválidos")
        prepared.append((member, encoded))

    offset = 0
    central_size = 0
    for member, encoded in prepared:
        if member.size > UINT32_MAX or offset > UINT32_MAX:
            raise SharedBackupZipError("ZIP64 no está admitido en formato v1")
        offset += 30 + len(encoded) + member.size
        central_size += 46 + len(encoded)
    total_size = offset + central_size + 22
    if total_size > MAX_ZIP_BYTES or offset > UINT32_MAX or central_size > UINT32_MAX:
        raise SharedBackupZipError("ZIP completo excede 512 MiB o límites ZIP v1")
    return prepared, total_size


def _iter_zip_chunks(
    prepared: list[tuple[ZipMember, bytes]],
    expected_total: int,
    chunk_size: int,
) -> Iterator[bytes]:
    emitted_total = 0
    central_records: list[bytes] = []
    local_offset = 0

    for member, encoded_name in prepared:
        local_header = struct.pack(
            "<IHHHHHIIIHH",
            0x04034B50, 20, UTF8_FLAG, ZIP_STORED,
            0, DOS_DATE_1980_01_01, member.crc32,
            member.size, member.size, len(encoded_name), 0,
        ) + encoded_name
        emitted_total += len(local_header)
        yield local_header
        observed_size = 0
        observed_crc = 0
        observed_hash = hashlib.sha256()
        for block in member.iter_chunks(chunk_size):
            observed_size += len(block)
            if observed_size > member.size:
                raise SharedBackupZipError("miembro produjo más bytes de los declarados")
            observed_crc = zlib.crc32(block, observed_crc)
            observed_hash.update(block)
            emitted_total += len(block)
            yield block
        if (
            observed_size != member.size
            or (observed_crc & UINT32_MAX) != member.crc32
            or observed_hash.hexdigest() != member.sha256
        ):
            raise SharedBackupZipError("miembro no coincide con tamaño/CRC/SHA-256 del preflight")

        central = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            0x02014B50, (3 << 8) | 20, 20, UTF8_FLAG, ZIP_STORED,
            0, DOS_DATE_1980_01_01, member.crc32,
            member.size, member.size, len(encoded_name), 0, 0,
            0, 0, (stat.S_IFREG | 0o600) << 16, local_offset,
        ) + encoded_name
        central_records.append(central)
        local_offset += len(local_header) + member.size

    central_start = emitted_total
    for record in central_records:
        emitted_total += len(record)
        yield record
    central_length = emitted_total - central_start
    eocd = struct.pack(
        "<IHHHHIIH",
        0x06054B50, 0, 0, len(prepared), len(prepared),
        central_length, central_start, 0,
    )
    emitted_total += len(eocd)
    yield eocd
    if emitted_total != expected_total:
        raise SharedBackupZipError("tamaño ZIP emitido no coincide con el preflight")


class ZipStream:
    """Fuente read(n) para cifrar el ZIP directamente sin archivo intermedio."""

    def __init__(self, members: list[ZipMember], *, chunk_size: int = DEFAULT_CHUNK_SIZE):
        if type(chunk_size) is not int or not 1 <= chunk_size <= 16 * 1024 * 1024:
            raise SharedBackupZipError("tamaño de bloque inválido")
        prepared, total_size = _validate_members(members)
        self.size = total_size
        self._chunks = iter(_iter_zip_chunks(prepared, total_size, chunk_size))
        self._buffer = bytearray()
        self._finished = False
        self._remaining = total_size

    def read(self, length: int = -1) -> bytes:
        if type(length) is not int or length < -1:
            raise SharedBackupZipError("longitud de lectura inválida")
        if length == 0:
            return b""
        if length < 0:
            target = self._remaining
            while not self._finished:
                try:
                    chunk = next(self._chunks)
                except StopIteration:
                    self._finished = True
                    break
                self._buffer.extend(chunk)
        else:
            target = length
        while len(self._buffer) < target and not self._finished:
            try:
                chunk = next(self._chunks)
            except StopIteration:
                self._finished = True
                break
            self._buffer.extend(chunk)
        if not self._buffer:
            return b""
        take = len(self._buffer) if length < 0 else min(length, len(self._buffer))
        result = bytes(self._buffer[:take])
        del self._buffer[:take]
        self._remaining -= take
        return result


def write_zip_stream(
    members: list[ZipMember],
    destination: Any,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> int:
    """Emite ZIP_STORED reproducible sin crear archivo ZIP temporal en claro."""
    source = ZipStream(members, chunk_size=chunk_size)
    written_total = 0
    while True:
        block = source.read(chunk_size)
        if not block:
            break
        written_total += _write_all(destination, block)
    if source.read(1):
        raise SharedBackupZipError("ZIP produjo bytes posteriores a la longitud preflight")
    if written_total != source.size:
        raise SharedBackupZipError("tamaño ZIP escrito no coincide con el preflight")
    return written_total
