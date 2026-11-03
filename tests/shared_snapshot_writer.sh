#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONDONTWRITEBYTECODE=1 python3 -B - "$ROOT" <<'PY'
import copy
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "scripts"))
import shared_snapshot_writer as writer

def blocked(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except writer.SnapshotBlocked:
        return
    raise AssertionError("se esperaba SnapshotBlocked")

def rejected(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except Exception:
        return
    raise AssertionError("se esperaba rechazo de validación")

# Timeout debe ser finito, no negativo y numérico (bool no es aceptable).
for invalid_timeout in (-1, float("nan"), float("inf"), True, "30"):
    blocked(
        writer.create_snapshot,
        Path("/tmp/xrm-writer-test-output"),
        "Synthetic-Only-Password-123!",
        lock_timeout=invalid_timeout,
    )

# SW-01: selective necesita categorías explícitas en API y CLI.
blocked(
    writer.create_snapshot,
    Path("/tmp/xrm-writer-test-output"),
    "Synthetic-Only-Password-123!",
    selection_mode="all_available",
    requested_categories=["connections.vless"],
)
blocked(
    writer.create_snapshot,
    Path("/tmp/xrm-writer-test-output"),
    "Synthetic-Only-Password-123!",
    selection_mode="selective",
    requested_categories=None,
)
with mock.patch.object(writer.getpass, "getpass", side_effect=AssertionError("no debe pedir contraseña")):
    with mock.patch.object(sys, "argv", ["shared_snapshot_writer.py", "--destination", "/tmp/xrm-writer-test-output", "--selection-mode", "selective"]):
        try:
            writer.main()
        except SystemExit as exc:
            assert exc.code == 2
        else:
            raise AssertionError("CLI aceptó selective sin --category")

# La CLI all_available delega la selección por defecto a la API (None),
# mientras selective pasa únicamente las categorías explícitas.
with mock.patch.object(writer, "create_snapshot", return_value={"status": "CREATED_COMPLETE"}) as create_call:
    with mock.patch.object(sys, "argv", ["shared_snapshot_writer.py", "--destination", "/tmp/xrm-cli-default.xrm"]):
        assert writer.main() == 0
    assert create_call.call_args.kwargs["selection_mode"] == "all_available"
    assert create_call.call_args.kwargs["requested_categories"] is None

# SW-02: la contraseña se solicita antes de crear staging; el staging
# queda protegido por owner.lock y se limpia si falla la adquisición posterior.
with tempfile.TemporaryDirectory(prefix="xrm-writer-test-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    destination = parent / "snapshot.xrm"
    calls = []
    def prompt(_):
        assert not list(parent.glob(".xrm-snapshot-*")), "staging apareció antes de confirmar la contraseña"
        calls.append(True)
        return "Synthetic-Only-Password-123!"
    with mock.patch.object(writer.getpass, "getpass", side_effect=prompt):
        with mock.patch.object(writer, "acquire_snapshot_locks", side_effect=writer.SnapshotBlocked("synthetic lock failure")):
            blocked(writer.create_snapshot, destination, None)
    assert len(calls) == 2
    assert not destination.exists()
    assert not list(parent.glob(".xrm-snapshot-*"))

# El lock de coordinación rechaza objetos inseguros sin modificar sus metadatos.
with tempfile.TemporaryDirectory(prefix="xrm-coordination-hardlink-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    unrelated = parent / "unrelated.data"
    unrelated.write_bytes(b"preserve-inode-metadata")
    os.chmod(unrelated, 0o640)
    lock_path = parent / ".xrm-coordination.lock"
    os.link(unrelated, lock_path)
    before = unrelated.stat()
    blocked(writer._acquire_coordination_lock, parent, 0.1)
    after = unrelated.stat()
    assert before.st_ino == after.st_ino and before.st_nlink == after.st_nlink == 2
    assert (before.st_mode & 0o777) == (after.st_mode & 0o777) == 0o640
    assert unrelated.read_bytes() == b"preserve-inode-metadata"

with tempfile.TemporaryDirectory(prefix="xrm-coordination-symlink-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    target = parent / "target"
    target.write_bytes(b"do-not-touch")
    os.chmod(target, 0o640)
    (parent / ".xrm-coordination.lock").symlink_to(target)
    before = target.stat()
    blocked(writer._acquire_coordination_lock, parent, 0.1)
    after = target.stat()
    assert (before.st_mode & 0o777) == (after.st_mode & 0o777) == 0o640
    assert target.read_bytes() == b"do-not-touch"

with tempfile.TemporaryDirectory(prefix="xrm-coordination-special-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    os.mkfifo(parent / ".xrm-coordination.lock", 0o600)
    blocked(writer._acquire_coordination_lock, parent, 0.1)

with tempfile.TemporaryDirectory(prefix="xrm-coordination-mode-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    lock_path = parent / ".xrm-coordination.lock"
    lock_path.write_bytes(b"")
    os.chmod(lock_path, 0o640)
    before = lock_path.stat()
    blocked(writer._acquire_coordination_lock, parent, 0.1)
    after = lock_path.stat()
    assert (before.st_mode & 0o777) == (after.st_mode & 0o777) == 0o640

# La contención del propio lock de coordinación respeta el timeout y libera el FD.
with tempfile.TemporaryDirectory(prefix="xrm-coordination-timeout-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    first_fd = writer._acquire_coordination_lock(parent, 1.0)
    try:
        import time
        started = time.monotonic()
        blocked(writer._acquire_coordination_lock, parent, 0.05)
        elapsed = time.monotonic() - started
        assert 0.04 <= elapsed < 0.5, elapsed
    finally:
        os.close(first_fd)
    second_fd = writer._acquire_coordination_lock(parent, 0.1)
    os.close(second_fd)

# Recuperación: elimina un temporal abandonado sólo cuando su owner.lock está libre.
with tempfile.TemporaryDirectory(prefix="xrm-orphan-test-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    orphan = parent / ".xrm-snapshot-orphan"
    orphan.mkdir(mode=0o700)
    (orphan / "owner.lock").touch(mode=0o600)
    os.chmod(orphan / "owner.lock", 0o600)
    (orphan / "package.tmp").write_bytes(b"synthetic-incomplete-ciphertext")
    os.chmod(orphan / "package.tmp", 0o600)
    coordination_fd = writer._acquire_coordination_lock(parent, 1.0)
    try:
        assert writer._recover_orphan_staging(parent) == 1
    finally:
        os.close(coordination_fd)
    assert not orphan.exists()

# Un temporal activo se conserva; al liberar owner.lock pasa a ser recuperable.
with tempfile.TemporaryDirectory(prefix="xrm-active-stage-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    active = parent / ".xrm-snapshot-active"
    active.mkdir(mode=0o700)
    owner_path = active / "owner.lock"
    owner_fd = os.open(owner_path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    writer.fcntl.flock(owner_fd, writer.fcntl.LOCK_EX | writer.fcntl.LOCK_NB)
    coordination_fd = writer._acquire_coordination_lock(parent, 1.0)
    try:
        assert writer._recover_orphan_staging(parent) == 0
        assert active.exists()
    finally:
        os.close(coordination_fd)
    os.close(owner_fd)
    coordination_fd = writer._acquire_coordination_lock(parent, 1.0)
    try:
        assert writer._recover_orphan_staging(parent) == 1
    finally:
        os.close(coordination_fd)
    assert not active.exists()

# Estructura inesperada sin owner.lock se conserva y bloquea fail-closed.
with tempfile.TemporaryDirectory(prefix="xrm-unknown-stage-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    unknown = parent / ".xrm-snapshot-unknown"
    unknown.mkdir(mode=0o700)
    (unknown / "unexpected").write_text("synthetic")
    os.chmod(unknown / "unexpected", 0o600)
    coordination_fd = writer._acquire_coordination_lock(parent, 1.0)
    try:
        blocked(writer._recover_orphan_staging, parent)
        assert unknown.exists()
    finally:
        os.close(coordination_fd)


# A-16: un hardlink sin marcador no se interpreta como publicación válida.
with tempfile.TemporaryDirectory(prefix="xrm-orphan-arbitrary-hardlink-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    stage = parent / ".xrm-snapshot-arbitrary"
    stage.mkdir(mode=0o700)
    (stage / "owner.lock").touch(mode=0o600)
    os.chmod(stage / "owner.lock", 0o600)
    package = stage / "package.tmp"
    package.write_bytes(b"synthetic-not-a-published-package")
    os.chmod(package, 0o600)
    unrelated = parent / "unrelated.bin"
    os.link(package, unrelated)
    coordination_fd = writer._acquire_coordination_lock(parent, 1.0)
    try:
        blocked(writer._recover_orphan_staging, parent)
        assert stage.exists() and package.exists() and unrelated.exists()
        assert package.stat().st_nlink == 2
    finally:
        os.close(coordination_fd)

# A-16: el marcador sólo autoriza el nombre final exacto y el inode registrado.
with tempfile.TemporaryDirectory(prefix="xrm-orphan-marker-mismatch-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    stage = parent / ".xrm-snapshot-mismatch"
    stage.mkdir(mode=0o700)
    (stage / "owner.lock").touch(mode=0o600)
    os.chmod(stage / "owner.lock", 0o600)
    package = stage / "package.tmp"
    package.write_bytes(b"synthetic-marker-bound-artifact")
    os.chmod(package, 0o600)
    expected = parent / "expected.xrm"
    writer._write_publication_marker(package, expected)
    wrong = parent / "different-name.xrm"
    os.link(package, wrong)
    coordination_fd = writer._acquire_coordination_lock(parent, 1.0)
    try:
        blocked(writer._recover_orphan_staging, parent)
        assert stage.exists() and package.exists() and wrong.exists()
        assert not expected.exists() and package.stat().st_nlink == 2
    finally:
        os.close(coordination_fd)

# A-16: un tercer hardlink nunca se admite, incluso con marcador válido.
with tempfile.TemporaryDirectory(prefix="xrm-orphan-third-hardlink-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    stage = parent / ".xrm-snapshot-third-link"
    stage.mkdir(mode=0o700)
    (stage / "owner.lock").touch(mode=0o600)
    os.chmod(stage / "owner.lock", 0o600)
    package = stage / "package.tmp"
    package.write_bytes(b"synthetic-three-link-artifact")
    os.chmod(package, 0o600)
    final_path = parent / "published.xrm"
    writer._write_publication_marker(package, final_path)
    os.link(package, final_path)
    extra_link = parent / "extra-hardlink.bin"
    os.link(package, extra_link)
    coordination_fd = writer._acquire_coordination_lock(parent, 1.0)
    try:
        blocked(writer._recover_orphan_staging, parent)
        assert stage.exists() and package.exists() and final_path.exists() and extra_link.exists()
        assert package.stat().st_nlink == 3
    finally:
        os.close(coordination_fd)

# SW-03: un padre ausente no debe crearse para alojar un lock.
with tempfile.TemporaryDirectory(prefix="xrm-lock-test-") as raw:
    parent = Path(raw)
    missing = parent / "must-not-be-created"
    blocked(writer._open_lock_file, missing / "catalog.lock")
    assert not missing.exists()

# SW-03: los padres de lock inseguros (group/world writable sin sticky) se rechazan.
with tempfile.TemporaryDirectory(prefix="xrm-lock-mode-") as raw:
    parent = Path(raw)
    unsafe = parent / "unsafe"
    unsafe.mkdir(mode=0o700)
    os.chmod(unsafe, 0o777)
    blocked(writer._open_lock_file, unsafe / "catalog.lock")
    assert not (unsafe / "catalog.lock").exists()

# Lock en directorio privado root-owned: apertura y permisos del archivo.
with tempfile.TemporaryDirectory(prefix="xrm-lock-good-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    fd = writer._open_lock_file(parent / "catalog.lock")
    try:
        st = os.fstat(fd)
        assert st.st_uid == 0 and st.st_gid == 0
        assert (st.st_mode & 0o777) == 0o600
        assert st.st_nlink == 1
    finally:
        os.close(fd)


# Locks: orden de adquisición y liberación inversa.
with tempfile.TemporaryDirectory(prefix="xrm-lock-order-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    paths = writer.SnapshotPaths(
        lifecycle_lock=parent / "01.lock",
        integrity_lock=parent / "02.lock",
        catalog_lock=parent / "03.lock",
    )
    real_flock = writer.fcntl.flock
    events = []
    def record_flock(fd, operation):
        events.append((fd, operation))
        return real_flock(fd, operation)
    with mock.patch.object(writer.fcntl, "flock", side_effect=record_flock):
        with writer.acquire_snapshot_locks(paths, timeout=1):
            acquired_fds = [fd for fd, op in events if op & writer.fcntl.LOCK_EX]
            assert len(acquired_fds) == 3
    released_fds = [fd for fd, op in events if op == writer.fcntl.LOCK_UN]
    assert released_fds == list(reversed(acquired_fds))

# Timeout fail-closed si el primer lock está ocupado.
with tempfile.TemporaryDirectory(prefix="xrm-lock-timeout-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    paths = writer.SnapshotPaths(
        lifecycle_lock=parent / "01.lock",
        integrity_lock=parent / "02.lock",
        catalog_lock=parent / "03.lock",
    )
    def enter_locked_context():
        with writer.acquire_snapshot_locks(paths, timeout=0):
            raise AssertionError("lock ocupado no debe permitir entrar")
    with mock.patch.object(writer.fcntl, "flock", side_effect=BlockingIOError):
        blocked(enter_locked_context)

# Contención real entre descriptores/procesos del mismo kernel: el segundo
# lock ocupado vence el timeout y libera el primero ya adquirido.
with tempfile.TemporaryDirectory(prefix="xrm-lock-real-contention-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    paths = writer.SnapshotPaths(
        lifecycle_lock=parent / "01.lock", integrity_lock=parent / "02.lock",
        catalog_lock=parent / "03.lock",
    )
    held_fd = writer._open_lock_file(paths.integrity_lock)
    writer.fcntl.flock(held_fd, writer.fcntl.LOCK_EX | writer.fcntl.LOCK_NB)
    try:
        def acquire_timeout():
            with writer.acquire_snapshot_locks(paths, timeout=0.05):
                raise AssertionError("debió vencer el timeout del segundo lock")
        blocked(acquire_timeout)
    finally:
        writer.fcntl.flock(held_fd, writer.fcntl.LOCK_UN)
        os.close(held_fd)
    probe_fd = writer._open_lock_file(paths.lifecycle_lock)
    try:
        writer.fcntl.flock(probe_fd, writer.fcntl.LOCK_EX | writer.fcntl.LOCK_NB)
        writer.fcntl.flock(probe_fd, writer.fcntl.LOCK_UN)
    finally:
        os.close(probe_fd)

# Las asociaciones eliminan el valor de credencial, pero conservan tipo y
# metadatos; los protocolos VMess usan el protocol_id completo del catálogo.
identity_id = "123e4567-e89b-12d3-a456-426614174000"
association_id = "123e4567-e89b-12d3-a456-426614174001"
catalog = {
    "schema_version": 2,
    "identities": [{"id": identity_id, "created_at": "2026-11-03T00:00:00Z"}],
    "associations": [{
        "id": association_id, "identity_id": identity_id, "connection_id": "vmess-1",
        "protocol": "vmess_ws", "credential": {"type": "uuid", "value": "SYNTHETIC-VMESS-UUID"},
        "alias": "test", "created_at": "2026-11-03T00:00:00Z",
    }],
}
clean_catalog, identity_exclusions = writer._validate_identity_catalog(
    catalog, {"vmess-1": {"id": "vmess-1", "protocol_id": "vmess_ws"}}
)
serialized = writer.canonical_json(clean_catalog)
assert b"SYNTHETIC-VMESS-UUID" not in serialized
assert clean_catalog["associations"][0]["credential_type"] == "uuid"
assert identity_exclusions[0][1] == "vmess_uuid"

broken_catalog = {
    "schema_version": 2, "identities": [],
    "associations": catalog["associations"],
}
blocked(writer._validate_identity_catalog, broken_catalog, {"vmess-1": {"id": "vmess-1", "protocol_id": "vmess_ws"}})

# WireGuard no se exporta en snapshot v1: el peer completo queda fuera y se
# declara como exclusión PARTIAL. Campos de claves/PSK desconocidos bloquean.
wg_assoc = {
    "id": "123e4567-e89b-12d3-a456-426614174002",
    "identity_id": identity_id, "connection_id": "wg-1", "protocol": "wireguard",
    "credential": {"type": "public_key", "value": "SYNTHETIC-WG-PUBLIC-KEY"},
    "alias": "WG synthetic peer", "created_at": "2026-11-03T00:00:00Z",
}
wg_clean, wg_exclusions = writer._validate_identity_catalog(
    {"schema_version": 2, "identities": catalog["identities"], "associations": [wg_assoc]},
    {"wg-1": {"id": "wg-1", "protocol_id": "wireguard"}},
)
assert wg_clean["associations"] == []
assert wg_exclusions == [(wg_assoc["id"], "wireguard_peer_keys", "unsupported_protocol", "wg-1", identity_id)]
for sensitive_field in ("private_key", "preshared_key", "psk", "peer_private_key"):
    unsafe_wg = {**wg_assoc, sensitive_field: "SYNTHETIC-DO-NOT-EXPORT"}
    blocked(
        writer._validate_identity_catalog,
        {"schema_version": 2, "identities": catalog["identities"], "associations": [unsafe_wg]},
        {"wg-1": {"id": "wg-1", "protocol_id": "wireguard"}},
    )
unsafe_identity = {"schema_version": 2, "identities": [{**catalog["identities"][0], "notes": "unknown"}], "associations": []}
blocked(writer._validate_identity_catalog, unsafe_identity, {})

# VMess conserva email/level protegidos y excluye UUID; VLESS REALITY elimina
# referencias de secreto y declara la exclusión correspondiente.
vmess_clean, vmess_exclusions, _ = writer._sanitize_protocol_config(
    "vmess",
    {"security": "none", "security_options": {}, "users": [
        {"id": "SYNTHETIC-VMESS-UUID", "email": "assoc:synthetic", "level": 7}
    ]},
    {"id": "vmess-1"}, None,
)
assert vmess_clean["users"] == [{"email": "assoc:synthetic", "level": 7}]
assert vmess_exclusions == [("vmess_uuid", "excluded_by_default")]

vless_clean, vless_exclusions, _ = writer._sanitize_protocol_config(
    "vless",
    {"security": "reality", "security_options": {"secret_ref": "SYNTHETIC-SECRET-REF"}},
    {"id": "vless-1"}, "SYNTHETIC-SECRET-REF",
)
assert "secret_ref" not in vless_clean["security_options"]
assert vless_exclusions == [("vless_reality_private_key", "excluded_by_default")]

# Ancestros del destino: rechazar escritura grupal/mundial sin sticky; /tmp
# sticky y el directorio privado final root-only sí son admisibles.
with tempfile.TemporaryDirectory(prefix="xrm-destination-parent-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    writer._validate_destination_parent(parent)
    unsafe = parent / "unsafe-ancestor"
    unsafe.mkdir(mode=0o700)
    os.chmod(unsafe, 0o777)
    final = unsafe / "private-output"
    final.mkdir(mode=0o700)
    blocked(writer._validate_destination_parent, final)
    symlink = parent / "symlink-ancestor"
    symlink.symlink_to(parent, target_is_directory=True)
    blocked(writer._validate_destination_parent, symlink / "output")

# Referencias/revisiones VLESS y VMess: sólo se acepta la revisión vigente.
valid_vless = {
    "id": "vless-revision", "configuration_ref": "configurations/vless-revision.r000007.json",
    "configuration_revision": 7, "configuration_schema_version": 1, "secret_ref": None,
}
assert writer._validate_vless_reference(valid_vless) == ("configurations/vless-revision.r000007.json", 7)
for invalid in (
    {**valid_vless, "configuration_revision": 6},
    {**valid_vless, "configuration_ref": "../vless-revision.r000007.json"},
    {**valid_vless, "configuration_schema_version": 2},
):
    blocked(writer._validate_vless_reference, invalid)
valid_vmess = {
    "id": "vmess-revision", "vmess_configuration_ref": "configurations/vmess-revision.r000003.json",
    "vmess_configuration_revision": 3, "vmess_configuration_schema_version": 1,
}
assert writer.vmess_config_store.validate_catalog_metadata(
    valid_vmess, valid_vmess["vmess_configuration_ref"]
) == 3
for invalid in (
    {**valid_vmess, "vmess_configuration_revision": 2},
    {**valid_vmess, "vmess_configuration_schema_version": 2},
):
    rejected(writer.vmess_config_store.validate_catalog_metadata, invalid, invalid["vmess_configuration_ref"])

# El destino preexistente nunca se reemplaza y los fallos antes de publicar
# limpian exclusivamente el staging creado por esta operación.
with tempfile.TemporaryDirectory(prefix="xrm-destination-existing-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    destination = parent / "already-there.xrm"
    destination.write_bytes(b"DO-NOT-REPLACE")
    blocked(writer.create_snapshot, destination, "Synthetic-Only-Password-123!")
    assert destination.read_bytes() == b"DO-NOT-REPLACE"
    assert not list(parent.glob(".xrm-snapshot-*"))
with tempfile.TemporaryDirectory(prefix="xrm-stage-failure-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    destination = parent / "never-published.xrm"
    with mock.patch.object(writer, "acquire_snapshot_locks", side_effect=writer.SnapshotBlocked("synthetic lock failure")):
        blocked(writer.create_snapshot, destination, "Synthetic-Only-Password-123!")
    assert not destination.exists()
    assert not list(parent.glob(".xrm-snapshot-*"))

# Una política de passphrase incumplida es BLOCKED, no un fallo operativo.
with tempfile.TemporaryDirectory(prefix="xrm-passphrase-class-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    try:
        writer.create_snapshot(parent / "bad.xrm", "weak")
    except writer.SnapshotBlocked:
        pass
    else:
        raise AssertionError("passphrase inválida no se clasificó como BLOCKED")
    assert not (parent / "bad.xrm").exists()
    assert not list(parent.glob(".xrm-snapshot-*"))

# Los metadatos de exclusión trazan asociación, identidad y conexión sin valor
# de credencial; las dependencias agregan conexiones para un mismo certificado.
identity_exclusion = {}
writer._add_exclusion(
    identity_exclusion, "identity-association:" + association_id,
    "vmess_uuid", "excluded_by_default", token=association_id,
    association_id=association_id, identity_id=identity_id, connection_id="vmess-1",
)
record = next(iter(identity_exclusion.values()))
assert record["association_id"] == association_id
assert record["identity_id"] == identity_id
assert record["connection_id"] == "vmess-1"
deps = {}
writer._add_dependency(deps, "tls:cert-demo", "tls_reference", "certificate:cert-demo", "a" * 64, "pending_restore_preflight", dependent_connection="vless-a")
writer._add_dependency(deps, "tls:cert-demo", "tls_reference", "certificate:cert-demo", "a" * 64, "pending_restore_preflight", dependent_connection="vless-b")
external = writer._external_dependencies_member(deps, {
    "cert-demo": {"storage_type": "reference", "fingerprint_sha256": "a" * 64, "certificate_source": "/etc/ssl/synthetic.pem"}
})
external_data = writer.strict_json_loads(external.source)
assert external.name == "external-dependencies.json"
assert external_data["dependencies"][0]["dependent_connections"] == ["vless-a", "vless-b"]
assert external_data["dependencies"][0]["expected_path"] == "/etc/ssl/synthetic.pem"

# Un catálogo de identidades ausente no se interpreta silenciosamente como
# vacío: el contrato del almacén no autoriza esa sustitución.
with tempfile.TemporaryDirectory(prefix="xrm-identities-absent-") as raw:
    base = Path(raw)
    os.chmod(base, 0o700)
    connections = base / "connections"
    connections.mkdir(mode=0o700)
    catalog_path = connections / "connections.json"
    catalog_path.write_text("[]", encoding="utf-8")
    os.chown(catalog_path, 0, 0)
    os.chmod(catalog_path, 0o600)
    paths = writer.SnapshotPaths(
        connections_root=connections, users_root=base / "users",
        vmess_root=base / "vmess", certificates_root=base / "certificates",
        lifecycle_lock=base / "lifecycle.lock", integrity_lock=base / "integrity.lock",
        catalog_lock=base / "catalog.lock",
    )
    blocked(writer._build_snapshot_members, paths, ["identities"], "selective")

# Una categoría no soportada solicitada se representa explícitamente y fuerza
# PARTIAL; no se convierte en un snapshot COMPLETE vacío.
with tempfile.TemporaryDirectory(prefix="xrm-unsupported-category-") as raw:
    base = Path(raw)
    os.chmod(base, 0o700)
    paths = writer.SnapshotPaths(
        connections_root=base / "connections", users_root=base / "users",
        vmess_root=base / "vmess", certificates_root=base / "certificates",
        lifecycle_lock=base / "lifecycle.lock", integrity_lock=base / "integrity.lock",
        catalog_lock=base / "catalog.lock",
    )
    _, unsupported_manifest = writer._build_snapshot_members(paths, ["profiles"], "selective")
    assert unsupported_manifest["categories"]["unsupported"] == ["profiles"]
    assert unsupported_manifest["completeness"]["status"] == "PARTIAL"

# E2E íntegro y exclusivamente sintético: crea, autentica y abre el ZIP; verifica
# metadatos source_snapshot y la presencia del índice de dependencias externo.
import io
import json
import zipfile
with tempfile.TemporaryDirectory(prefix="xrm-snapshot-e2e-") as raw:
    base = Path(raw)
    os.chmod(base, 0o700)
    dirs = {name: base / name for name in ("connections", "users", "vmess", "certificates", "locks", "output")}
    for directory in dirs.values():
        directory.mkdir(mode=0o700)
    (dirs["connections"] / "connections.json").write_text("[]", encoding="utf-8")
    (dirs["users"] / "users.json").write_text(
        json.dumps({"schema_version": 2, "identities": [], "associations": []}), encoding="utf-8"
    )
    for source in (dirs["connections"] / "connections.json", dirs["users"] / "users.json"):
        os.chown(source, 0, 0)
        os.chmod(source, 0o600)
    paths = writer.SnapshotPaths(
        connections_root=dirs["connections"], users_root=dirs["users"],
        vmess_root=dirs["vmess"], certificates_root=dirs["certificates"],
        lifecycle_lock=dirs["locks"] / "lifecycle.lock",
        integrity_lock=dirs["locks"] / "integrity.lock",
        catalog_lock=dirs["locks"] / "catalog.lock",
    )
    destination = dirs["output"] / "synthetic.xrm"
    result = writer.create_snapshot(destination, "Synthetic-Only-Password-123!", paths=paths)
    assert result["status"] == "CREATED_COMPLETE"
    with destination.open("rb") as stream:
        writer.crypto.verify_package_stream(stream, "Synthetic-Only-Password-123!")
    plaintext = writer.crypto.decrypt_payload(destination.read_bytes(), "Synthetic-Only-Password-123!")
    with zipfile.ZipFile(io.BytesIO(plaintext)) as archive:
        assert archive.testzip() is None
        assert "external-dependencies.json" in archive.namelist()
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["completeness"]["status"] == "COMPLETE"
        source = {item["catalog_id"]: item for item in manifest["source_snapshot"]["catalogs"]}
        assert source["connections.shared"]["present"] is True
        assert source["connections.shared"]["schema_version"] is None
        assert source["certificates.tls"]["present"] is False
        assert source["identities"]["schema_version"] == 2
        assert source["identities"]["revision"] is None
        assert archive.read("manifest.json") == writer.canonical_json(manifest)
        writer._validate_manifest_contract(manifest)
        invalid_manifests = []
        invalid = copy.deepcopy(manifest)
        invalid["backup_id"] = "not-a-uuid"
        invalid_manifests.append(invalid)
        invalid = copy.deepcopy(manifest)
        invalid["created_at"] = "2026-11-03T12:00:00-05:00"
        invalid_manifests.append(invalid)
        invalid = copy.deepcopy(manifest)
        invalid["created_at"] = "2026-02-30T12:00:00Z"
        invalid_manifests.append(invalid)
        invalid = copy.deepcopy(manifest)
        invalid["request"]["requested_categories"].append(invalid["request"]["requested_categories"][0])
        invalid_manifests.append(invalid)
        invalid = copy.deepcopy(manifest)
        invalid["manifest_version"] = True
        invalid_manifests.append(invalid)
        invalid = copy.deepcopy(manifest)
        invalid["manifest_version"] = 2
        invalid_manifests.append(invalid)
        invalid = copy.deepcopy(manifest)
        invalid["categories"]["included"].append("profiles")
        invalid_manifests.append(invalid)
        invalid = copy.deepcopy(manifest)
        invalid["categories"]["unsupported"].append("profiles")
        invalid_manifests.append(invalid)
        invalid = copy.deepcopy(manifest)
        invalid["categories"]["included"] = []
        invalid["categories"]["unsupported"] = []
        invalid_manifests.append(invalid)
        invalid = copy.deepcopy(manifest)
        invalid["request"]["requested_categories"] = ["profiles"]
        invalid["categories"] = {"included": ["profiles"], "unsupported": []}
        invalid_manifests.append(invalid)
        invalid = copy.deepcopy(manifest)
        invalid["categories"]["included"].append(invalid["categories"]["included"][0])
        invalid_manifests.append(invalid)
        invalid = copy.deepcopy(manifest)
        invalid["resources"][0].pop("resource_type")
        invalid_manifests.append(invalid)
        invalid = copy.deepcopy(manifest)
        invalid["members"][0].pop("sha256")
        invalid_manifests.append(invalid)
        invalid = copy.deepcopy(manifest)
        invalid["exclusions"].append({"exclusion_id": "incomplete"})
        invalid_manifests.append(invalid)
        invalid = copy.deepcopy(manifest)
        invalid["dependencies"].append({"dependency_id": "incomplete"})
        invalid_manifests.append(invalid)
        invalid = copy.deepcopy(manifest)
        invalid["source_snapshot"]["catalogs"][0].pop("sha256")
        invalid_manifests.append(invalid)
        for invalid_manifest in invalid_manifests:
            blocked(writer._validate_manifest_contract, invalid_manifest)
        external_doc = json.loads(archive.read("external-dependencies.json"))
        assert external_doc == {"schema_version": 1, "dependencies": []}

    # Fallos antes del punto de commit: no dejan paquete final ni staging.
    verify_failure = dirs["output"] / "verify-failure.xrm"
    with mock.patch.object(writer.crypto, "verify_package_stream", side_effect=writer.crypto.SharedBackupFormatError("synthetic verification failure")):
        blocked(writer.create_snapshot, verify_failure, "Synthetic-Only-Password-123!", paths=paths)
    assert not verify_failure.exists()
    assert not list(dirs["output"].glob(".xrm-snapshot-*"))

    fsync_failure = dirs["output"] / "fsync-failure.xrm"
    with mock.patch.object(writer.os, "fsync", side_effect=OSError("synthetic fsync failure")):
        try:
            writer.create_snapshot(fsync_failure, "Synthetic-Only-Password-123!", paths=paths)
        except writer.SnapshotError:
            pass
        else:
            raise AssertionError("fallo fsync no se clasificó como FAILED")
    assert not fsync_failure.exists()
    assert not list(dirs["output"].glob(".xrm-snapshot-*"))

    interrupted = dirs["output"] / "interrupted.xrm"
    with mock.patch.object(writer.crypto, "encrypt_payload_stream", side_effect=KeyboardInterrupt):
        try:
            writer.create_snapshot(interrupted, "Synthetic-Only-Password-123!", paths=paths)
        except KeyboardInterrupt:
            pass
        else:
            raise AssertionError("interrupción sintética no se propagó")
    assert not interrupted.exists()
    assert not list(dirs["output"].glob(".xrm-snapshot-*"))

    collision = dirs["output"] / "publication-race.xrm"
    def competing_publisher(source, target, **kwargs):
        Path(target).write_bytes(b"COMPETING-PUBLISHER")
        raise FileExistsError(str(target))
    with mock.patch.object(writer.os, "link", side_effect=competing_publisher):
        blocked(writer.create_snapshot, collision, "Synthetic-Only-Password-123!", paths=paths)
    assert collision.read_bytes() == b"COMPETING-PUBLISHER"
    assert not list(dirs["output"].glob(".xrm-snapshot-*"))

    # Fallo de fsync del directorio después del enlace exclusivo: el punto de
    # commit ya ocurrió; se informa FAILED y se conserva el paquete publicado.
    post_commit = dirs["output"] / "post-commit-fsync.xrm"
    real_fsync = writer.os.fsync
    fsync_calls = []
    def fail_directory_fsync(fd):
        fsync_calls.append(fd)
        if len(fsync_calls) == 4:
            raise OSError("synthetic parent fsync failure")
        return real_fsync(fd)
    with mock.patch.object(writer.os, "fsync", side_effect=fail_directory_fsync):
        try:
            writer.create_snapshot(post_commit, "Synthetic-Only-Password-123!", paths=paths)
        except writer.SnapshotError as exc:
            assert "fue publicado" in str(exc)
        else:
            raise AssertionError("fallo fsync post-commit no se informó como FAILED")
    assert post_commit.exists()
    with post_commit.open("rb") as stream:
        writer.crypto.verify_package_stream(stream, "Synthetic-Only-Password-123!")
    assert not list(dirs["output"].glob(".xrm-snapshot-*"))

    # Cualquier fallo de cleanup debe cambiar el resultado a FAILED. Si el
    # paquete ya se publicó, se conserva y se informa expresamente.
    import fcntl

    def assert_cleanup_failed(destination, patcher, expect_residue):
        try:
            with patcher:
                writer.create_snapshot(destination, "Synthetic-Only-Password-123!", paths=paths)
        except writer.SnapshotError as exc:
            assert "fue publicado" in str(exc) and "limpieza del staging" in str(exc), str(exc)
        else:
            raise AssertionError("cleanup fallido devolvió éxito CREATED_*")
        assert destination.exists()
        with destination.open("rb") as stream:
            writer.crypto.verify_package_stream(stream, "Synthetic-Only-Password-123!")
        leftovers = list(dirs["output"].glob(".xrm-snapshot-*"))
        assert len(leftovers) == (1 if expect_residue else 0), leftovers
        if leftovers:
            coordination_fd = writer._acquire_coordination_lock(dirs["output"], 1.0)
            try:
                assert writer._recover_orphan_staging(dirs["output"]) == 1
            finally:
                os.close(coordination_fd)
            assert not list(dirs["output"].glob(".xrm-snapshot-*"))
            assert destination.stat().st_nlink == 1
            with destination.open("rb") as stream:
                writer.crypto.verify_package_stream(stream, "Synthetic-Only-Password-123!")

    # 1) No se pudo adquirir el lock de coordinación para limpiar.
    real_coord_lock = writer._acquire_coordination_lock
    coord_calls = []
    def fail_cleanup_coordination(parent, timeout):
        coord_calls.append(parent)
        if len(coord_calls) == 2:
            raise OSError("synthetic cleanup coordination failure")
        return real_coord_lock(parent, timeout)
    assert_cleanup_failed(
        dirs["output"] / "cleanup-coordination.xrm",
        mock.patch.object(writer, "_acquire_coordination_lock", side_effect=fail_cleanup_coordination),
        True,
    )

    # 2) unlink de package.tmp falla: owner_fd debe cerrarse aunque quede staging.
    real_unlink = Path.unlink
    def fail_package_unlink(path, *args, **kwargs):
        if path.name == "package.tmp":
            raise OSError("synthetic cleanup unlink failure")
        return real_unlink(path, *args, **kwargs)
    assert_cleanup_failed(
        dirs["output"] / "cleanup-unlink.xrm",
        mock.patch.object(Path, "unlink", fail_package_unlink),
        True,
    )

    # 3) rmdir falla después de retirar package.tmp y owner.lock.
    real_rmdir = Path.rmdir
    def fail_staging_rmdir(path, *args, **kwargs):
        if path.name.startswith(".xrm-snapshot-"):
            raise OSError("synthetic cleanup rmdir failure")
        return real_rmdir(path, *args, **kwargs)
    assert_cleanup_failed(
        dirs["output"] / "cleanup-rmdir.xrm",
        mock.patch.object(Path, "rmdir", fail_staging_rmdir),
        True,
    )

    # 4) fsync final del directorio falla después de retirar staging.
    real_fsync = writer.os.fsync
    cleanup_fsync_calls = []
    def fail_cleanup_fsync(fd):
        cleanup_fsync_calls.append(fd)
        if len(cleanup_fsync_calls) == 5:
            raise OSError("synthetic cleanup directory fsync failure")
        return real_fsync(fd)
    assert_cleanup_failed(
        dirs["output"] / "cleanup-fsync.xrm",
        mock.patch.object(writer.os, "fsync", side_effect=fail_cleanup_fsync),
        False,
    )

    # Terminaciones abruptas en cuatro puntos: prompt sin staging, cifrado,
    # antes del enlace final y después del enlace pero antes del fsync del padre.
    crash_program = r'''import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[3])
import shared_snapshot_writer as writer
base = Path(sys.argv[1])
phase = sys.argv[2]
paths = writer.SnapshotPaths(
    connections_root=base/"connections", users_root=base/"users",
    vmess_root=base/"vmess", certificates_root=base/"certificates",
    lifecycle_lock=base/"locks/lifecycle.lock", integrity_lock=base/"locks/integrity.lock",
    catalog_lock=base/"locks/catalog.lock")
destination = base/"output"/(phase + ".xrm")
if phase == "prompt-crash":
    writer.getpass.getpass = lambda prompt: os._exit(81)
elif phase == "encrypt-crash":
    original_encrypt = writer.crypto.encrypt_payload_stream
    def stop_during_encryption(source, output, length, password, **kwargs):
        class CrashSink:
            def write(self, data):
                written = output.write(data)
                output.flush()
                os._exit(82)
        return original_encrypt(source, CrashSink(), length, password, **kwargs)
    writer.crypto.encrypt_payload_stream = stop_during_encryption
elif phase == "publish-crash":
    writer.os.link = lambda *args, **kwargs: os._exit(83)
elif phase == "post-link-crash":
    original_link = writer.os.link
    def link_then_crash(source, target, **kwargs):
        original_link(source, target, **kwargs)
        os._exit(84)
    writer.os.link = link_then_crash
writer.create_snapshot(destination, None if phase == "prompt-crash" else "Synthetic-Only-Password-123!", paths=paths)
'''
    import subprocess
    child = subprocess.run(
        [sys.executable, "-c", crash_program, str(base), "prompt-crash", str(root / "scripts")],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert child.returncode == 81, ("prompt-crash", child.returncode, child.stderr)
    assert not (dirs["output"] / "prompt-crash.xrm").exists()
    assert not list(dirs["output"].glob(".xrm-snapshot-*"))

    for phase, expected_code in (
        ("encrypt-crash", 82), ("publish-crash", 83), ("post-link-crash", 84)
    ):
        child = subprocess.run(
            [sys.executable, "-c", crash_program, str(base), phase, str(root / "scripts")],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        assert child.returncode == expected_code, (phase, child.returncode, child.stderr)
        final_path = dirs["output"] / f"{phase}.xrm"
        if phase == "post-link-crash":
            assert final_path.exists()
            with final_path.open("rb") as stream:
                writer.crypto.verify_package_stream(stream, "Synthetic-Only-Password-123!")
        else:
            assert not final_path.exists()
        leftovers = list(dirs["output"].glob(".xrm-snapshot-*"))
        assert len(leftovers) == 1
        stage_stat = leftovers[0].lstat()
        assert stage_stat.st_uid == 0 and stage_stat.st_gid == 0 and (stage_stat.st_mode & 0o777) == 0o700
        partial = leftovers[0] / "package.tmp"
        partial_stat = partial.lstat()
        assert partial_stat.st_uid == 0 and partial_stat.st_gid == 0
        assert (partial_stat.st_mode & 0o777) == 0o600
        assert partial.read_bytes().startswith(writer.crypto.MAGIC)
        if phase == "post-link-crash":
            assert partial_stat.st_nlink == 2  # hard-link publicado + staging pendiente
            marker = json.loads((leftovers[0] / "publication.json").read_text(encoding="utf-8"))
            assert marker["destination_name"] == final_path.name
            assert marker["inode"] == partial_stat.st_ino
        else:
            assert partial_stat.st_nlink == 1
        coordination_fd = writer._acquire_coordination_lock(dirs["output"], 1.0)
        try:
            assert writer._recover_orphan_staging(dirs["output"]) == 1
        finally:
            os.close(coordination_fd)
        assert not leftovers[0].exists()
        if phase == "post-link-crash":
            assert final_path.exists() and final_path.stat().st_nlink == 1
            with final_path.open("rb") as stream:
                writer.crypto.verify_package_stream(stream, "Synthetic-Only-Password-123!")
        else:
            assert not final_path.exists()


# A-16: si la recuperación se interrumpe después de retirar package.tmp,
# el siguiente intento reconoce el marcador y finaliza sin tocar el paquete.
with tempfile.TemporaryDirectory(prefix="xrm-recovery-interrupted-") as raw:
    parent = Path(raw)
    os.chmod(parent, 0o700)
    stage = parent / ".xrm-snapshot-recovery-interrupted"
    stage.mkdir(mode=0o700)
    (stage / "owner.lock").touch(mode=0o600)
    os.chmod(stage / "owner.lock", 0o600)
    package = stage / "package.tmp"
    package.write_bytes(b"synthetic-recovery-interruption")
    os.chmod(package, 0o600)
    final_path = parent / "durable-final.xrm"
    writer._write_publication_marker(package, final_path)
    os.link(package, final_path)
    recovery_program = r'''import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
import shared_snapshot_writer as writer
parent = Path(sys.argv[1])
original_unlink = Path.unlink
def unlink_then_crash(path, *args, **kwargs):
    result = original_unlink(path, *args, **kwargs)
    if path.name == "package.tmp":
        os._exit(86)
    return result
Path.unlink = unlink_then_crash
coordination_fd = writer._acquire_coordination_lock(parent, 1.0)
writer._recover_orphan_staging(parent)
'''
    child = subprocess.run(
        [sys.executable, "-c", recovery_program, str(parent), str(root / "scripts")],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert child.returncode == 86, (child.returncode, child.stderr)
    assert final_path.exists() and final_path.stat().st_nlink == 1
    assert stage.exists() and not (stage / "package.tmp").exists()
    assert (stage / "publication.json").exists()
    coordination_fd = writer._acquire_coordination_lock(parent, 1.0)
    try:
        assert writer._recover_orphan_staging(parent) == 1
    finally:
        os.close(coordination_fd)
    assert final_path.exists() and final_path.stat().st_nlink == 1
    assert not stage.exists()
    assert final_path.read_bytes() == b"synthetic-recovery-interruption"

# E2E de adaptadores VLESS/VMess e identidades con datos sintéticos. Comprueba
# que los UUID no salen en ningún miembro y que email/level VMess se conservan.
with tempfile.TemporaryDirectory(prefix="xrm-protocol-adapters-e2e-") as raw:
    base = Path(raw)
    os.chmod(base, 0o700)
    dirs = {name: base / name for name in ("connections", "users", "vmess", "certificates", "locks", "output")}
    for directory in dirs.values():
        directory.mkdir(mode=0o700)
    (dirs["connections"] / "configurations").mkdir(mode=0o700)
    (dirs["vmess"] / "configurations").mkdir(mode=0o700)
    vless_id = "vless-demo"
    vmess_id = "vmess-demo"
    vless_uuid = "11111111-1111-4111-8111-111111111111"
    vmess_uuid = "22222222-2222-4222-8222-222222222222"
    identity_id = "123e4567-e89b-12d3-a456-426614174010"
    vless_assoc = "123e4567-e89b-12d3-a456-426614174011"
    vmess_assoc = "123e4567-e89b-12d3-a456-426614174012"
    connection_catalog = [
        {"id": vless_id, "name": "VLESS synthetic", "port": 12001, "max_users": 10,
         "state": "draft", "runtime_applied": False, "protocol_id": "vless_ws",
         "configuration_ref": f"configurations/{vless_id}.r000001.json",
         "configuration_revision": 1, "configuration_schema_version": 1, "secret_ref": None},
        {"id": vmess_id, "name": "VMess synthetic", "port": 12002, "max_users": 10,
         "state": "draft", "runtime_applied": False, "protocol_id": "vmess_ws",
         "vmess_configuration_ref": f"configurations/{vmess_id}.r000001.json",
         "vmess_configuration_revision": 1, "vmess_configuration_schema_version": 1, "vmess_secret_ref": None},
    ]
    vless_config = {
        "schema_version": 1, "connection_id": vless_id, "protocol": "vless", "mode_id": "vless_ws",
        "transport": "websocket", "security": "none", "listen_address": "127.0.0.1",
        "listen_port": 12001, "transport_options": {"path": "/vless"}, "security_options": {},
    }
    vmess_config = {
        "schema_version": 1, "connection_id": vmess_id, "protocol": "vmess", "mode_id": "vmess_ws",
        "transport": "websocket", "security": "none", "listen_address": "127.0.0.1",
        "listen_port": 12002, "transport_options": {"path": "/vmess", "host": "synthetic.local"},
        "security_options": {}, "users": [{"id": vmess_uuid, "email": "synthetic-user@example.invalid", "level": 7}],
    }
    identity_catalog = {
        "schema_version": 2,
        "identities": [{"id": identity_id, "created_at": "2026-11-03T00:00:00Z"}],
        "associations": [
            {"id": vless_assoc, "identity_id": identity_id, "connection_id": vless_id,
             "protocol": "vless", "credential": {"type": "uuid", "value": vless_uuid},
             "alias": "VLESS synthetic", "created_at": "2026-11-03T00:00:00Z"},
            {"id": vmess_assoc, "identity_id": identity_id, "connection_id": vmess_id,
             "protocol": "vmess_ws", "credential": {"type": "uuid", "value": vmess_uuid},
             "alias": "VMess synthetic", "created_at": "2026-11-03T00:00:00Z"},
        ],
    }
    files = {
        dirs["connections"] / "connections.json": json.dumps(connection_catalog),
        dirs["connections"] / "configurations" / f"{vless_id}.r000001.json": json.dumps(vless_config),
        dirs["vmess"] / "configurations" / f"{vmess_id}.r000001.json": json.dumps(vmess_config),
        dirs["users"] / "users.json": json.dumps(identity_catalog),
    }
    for path, content in files.items():
        path.write_text(content, encoding="utf-8")
        os.chown(path, 0, 0)
        os.chmod(path, 0o600)
    paths = writer.SnapshotPaths(
        connections_root=dirs["connections"], users_root=dirs["users"],
        vmess_root=dirs["vmess"], certificates_root=dirs["certificates"],
        lifecycle_lock=dirs["locks"] / "lifecycle.lock",
        integrity_lock=dirs["locks"] / "integrity.lock",
        catalog_lock=dirs["locks"] / "catalog.lock",
    )
    destination = dirs["output"] / "protocols.xrm"
    result = writer.create_snapshot(destination, "Synthetic-Only-Password-123!", paths=paths)
    assert result["status"] == "CREATED_PARTIAL"
    plaintext = writer.crypto.decrypt_payload(destination.read_bytes(), "Synthetic-Only-Password-123!")
    with zipfile.ZipFile(io.BytesIO(plaintext)) as archive:
        all_members = {name: archive.read(name) for name in archive.namelist()}
        combined = b"".join(all_members.values())
        assert vless_uuid.encode() not in combined
        assert vmess_uuid.encode() not in combined
        vmess_member = next(data for name, data in all_members.items() if name.startswith("connections/vmess/"))
        assert b"synthetic-user@example.invalid" in vmess_member
        assert b'"level":7' in vmess_member
        clean_identities = json.loads(all_members["users/identities.json"])
        assert all("credential" not in association for association in clean_identities["associations"])
        assert all(association["credential_type"] == "uuid" for association in clean_identities["associations"])
        manifest = json.loads(all_members["manifest.json"])
        exclusion_by_assoc = {item.get("association_id"): item for item in manifest["exclusions"] if "association_id" in item}
        assert set(exclusion_by_assoc) == {vless_assoc, vmess_assoc}
        assert exclusion_by_assoc[vless_assoc]["connection_id"] == vless_id
        assert exclusion_by_assoc[vmess_assoc]["connection_id"] == vmess_id
        assert manifest["completeness"]["status"] == "PARTIAL"
        assert b"synthetic-user@example.invalid" not in all_members["manifest.json"]
        assert vless_uuid.encode() not in all_members["manifest.json"]

    # Cambio TOCTOU después del preflight del factory y antes de emitir ZIP:
    # el hash/tamaño del miembro deben bloquear sin publicar.
    config_path = dirs["connections"] / "configurations" / f"{vless_id}.r000001.json"
    original_zip_stream = writer.package_zip.ZipStream
    def mutate_after_preflight(members):
        changed = {**vless_config, "transport_options": {"path": "/xxxxx"}}
        config_path.write_text(json.dumps(changed), encoding="utf-8")
        os.chown(config_path, 0, 0)
        os.chmod(config_path, 0o600)
        return original_zip_stream(members)
    toctou_destination = dirs["output"] / "toctou.xrm"
    with mock.patch.object(writer.package_zip, "ZipStream", side_effect=mutate_after_preflight):
        blocked(writer.create_snapshot, toctou_destination, "Synthetic-Only-Password-123!", paths=paths)
    assert not toctou_destination.exists()
    assert not list(dirs["output"].glob(".xrm-snapshot-*"))

# E2E TLS reference sintético: dependency queda en manifiesto y el path
# esperado sólo aparece dentro de external-dependencies.json cifrado.
with tempfile.TemporaryDirectory(prefix="xrm-tls-reference-e2e-") as raw:
    base = Path(raw)
    os.chmod(base, 0o700)
    dirs = {name: base / name for name in ("connections", "users", "vmess", "certificates", "locks", "output")}
    for directory in dirs.values():
        directory.mkdir(mode=0o700)
    (dirs["connections"] / "configurations").mkdir(mode=0o700)
    cert_id = "cert-synthetic"
    external_path = "/etc/ssl/synthetic-reference.pem"
    certificate_record = {
        "certificate_id": cert_id, "storage_type": "reference", "certificate_source": external_path,
        "secret_ref": f"secrets/{cert_id}.r000001.bin", "fingerprint_sha256": "a" * 64,
        "public_key_fingerprint_sha256": "b" * 64, "subject": "CN=synthetic.invalid",
        "issuer": "CN=synthetic-ca.invalid", "sans": ["synthetic.invalid"],
        "not_before": "2026-01-01T00:00:00+00:00", "not_after": "2027-01-01T00:00:00+00:00",
        "status": "active", "revision": 1,
        "created_at": "2026-11-03T00:00:00Z", "updated_at": "2026-11-03T00:00:00Z",
    }
    tls_connection = {
        "id": "vless-tls", "name": "TLS reference synthetic", "port": 12003,
        "max_users": 5, "state": "draft", "runtime_applied": False,
        "protocol_id": "vless_tcp_tls", "configuration_ref": "configurations/vless-tls.r000001.json",
        "configuration_revision": 1, "configuration_schema_version": 1, "secret_ref": None,
    }
    tls_config = {
        "schema_version": 1, "connection_id": "vless-tls", "protocol": "vless",
        "mode_id": "vless_tcp_tls", "transport": "raw", "security": "tls",
        "listen_address": "127.0.0.1", "listen_port": 12003,
        "transport_options": {}, "security_options": {"certificate_id": cert_id},
    }
    tls_files = {
        dirs["connections"] / "connections.json": json.dumps([tls_connection]),
        dirs["connections"] / "configurations" / "vless-tls.r000001.json": json.dumps(tls_config),
        dirs["users"] / "users.json": json.dumps({"schema_version": 2, "identities": [], "associations": []}),
        dirs["certificates"] / "catalog.json": json.dumps({"schema_version": 1, "revision": 4, "certificates": [certificate_record]}),
    }
    for path, content in tls_files.items():
        path.write_text(content, encoding="utf-8")
        os.chown(path, 0, 0)
        os.chmod(path, 0o600)
    paths = writer.SnapshotPaths(
        connections_root=dirs["connections"], users_root=dirs["users"],
        vmess_root=dirs["vmess"], certificates_root=dirs["certificates"],
        lifecycle_lock=dirs["locks"] / "lifecycle.lock",
        integrity_lock=dirs["locks"] / "integrity.lock",
        catalog_lock=dirs["locks"] / "catalog.lock",
    )
    destination = dirs["output"] / "tls-reference.xrm"
    result = writer.create_snapshot(destination, "Synthetic-Only-Password-123!", paths=paths)
    assert result["status"] == "CREATED_PARTIAL"
    plaintext = writer.crypto.decrypt_payload(destination.read_bytes(), "Synthetic-Only-Password-123!")
    with zipfile.ZipFile(io.BytesIO(plaintext)) as archive:
        manifest_bytes = archive.read("manifest.json")
        manifest = json.loads(manifest_bytes)
        assert external_path.encode() not in manifest_bytes
        dependency = next(item for item in manifest["dependencies"] if item["dependency_id"] == f"tls:{cert_id}")
        assert dependency["dependency_type"] == "tls_reference"
        assert dependency["fingerprint_sha256"] == "a" * 64
        assert dependency["dependent_connections"] == ["vless-tls"]
        external_doc = json.loads(archive.read("external-dependencies.json"))
        assert external_doc["dependencies"] == [{
            "certificate_id": cert_id, "fingerprint_sha256": "a" * 64,
            "expected_path": external_path, "dependent_connections": ["vless-tls"],
            "validation_required": "regular_file_no_symlink_no_hardlink_fingerprint_and_key_pair",
        }]

# E2E certificado managed sintético: incluye sólo PEM público, conserva metadata
# de catálogo y declara excluida la clave privada sin crear/leer master.key.
with tempfile.TemporaryDirectory(prefix="xrm-tls-managed-e2e-") as raw:
    from datetime import datetime, timedelta, timezone
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    base = Path(raw)
    os.chmod(base, 0o700)
    dirs = {name: base / name for name in ("connections", "users", "vmess", "certificates", "locks", "output")}
    for directory in dirs.values():
        directory.mkdir(mode=0o700)
    managed_dir = dirs["certificates"] / "managed"
    managed_dir.mkdir(mode=0o700)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "managed.synthetic.invalid")])
    now = datetime.now(timezone.utc)
    public_certificate = (
        x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
        .public_key(private_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=30))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("managed.synthetic.invalid")]), critical=False)
        .sign(private_key, hashes.SHA256())
    )
    certificate_bytes = public_certificate.public_bytes(serialization.Encoding.PEM)
    cert_id = "cert-managed"
    cert_path = managed_dir / f"{cert_id}.pem"
    cert_path.write_bytes(certificate_bytes)
    os.chown(cert_path, 0, 0)
    os.chmod(cert_path, 0o600)
    metadata = writer._certificate_public_metadata(certificate_bytes)
    certificate_record = {
        "certificate_id": cert_id, "storage_type": "managed",
        "certificate_source": f"managed/{cert_id}.pem",
        "secret_ref": f"secrets/{cert_id}.r000001.bin", **metadata,
        "status": "active", "revision": 1,
        "created_at": "2026-11-03T00:00:00Z", "updated_at": "2026-11-03T00:00:00Z",
    }
    connection = {
        "id": "vless-managed", "name": "TLS managed synthetic", "port": 12004,
        "max_users": 5, "state": "draft", "runtime_applied": False,
        "protocol_id": "vless_tcp_tls", "configuration_ref": "configurations/vless-managed.r000001.json",
        "configuration_revision": 1, "configuration_schema_version": 1, "secret_ref": None,
    }
    config = {
        "schema_version": 1, "connection_id": "vless-managed", "protocol": "vless",
        "mode_id": "vless_tcp_tls", "transport": "raw", "security": "tls",
        "listen_address": "127.0.0.1", "listen_port": 12004,
        "transport_options": {}, "security_options": {"certificate_id": cert_id},
    }
    managed_files = {
        dirs["connections"] / "connections.json": json.dumps([connection]),
        dirs["connections"] / "configurations" / "vless-managed.r000001.json": json.dumps(config),
        dirs["users"] / "users.json": json.dumps({"schema_version": 2, "identities": [], "associations": []}),
        dirs["certificates"] / "catalog.json": json.dumps({"schema_version": 1, "revision": 1, "certificates": [certificate_record]}),
    }
    (dirs["connections"] / "configurations").mkdir(mode=0o700)
    for path, content in managed_files.items():
        path.write_text(content, encoding="utf-8")
        os.chown(path, 0, 0)
        os.chmod(path, 0o600)
    paths = writer.SnapshotPaths(
        connections_root=dirs["connections"], users_root=dirs["users"],
        vmess_root=dirs["vmess"], certificates_root=dirs["certificates"],
        lifecycle_lock=dirs["locks"] / "lifecycle.lock",
        integrity_lock=dirs["locks"] / "integrity.lock",
        catalog_lock=dirs["locks"] / "catalog.lock",
    )
    destination = dirs["output"] / "tls-managed.xrm"
    result = writer.create_snapshot(destination, "Synthetic-Only-Password-123!", paths=paths)
    assert result["status"] == "CREATED_PARTIAL"
    plaintext = writer.crypto.decrypt_payload(destination.read_bytes(), "Synthetic-Only-Password-123!")
    with zipfile.ZipFile(io.BytesIO(plaintext)) as archive:
        assert archive.read(f"certificates/managed/{cert_id}.pem") == certificate_bytes
        cert_snapshot = json.loads(archive.read("certificates/catalog.json"))
        cert_doc = cert_snapshot["certificates"][0]
        assert "secret_ref" not in cert_doc
        assert cert_doc["certificate_id"] == cert_id
        manifest = json.loads(archive.read("manifest.json"))
        cert_resource = next(item for item in manifest["resources"] if item["resource_id"] == f"certificate:{cert_id}")
        assert cert_resource["completeness"] == "PARTIAL"
        assert any(item["secret_class"] == "tls_private_key" for item in manifest["exclusions"])
        assert json.loads(archive.read("external-dependencies.json"))["dependencies"] == []

# Los límites de entradas y tamaño se fuerzan a través de create_snapshot,
# no sólo mediante pruebas unitarias del generador ZIP.
with tempfile.TemporaryDirectory(prefix="xrm-writer-limits-") as raw:
    base = Path(raw)
    os.chmod(base, 0o700)
    locks = base / "locks"
    output = base / "output"
    locks.mkdir(mode=0o700)
    output.mkdir(mode=0o700)
    paths = writer.SnapshotPaths(
        connections_root=base / "connections", users_root=base / "users",
        vmess_root=base / "vmess", certificates_root=base / "certificates",
        lifecycle_lock=locks / "lifecycle.lock", integrity_lock=locks / "integrity.lock",
        catalog_lock=locks / "catalog.lock",
    )
    structural = [
        writer.package_zip.ZipMember.from_bytes("manifest.json", b"{}"),
        writer.package_zip.ZipMember.from_bytes("index.json", b"{}"),
    ]
    too_many = structural + [
        writer.package_zip.ZipMember.from_bytes(f"payload/{index:05d}.bin", b"x")
        for index in range(writer.package_zip.MAX_ENTRIES - 1)
    ]
    with mock.patch.object(writer, "_build_snapshot_members", return_value=(too_many, {"completeness": {"status": "COMPLETE"}})):
        blocked(writer.create_snapshot, output / "too-many.xrm", "Synthetic-Only-Password-123!", paths=paths)
    assert not (output / "too-many.xrm").exists()
    oversize = writer.package_zip.ZipMember(
        "payload/oversize.bin", writer.package_zip.MAX_ZIP_BYTES, 0, "0" * 64, b""
    )
    with mock.patch.object(writer, "_build_snapshot_members", return_value=(structural + [oversize], {"completeness": {"status": "COMPLETE"}})):
        blocked(writer.create_snapshot, output / "oversize.xrm", "Synthetic-Only-Password-123!", paths=paths)
    assert not (output / "oversize.xrm").exists()
    assert not list(output.glob(".xrm-snapshot-*"))

# Medición de memoria del camino ZIP->AES-GCM: el miembro de 16 MiB se lee
# desde archivo en bloques; el sink descarta ciphertext para medir memoria extra.
with tempfile.TemporaryDirectory(prefix="xrm-stream-memory-") as raw:
    import tracemalloc
    base = Path(raw)
    os.chmod(base, 0o700)
    source_path = base / "large.synthetic"
    with source_path.open("wb") as stream:
        for _ in range(16):
            stream.write(b"X" * (1024 * 1024))
    os.chown(source_path, 0, 0)
    os.chmod(source_path, 0o600)
    large_member = writer.package_zip.ZipMember.from_path(
        "payload/large.synthetic", source_path, allowed_root=base
    )
    class NullWriter:
        def write(self, data):
            return len(data)
    tracemalloc.start()
    zip_stream = writer.package_zip.ZipStream([
        writer.package_zip.ZipMember.from_bytes("manifest.json", b"{}"),
        writer.package_zip.ZipMember.from_bytes("index.json", b"{}"),
        large_member,
    ])
    writer.crypto.encrypt_payload_stream(
        zip_stream, NullWriter(), zip_stream.size,
        "Synthetic-Only-Password-123!", chunk_size=64 * 1024,
    )
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak_memory < 8 * 1024 * 1024, f"streaming consumió demasiada memoria Python: {peak_memory}"

# RSS máximo en proceso aislado (incluye el perfil scrypt nativo); el límite
# evita que el writer materialice el miembro ZIP completo en RAM.
import subprocess
rss_program = r'''import os, resource, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import shared_snapshot_writer as writer
with tempfile.TemporaryDirectory(prefix="xrm-rss-") as raw:
    root = Path(raw); os.chmod(root, 0o700)
    source = root / "large.bin"
    with source.open("wb") as stream:
        for _ in range(16): stream.write(b"R" * (1024 * 1024))
    os.chown(source, 0, 0); os.chmod(source, 0o600)
    member = writer.package_zip.ZipMember.from_path("payload/large.bin", source, allowed_root=root)
    class Sink:
        def write(self, data): return len(data)
    zip_source = writer.package_zip.ZipStream([
        writer.package_zip.ZipMember.from_bytes("manifest.json", b"{}"),
        writer.package_zip.ZipMember.from_bytes("index.json", b"{}"), member,
    ])
    writer.crypto.encrypt_payload_stream(zip_source, Sink(), zip_source.size,
        "Synthetic-Only-Password-123!", chunk_size=64 * 1024)
    print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
'''
rss_result = subprocess.run(
    [sys.executable, "-c", rss_program, str(root / "scripts")],
    check=True, capture_output=True, text=True,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
)
rss_peak_kib = int(rss_result.stdout.strip())
assert rss_peak_kib < 128 * 1024, f"RSS pico excedió 128 MiB: {rss_peak_kib} KiB"
print(f"STREAM_RSS_PEAK_KIB={rss_peak_kib}")

print("PASS: writer — destino endurecido, clasificación BLOCKED, trazabilidad, dependencias TLS y snapshot sintético E2E.")
PY
