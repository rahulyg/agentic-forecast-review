from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from agentic_forecast_review.sealing import (
    AGE_HEADER,
    EXPECTED_ARTIFACT,
    SealError,
    verify_manifest,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _write_seal(root: Path) -> Path:
    artifact = root / EXPECTED_ARTIFACT
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(AGE_HEADER + b"-> X25519 test-recipient\n--- test-payload")
    manifest = {
        "seal_process_revision": "seal-v1",
        "cipher_artifact": {"path": EXPECTED_ARTIFACT.as_posix(), "format": "age"},
        "cipher_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "total_families": 10,
        "baseline_commit": "0" * 40,
        "sealed_at": "2026-11-28T00:00:00Z",
    }
    manifest_path = artifact.with_name("manifest.json")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def _edit(manifest_path: Path, **changes: object) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(changes)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_verifier_accepts_valid_seal_without_decrypting(tmp_path: Path) -> None:
    verify_manifest(_write_seal(tmp_path), tmp_path)


def test_verifier_rejects_ciphertext_hash_mismatch(tmp_path: Path) -> None:
    manifest = _write_seal(tmp_path)
    artifact = tmp_path / EXPECTED_ARTIFACT
    artifact.write_bytes(artifact.read_bytes() + b"changed")
    with pytest.raises(SealError, match="does not match"):
        verify_manifest(manifest, tmp_path)


def test_verifier_rejects_non_age_artifact(tmp_path: Path) -> None:
    manifest = _write_seal(tmp_path)
    artifact = tmp_path / EXPECTED_ARTIFACT
    artifact.write_bytes(b"plaintext seeds")
    _edit(manifest, cipher_sha256=hashlib.sha256(b"plaintext seeds").hexdigest())
    with pytest.raises(SealError, match="age header"):
        verify_manifest(manifest, tmp_path)


def test_verifier_requires_full_baseline_commit(tmp_path: Path) -> None:
    manifest = _write_seal(tmp_path)
    _edit(manifest, baseline_commit="abc123")
    with pytest.raises(SealError, match="baseline_commit"):
        verify_manifest(manifest, tmp_path)


def test_verifier_rejects_unexpected_manifest_keys(tmp_path: Path) -> None:
    manifest = _write_seal(tmp_path)
    _edit(manifest, family_names=["leak"])
    with pytest.raises(SealError, match="unexpected"):
        verify_manifest(manifest, tmp_path)


def test_repository_has_no_plaintext_heldout_material() -> None:
    heldout = REPOSITORY_ROOT / "cases" / "heldout"
    if not heldout.exists():
        return
    allowed = {"seeds.jsonl.age", "manifest.json", ".gitkeep"}
    assert {path.name for path in heldout.iterdir()} <= allowed
