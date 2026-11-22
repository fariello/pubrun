import json
import logging
import os
import pytest
from pathlib import Path
from unittest.mock import patch

import pubrun.writer as writer_mod
from pubrun.writer import (
    ArtifactWriter,
    _atomic_json_write,
    _fsync_directory,
    _resolve_durability,
)


def test_atomic_json_write_success(tmp_path):
    target = tmp_path / "test.json"
    data = {"key": "value", "list": [1, 2, 3]}

    _atomic_json_write(target, data)

    assert target.exists()
    assert list(tmp_path.glob("*.tmp")) == []

    with open(target, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == data


def test_atomic_json_write_failure_cleanup(tmp_path):
    target = tmp_path / "test_fail.json"

    class Unserializable:
        pass

    data = {"key": Unserializable()}

    with pytest.raises(TypeError):
        _atomic_json_write(target, data)

    assert not target.exists()
    assert list(tmp_path.glob("*.tmp")) == []


class DummyRun:
    def __init__(self, run_dir, config):
        self.run_dir = run_dir
        self.config = config
        self._finalized = False
        self.finalize_called = 0
        self.to_manifest_called = 0

    def _finalize_state(self):
        self._finalized = True
        self.finalize_called += 1

    def to_manifest_dict(self):
        self.to_manifest_called += 1
        return {"run_id": "dummy_id"}


def test_artifact_writer_success(tmp_path):
    run_dir = tmp_path / "run_dir"
    config = {"methods": {"format": "markdown"}}
    run = DummyRun(run_dir, config)

    writer = ArtifactWriter(run)
    writer.write_artifacts()

    assert run.finalize_called == 1
    assert run.to_manifest_called == 1
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "config.resolved.json").exists()
    assert (run_dir / "methods.md").exists()


def test_artifact_writer_latex_format(tmp_path):
    run_dir = tmp_path / "run_dir"
    config = {"methods": {"format": "latex"}}
    run = DummyRun(run_dir, config)

    writer = ArtifactWriter(run)
    writer.write_artifacts()

    assert (run_dir / "methods.tex").exists()


def test_durability_policies_fsync_atomic_strict(tmp_path, monkeypatch):
    """Verify fsync, atomic, and strict modes invoke the expected fsync operations."""
    file_fsyncs = []
    dir_fsyncs = []
    real_fsync = os.fsync

    def spy_fsync(fd):
        file_fsyncs.append(fd)
        return real_fsync(fd)

    def spy_dir_fsync(dir_path):
        dir_fsyncs.append(Path(dir_path))

    monkeypatch.setattr(os, "fsync", spy_fsync)
    monkeypatch.setattr(writer_mod, "_fsync_directory", spy_dir_fsync)

    # atomic: no file fsync, no dir fsync, still valid JSON with zero .tmp leftovers
    p_atomic = tmp_path / "atomic.json"
    _atomic_json_write(p_atomic, {"mode": "atomic"}, durability="atomic")
    assert json.loads(p_atomic.read_text(encoding="utf-8")) == {"mode": "atomic"}
    assert len(file_fsyncs) == 0
    assert len(dir_fsyncs) == 0
    assert list(tmp_path.glob("*.tmp")) == []

    # fsync: 1 file fsync, 0 dir fsync
    p_fsync = tmp_path / "fsync.json"
    _atomic_json_write(p_fsync, {"mode": "fsync"}, durability="fsync")
    assert len(file_fsyncs) == 1
    assert len(dir_fsyncs) == 0

    # strict: +1 file fsync, +1 dir fsync
    p_strict = tmp_path / "strict.json"
    _atomic_json_write(p_strict, {"mode": "strict"}, durability="strict")
    assert len(file_fsyncs) == 2
    assert dir_fsyncs == [tmp_path]


def test_fsync_directory_posix_o_cloexec_and_oserror_fallback(tmp_path, monkeypatch):
    """_fsync_directory uses O_CLOEXEC on POSIX and tolerates OSError safely."""
    if os.name != "posix" or not hasattr(os, "O_DIRECTORY"):
        pytest.skip("POSIX O_DIRECTORY not supported on this platform")

    open_flags = []
    real_open = os.open

    def spy_open(path, flags, *args, **kwargs):
        open_flags.append(flags)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", spy_open)
    _fsync_directory(tmp_path)
    assert len(open_flags) == 1
    assert open_flags[0] & os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        assert open_flags[0] & os.O_CLOEXEC

    # OSError during os.fsync must be swallowed safely without raising
    monkeypatch.setattr(os, "fsync", lambda fd: (_ for _ in ()).throw(OSError("EINVAL")))
    _fsync_directory(tmp_path)


