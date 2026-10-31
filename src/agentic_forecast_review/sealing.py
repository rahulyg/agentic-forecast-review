"""Verify the sealed held-out case seeds without decrypting them.

Held-out seeds are encrypted with ``age`` and only an aggregate manifest is
public. The verifier checks the ciphertext digest, the age header and the
manifest's internal consistency; it cannot judge the plaintext itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

EXPECTED_ARTIFACT = Path("cases/heldout/seeds.jsonl.age")
MANIFEST_PATH = Path("cases/heldout/manifest.json")
SEAL_PROCESS_REVISION = "seal-v1"
SHA256_PATTERN = re.compile(r"[a-f0-9]{64}\Z")
COMMIT_PATTERN = re.compile(r"[a-f0-9]{40}\Z")
AGE_HEADER = b"age-encryption.org/v1\n"
MANIFEST_KEYS = {
    "seal_process_revision",
    "cipher_artifact",
    "cipher_sha256",
    "total_families",
    "baseline_commit",
    "sealed_at",
}


class SealError(ValueError):
    """Raised when the public seal cannot be verified."""


def _fail(message: str) -> NoReturn:
    raise SealError(message)


def _as_object(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{name} must be a JSON object")
    return value


def _as_string(value: object, name: str) -> str:
    if not isinstance(value, str):
        _fail(f"{name} must be a string")
    return value


def _require_keys(document: dict[str, Any], keys: set[str], name: str) -> None:
    missing = keys - set(document)
    unexpected = set(document) - keys
    if missing or unexpected:
        _fail(
            f"{name} keys do not match contract; missing={sorted(missing)!r}, "
            f"unexpected={sorted(unexpected)!r}"
        )


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    try:
        value: object = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SealError(f"held-out manifest is missing: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise SealError(f"held-out manifest is not valid JSON: {exc}") from exc
    return _as_object(value, "manifest")


def _stream_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as cipher:
        while block := cipher.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _artifact_path(root: Path, manifest: dict[str, Any]) -> Path:
    cipher_artifact = _as_object(manifest["cipher_artifact"], "cipher_artifact")
    _require_keys(cipher_artifact, {"path", "format"}, "cipher_artifact")
    declared_path = _as_string(cipher_artifact["path"], "cipher_artifact.path")
    if declared_path != EXPECTED_ARTIFACT.as_posix():
        _fail(f"cipher_artifact.path must be {EXPECTED_ARTIFACT.as_posix()}")
    if cipher_artifact["format"] != "age":
        _fail("cipher_artifact.format must be age")

    candidate = root / EXPECTED_ARTIFACT
    if candidate.is_symlink():
        _fail("cipher artifact must not be a symlink")
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise SealError("cipher artifact escapes repository root") from exc
    if not candidate.is_file():
        _fail(f"cipher artifact is missing: {candidate}")
    return candidate


def _validate_timestamp(value: object) -> None:
    timestamp = _as_string(value, "sealed_at")
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise SealError("sealed_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        _fail("sealed_at must include a timezone")


def verify_manifest(manifest_path: Path, repository_root: Path) -> None:
    """Check the sealed artifact and aggregate manifest without opening plaintext."""
    manifest = _load_manifest(manifest_path)
    _require_keys(manifest, MANIFEST_KEYS, "manifest")
    if manifest["seal_process_revision"] != SEAL_PROCESS_REVISION:
        _fail(f"seal_process_revision must be {SEAL_PROCESS_REVISION!r}")

    artifact = _artifact_path(repository_root.resolve(), manifest)
    expected_digest = _as_string(manifest["cipher_sha256"], "cipher_sha256")
    if SHA256_PATTERN.fullmatch(expected_digest) is None:
        _fail("cipher_sha256 must be a lowercase SHA-256 hex digest")
    if _stream_sha256(artifact) != expected_digest:
        _fail("cipher_sha256 does not match the ciphertext")
    with artifact.open("rb") as cipher:
        if cipher.read(len(AGE_HEADER)) != AGE_HEADER:
            _fail("cipher artifact does not have a standard age header")

    families = manifest["total_families"]
    if isinstance(families, bool) or not isinstance(families, int) or families < 1:
        _fail("total_families must be an integer at least 1")
    commit = _as_string(manifest["baseline_commit"], "baseline_commit")
    if COMMIT_PATTERN.fullmatch(commit) is None:
        _fail("baseline_commit must be a full 40-character git commit hash")
    _validate_timestamp(manifest["sealed_at"])


def default_repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_repository_root())
    root = parser.parse_args(argv).root.resolve()
    try:
        verify_manifest(root / MANIFEST_PATH, root)
    except SealError as exc:
        print(f"Held-out seal verification failed: {exc}", file=sys.stderr)
        return 1
    print("Held-out seal verified without decryption.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
