"""In-process seam tests for pubrun.report.diagnostics (out stream injection and DiagnosticsError)."""
import io
import json
from pathlib import Path

import pytest

from pubrun.report.diagnostics import (
    DiagnosticsError,
    print_report,
    print_resources_report,
)


def _create_run_fixture(tmp_path: Path, run_id: str = "seam1234") -> Path:
    run_dir = tmp_path / f"pubrun-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1.0",
        "manifest_type": "pubrun-manifest",
        "run": {"run_id": run_id},
        "status": {"outcome": "completed"},
        "invocation": {
            "argv": ["train.py", "--epochs", "2"],
            "script": {"basename": "train.py"},
        },
        "timing": {
            "started_at_utc": 1000.0,
            "ended_at_utc": 1060.0,
            "elapsed_seconds": 60.0,
        },
        "signals": {"exit_code": 0},
        "python": {"version": "3.12.0", "executable": "/usr/bin/python3"},
        "host": {"hostname": "node01", "os_name": "Linux", "os_version": "6.8"},
        "hardware": {"cpu": {"model": "Test CPU"}, "memory_total_bytes": 16 * 1024**3},
        "environment": {
            "variables": [
                {"name": "PUBRUN_TEST_VAR", "value": {"representation": "plain", "value": "ok"}},
            ]
        },
        "packages": {"records": [{"name": "numpy", "version": "1.26.0"}]},
        "resources": {
            "peak_rss_bytes": 2 * 1024**3,
            "peak_cpu_percent": 75.0,
            "end_rss_bytes": 1024**3,
        },
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    events = [
        {
            "type": "resource_sample",
            "timestamp_utc": 1000.0,
            "payload": {"rss_bytes": 1024**3, "cpu_percent": 20.0},
        },
        {
            "type": "resource_sample",
            "timestamp_utc": 1030.0,
            "payload": {"rss_bytes": int(1.5 * 1024**3), "cpu_percent": 75.0},
        },
        {
            "type": "resource_sample",
            "timestamp_utc": 1060.0,
            "payload": {"rss_bytes": 2 * 1024**3, "cpu_percent": 40.0},
        },
    ]
    with open(run_dir / "events.jsonl", "w", encoding="utf-8") as ef:
        for ev in events:
            ef.write(json.dumps(ev) + "\n")

    (run_dir / "stdout.log").write_text("epoch 1\n", encoding="utf-8")
    return manifest_path