def test_finalize_durability_upgrades_unchanged_config_in_place(tmp_path, monkeypatch):
    """finalize mode skips fsync at startup, fsyncs unchanged config in place at finalize."""
    run_dir = tmp_path / "finalize_run"
    config = {"core": {"artifact_durability": "finalize"}, "methods": {"format": "markdown"}}
    run = DummyRun(run_dir, config)
    writer = ArtifactWriter(run)

    atomic_calls = []
    fsync_existing_calls = []
    real_atomic = writer_mod._atomic_json_write
    real_fsync_existing = writer_mod._fsync_existing_file

    def spy_atomic(path, data, **kwargs):
        atomic_calls.append((Path(path).name, kwargs.get("durability")))
        return real_atomic(path, data, **kwargs)

    def spy_fsync_existing(path, *, durability):
        fsync_existing_calls.append((Path(path).name, durability))
        return real_fsync_existing(path, durability=durability)

    monkeypatch.setattr(writer_mod, "_atomic_json_write", spy_atomic)
    monkeypatch.setattr(writer_mod, "_fsync_existing_file", spy_fsync_existing)

    assert writer.write_startup_manifest() is True
    assert atomic_calls == [("manifest.json", "atomic"), ("config.resolved.json", "atomic")]
    assert fsync_existing_calls == []

    # Refresh write skips unchanged config completely
    assert writer.write_startup_manifest(is_refresh=True) is True
    assert atomic_calls == [
        ("manifest.json", "atomic"),
        ("config.resolved.json", "atomic"),
        ("manifest.json", "atomic"),
    ]
    assert fsync_existing_calls == []

    # Finalize upgrades unchanged config in place via _fsync_existing_file (no 2nd atomic write)
    assert writer.write_artifacts() is True
    assert atomic_calls == [
        ("manifest.json", "atomic"),
        ("config.resolved.json", "atomic"),
        ("manifest.json", "atomic"),
        ("manifest.json", "fsync"),
    ]
    assert fsync_existing_calls == [("config.resolved.json", "fsync")]


def test_finalize_in_place_fsync_oserror_falls_back_to_atomic_rewrite(tmp_path, monkeypatch):
    """If in-place r+b fsync raises OSError, writer falls back to atomic rewrite."""
    run_dir = tmp_path / "fallback_run"
    config = {"core": {"artifact_durability": "finalize"}, "methods": {"format": "markdown"}}
    run = DummyRun(run_dir, config)
    writer = ArtifactWriter(run)

    assert writer.write_startup_manifest() is True

    atomic_config_calls = []
    real_atomic = writer_mod._atomic_json_write

    def spy_atomic(path, data, **kwargs):
        if Path(path).name == "config.resolved.json":
            atomic_config_calls.append(kwargs.get("durability"))
        return real_atomic(path, data, **kwargs)

    monkeypatch.setattr(writer_mod, "_atomic_json_write", spy_atomic)
    monkeypatch.setattr(
        writer_mod,
        "_fsync_existing_file",
        lambda path, *, durability: (_ for _ in ()).throw(OSError("unsupported r+b")),
    )

    assert writer.write_artifacts() is True
    assert atomic_config_calls == ["fsync"]


def test_invalid_durability_warns_once_and_falls_back_to_fsync(caplog):
    """Invalid core.artifact_durability logs one warning per distinct value and uses fsync."""
    writer_mod._warned_invalid_durability.discard("bogus_mode_test")
    writer_mod._warned_invalid_durability.discard("12345")

    with caplog.at_level(logging.WARNING, logger="pubrun"):
        assert _resolve_durability({"core": {"artifact_durability": "bogus_mode_test"}}, stage="startup") == "fsync"
        assert _resolve_durability({"core": {"artifact_durability": "bogus_mode_test"}}, stage="finalize") == "fsync"
        assert _resolve_durability({"core": {"artifact_durability": 12345}}, stage="startup") == "fsync"
        assert _resolve_durability({"core": {"artifact_durability": 12345}}, stage="finalize") == "fsync"

    bogus_warnings = [r for r in caplog.records if "bogus_mode_test" in r.message]
    int_warnings = [r for r in caplog.records if "12345" in r.message]
    assert len(bogus_warnings) == 1
    assert len(int_warnings) == 1


def test_unchanged_config_skipped_including_reordered_keys_and_recreated_if_missing(tmp_path, monkeypatch):
    """Canonical sorted JSON digest skips rewrites across reordered dicts, but recreates missing file."""
    run_dir = tmp_path / "canonical_run"
    run = DummyRun(run_dir, {"b": 2, "a": {"y": 20, "x": 10}})
    writer = ArtifactWriter(run)

    config_writes = []
    real_atomic = writer_mod._atomic_json_write

    def spy_atomic(path, data, **kwargs):
        if Path(path).name == "config.resolved.json":
            config_writes.append(Path(path))
        return real_atomic(path, data, **kwargs)

    monkeypatch.setattr(writer_mod, "_atomic_json_write", spy_atomic)

    assert writer.write_startup_manifest() is True
    assert len(config_writes) == 1

    # Rebuild config dict with reversed key insertion order -> identical canonical SHA-256 digest
    run.config = {"a": {"x": 10, "y": 20}, "b": 2}
    assert writer.sync_config_if_changed() is False
    assert len(config_writes) == 1

    # Remove config.resolved.json externally -> must be recreated on next sync/finalize
    (run_dir / "config.resolved.json").unlink()
    assert writer.write_artifacts() is True
    assert len(config_writes) == 2
    assert (run_dir / "config.resolved.json").exists()


def test_write_artifacts_idempotency_skips_rewrites_after_finalization(tmp_path, monkeypatch):
    """Calling write_artifacts() twice writes manifest and config only once."""
    run_dir = tmp_path / "idempotent_run"
    run = DummyRun(run_dir, {"methods": {"format": "markdown"}})
    writer = ArtifactWriter(run)

    writes = []
    real_atomic = writer_mod._atomic_json_write

    def spy_atomic(path, data, **kwargs):
        writes.append(Path(path).name)
        return real_atomic(path, data, **kwargs)

    monkeypatch.setattr(writer_mod, "_atomic_json_write", spy_atomic)

    assert writer.write_artifacts() is True
    assert writes == ["config.resolved.json", "manifest.json"]

    assert writer.write_artifacts() is True
    assert writes == ["config.resolved.json", "manifest.json"]
    assert run.to_manifest_called == 1