class TestOutStream:
    """Verify report functions write solely to the injected out stream and honor its encoding."""

    @pytest.mark.parametrize("depth", ["basic", "standard", "deep"])
    def test_print_report_writes_only_to_out(self, tmp_path, monkeypatch, capsys, depth):
        monkeypatch.setenv("NO_COLOR", "1")
        manifest_path = _create_run_fixture(tmp_path)
        buf = io.StringIO()

        print_report(str(manifest_path), depth, out=buf)

        rendered = buf.getvalue()
        assert "PUBRUN DIAGNOSTICS" in rendered
        assert "seam1234" in rendered
        assert capsys.readouterr().out == ""

    @pytest.mark.parametrize(
        "section,expected_text",
        [
            ("logs", "epoch 1"),
            ("env", "[ Environment Variables ]"),
            ("packages", "[ Packages ]"),
        ],
    )
    def test_print_report_sections_write_to_out(
        self, tmp_path, monkeypatch, capsys, section, expected_text
    ):
        monkeypatch.setenv("NO_COLOR", "1")
        manifest_path = _create_run_fixture(tmp_path)
        buf = io.StringIO()

        print_report(str(manifest_path), section=section, out=buf)

        assert expected_text in buf.getvalue()
        assert capsys.readouterr().out == ""

    def test_print_resources_report_writes_only_to_out(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("NO_COLOR", "1")
        manifest_path = _create_run_fixture(tmp_path)
        buf = io.StringIO()

        print_resources_report(str(manifest_path), out=buf)

        rendered = buf.getvalue()
        assert "RESOURCE MONITORING" in rendered
        assert "CPU Utilization History" in rendered
        assert capsys.readouterr().out == ""

    def test_out_default_is_current_stdout(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("NO_COLOR", "1")
        manifest_path = _create_run_fixture(tmp_path)

        print_report(str(manifest_path), "basic")

        assert "PUBRUN DIAGNOSTICS" in capsys.readouterr().out

    def test_ascii_stream_gets_ascii_glyphs(self, tmp_path, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        manifest_path = _create_run_fixture(tmp_path)

        # Non-TTY without FORCE_COLOR must emit zero ANSI escapes.
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        plain_raw = io.BytesIO()
        plain_out = io.TextIOWrapper(plain_raw, encoding="ascii")
        print_report(str(manifest_path), "basic", out=plain_out)
        print_resources_report(str(manifest_path), out=plain_out)
        plain_out.flush()
        plain_text = plain_raw.getvalue().decode("ascii")
        assert "\x1b[" not in plain_text
        assert "=================================================" in plain_text

        # With FORCE_COLOR=1, ASCII streams get ASCII box headers and UTF-8 streams get Unicode.
        monkeypatch.setenv("FORCE_COLOR", "1")
        ascii_raw = io.BytesIO()
        ascii_out = io.TextIOWrapper(ascii_raw, encoding="ascii")
        print_report(str(manifest_path), "basic", out=ascii_out)
        print_resources_report(str(manifest_path), out=ascii_out)
        ascii_out.flush()
        ascii_text = ascii_raw.getvalue().decode("ascii")
        assert "+-------------------------------------------------+" in ascii_text
        assert "\x1b[2m" not in ascii_text

        utf8_raw = io.BytesIO()
        utf8_out = io.TextIOWrapper(utf8_raw, encoding="utf-8")
        print_report(str(manifest_path), "basic", out=utf8_out)
        print_resources_report(str(manifest_path), out=utf8_out)
        utf8_out.flush()
        utf8_text = utf8_raw.getvalue().decode("utf-8")
        assert "┌" in utf8_text
        assert "\x1b[2m" not in utf8_text

    def test_unknown_section_raises_exit_code_2(self, tmp_path):
        manifest_path = _create_run_fixture(tmp_path)
        buf = io.StringIO()
        with pytest.raises(DiagnosticsError) as exc_info:
            print_report(str(manifest_path), section="bogus", out=buf)
        assert exc_info.value.exit_code == 2
        assert "bogus" in str(exc_info.value)
        for sec in ("logs", "env", "packages"):
            assert sec in str(exc_info.value)

    def test_show_logs_missing_files_emits_stderr_hint_and_empty_stdout(self, tmp_path, capsys):
        manifest_path = _create_run_fixture(tmp_path)
        (manifest_path.parent / "stdout.log").unlink()
        buf = io.StringIO()
        print_report(str(manifest_path), section="logs", out=buf)
        assert buf.getvalue() == ""
        captured = capsys.readouterr()
        assert captured.out == ""
        assert 'capture_mode = "standard"' in captured.err
        assert "pubrun.full" in captured.err

    def test_show_logs_streams_multi_chunk_files(self, tmp_path):
        manifest_path = _create_run_fixture(tmp_path)
        big_stdout = "A" * 70000 + "\nEND_STDOUT\n"
        big_stderr = "B" * 70000 + "\nEND_STDERR\n"
        (manifest_path.parent / "stdout.log").write_text(big_stdout, encoding="utf-8")
        (manifest_path.parent / "stderr.log").write_text(big_stderr, encoding="utf-8")
        buf = io.StringIO()
        print_report(str(manifest_path), section="logs", out=buf)
        assert buf.getvalue() == big_stdout + big_stderr

    def test_events_timeline_o1_truncation_corrupt_lines_and_no_dim(self, tmp_path, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("FORCE_COLOR", "1")
        manifest_path = _create_run_fixture(tmp_path)
        lines = []
        for i in range(25):
            lines.append(
                json.dumps(
                    {
                        "type": "metric",
                        "name": f"ev_{i:02d}",
                        "timestamp_utc": 1000.0 + i,
                        "payload": {"step": i},
                    }
                )
            )
        # Interleave blank lines, truncated JSON, and a non-dict JSON entry.
        lines.insert(5, "")
        lines.insert(12, '{"type": "truncated')
        lines.insert(18, "[1, 2, 3]")
        (manifest_path.parent / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

        buf = io.StringIO()
        print_report(str(manifest_path), "basic", utc=True, out=buf)
        rendered = buf.getvalue()
        assert "ev_00" in rendered and "ev_09" in rendered
        assert "ev_10" not in rendered and "ev_14" not in rendered
        assert "ev_15" in rendered and "ev_24" in rendered
        assert "... [ 5 events truncated ] ..." in rendered
        assert "Skipped 2 corrupt or non-object event line(s)." in rendered
        assert "\x1b[2m" not in rendered

    def test_print_resources_report_utc_and_malformed_nested_dicts(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        run_dir = tmp_path / "pubrun-malformed"
        run_dir.mkdir(parents=True)
        manifest = {
            "run": "not-a-dict",
            "timing": None,
            "status": ["bad"],
            "invocation": {"script": "not-a-dict"},
            "resources": {
                "peak_rss_bytes": float("nan"),
                "peak_cpu_percent": float("inf"),
                "end_rss_bytes": True,
                "system_memory": "bad",
                "load_average": {"start": "bad", "max_1min": float("nan")},
                "system_iowait_pct": "bad",
                "io_counters": {"delta": "bad"},
            },
        }
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, allow_nan=True), encoding="utf-8")
        events = [
            {"type": "resource_sample", "timestamp_utc": 100.0, "payload": {"rss_bytes": 1024**2, "cpu_percent": 10.0}},
            {"type": "resource_sample", "timestamp_utc": 130.0, "payload": {"rss_bytes": 2 * 1024**2, "cpu_percent": 30.0}},
        ]
        (run_dir / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")

        buf = io.StringIO()
        print_resources_report(str(manifest_path), utc=True, width=40, out=buf)
        rendered = buf.getvalue()
        assert "RESOURCE MONITORING" in rendered
        assert "1970-01-01 00:01:40Z" in rendered
        assert "1970-01-01 00:02:10Z" in rendered


class TestDiagnosticsError:
    """Verify all seven error paths raise DiagnosticsError without writing to stdout/stderr."""

    def test_print_report_missing_manifest(self, tmp_path, capsys):
        missing = str(tmp_path / "does-not-exist" / "manifest.json")
        buf = io.StringIO()

        with pytest.raises(DiagnosticsError) as exc_info:
            print_report(missing, out=buf)

        err = exc_info.value
        assert err.exit_code == 1
        assert str(err) == f"Could not find manifest file at '{missing}'."
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_print_report_corrupt_manifest(self, tmp_path, capsys):
        bad_manifest = tmp_path / "manifest.json"
        bad_manifest.write_text("{bad", encoding="utf-8")
        buf = io.StringIO()

        with pytest.raises(DiagnosticsError) as exc_info:
            print_report(str(bad_manifest), out=buf)

        err = exc_info.value
        assert err.exit_code == 1
        assert str(err) == f"The manifest file at '{bad_manifest}' is corrupt or contains invalid JSON."
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_print_report_unreadable_stdout_log(self, tmp_path, capsys):
        manifest_path = _create_run_fixture(tmp_path)
        stdout_log = manifest_path.parent / "stdout.log"
        stdout_log.unlink()
        stdout_log.mkdir()
        buf = io.StringIO()

        with pytest.raises(DiagnosticsError) as exc_info:
            print_report(str(manifest_path), section="logs", out=buf)

        err = exc_info.value
        assert err.exit_code == 1
        assert str(err).startswith("Failed to read stdout log: ")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_print_report_unreadable_stderr_log(self, tmp_path, capsys):
        manifest_path = _create_run_fixture(tmp_path)
        (manifest_path.parent / "stderr.log").mkdir()
        buf = io.StringIO()

        with pytest.raises(DiagnosticsError) as exc_info:
            print_report(str(manifest_path), section="logs", out=buf)

        err = exc_info.value
        assert err.exit_code == 1
        assert str(err).startswith("Failed to read stderr log: ")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_print_resources_report_missing_manifest(self, tmp_path, capsys):
        missing = str(tmp_path / "missing" / "manifest.json")
        buf = io.StringIO()

        with pytest.raises(DiagnosticsError) as exc_info:
            print_resources_report(missing, out=buf)

        err = exc_info.value
        assert err.exit_code == 1
        assert str(err) == f"Could not find manifest file at '{missing}'."
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_print_resources_report_corrupt_manifest(self, tmp_path, capsys):
        bad_manifest = tmp_path / "manifest.json"
        bad_manifest.write_text("{bad", encoding="utf-8")
        buf = io.StringIO()

        with pytest.raises(DiagnosticsError) as exc_info:
            print_resources_report(str(bad_manifest), out=buf)

        err = exc_info.value
        assert err.exit_code == 1
        assert str(err) == f"The manifest file at '{bad_manifest}' is corrupt or contains invalid JSON."
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_print_resources_report_invalid_last(self, tmp_path, capsys):
        manifest_path = _create_run_fixture(tmp_path)
        buf = io.StringIO()

        with pytest.raises(DiagnosticsError) as exc_info:
            print_resources_report(str(manifest_path), last="bogus", out=buf)

        err = exc_info.value
        assert err.exit_code == 1
        assert str(err).startswith("Invalid duration for --last: ")
        assert buf.getvalue() == ""
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_print_resources_report_invalid_last_without_events_jsonl(self, tmp_path, capsys):
        manifest_path = _create_run_fixture(tmp_path)
        (manifest_path.parent / "events.jsonl").unlink()
        buf = io.StringIO()

        with pytest.raises(DiagnosticsError) as exc_info:
            print_resources_report(str(manifest_path), last="bogus", out=buf)

        err = exc_info.value
        assert err.exit_code == 1
        assert str(err).startswith("Invalid duration for --last: ")
        assert buf.getvalue() == ""
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""
