"""Tests for the deprecation of the (never-wired) `core.profile` setting.

Background: `core.profile` ("minimal"/"default"/"deep") was documented and exposed
(config key, PUBRUN_PROFILE env var, start(profile=) kwarg, TUI selector) as a
"master capture depth" dial, but it was never connected to any capture engine —
setting it had no effect on what pubrun captured. Per the executed decision
(.agents/plans/executed/2026-07-08-meta-ref-profile-capture-suppression.md, Option
D), `profile` is deprecated: still accepted (no import breaks), but explicitly inert
for capture, with a non-disruptive notice recorded in the manifest.

The first test is a CHARACTERIZATION test pinning the pre-existing reality (profile
does not gate capture) so the deprecation is a deliberate, documented state.
"""
import json

from pubrun.config import resolve_config, profile_deprecation_notice


class TestProfileDoesNotGateCapture:
    """Characterization: `core.profile` has never affected capture depth."""

    def test_minimal_and_deep_profiles_capture_identically(self, monkeypatch):
        """With only `profile` differing, hardware/packages capture the same.

        If profile were a real capture dial, `minimal` would suppress hardware and
        packages while `deep` would not. It does neither — proving profile is inert.
        """
        monkeypatch.setattr("pubrun.config.load_user_config", lambda: None)
        monkeypatch.setattr("pubrun.config.load_local_config", lambda start_dir=None: None)
        monkeypatch.delenv("PUBRUN_PROFILE", raising=False)

        minimal = resolve_config({"core": {"profile": "minimal"}})
        deep = resolve_config({"core": {"profile": "deep"}})

        # profile changes nothing about the capture.* keys that actually gate capture.
        assert minimal["capture"]["hardware"]["depth"] == deep["capture"]["hardware"]["depth"]
        assert minimal["capture"]["packages"]["mode"] == deep["capture"]["packages"]["mode"]
        # And both equal the built-in defaults (profile did not lower or raise them).
        base = resolve_config()
        assert minimal["capture"]["hardware"]["depth"] == base["capture"]["hardware"]["depth"]
        assert minimal["capture"]["packages"]["mode"] == base["capture"]["packages"]["mode"]


class TestProfileDeprecationNotice:
    """The deprecation notice is a recorded fact, never an exception into the host."""

    def test_notice_for_nondefault_profile(self):
        assert profile_deprecation_notice({"core": {"profile": "minimal"}}) is not None
        assert profile_deprecation_notice({"core": {"profile": "deep"}}) is not None

    def test_no_notice_for_default_or_unset(self):
        assert profile_deprecation_notice({"core": {"profile": "default"}}) is None
        assert profile_deprecation_notice({"core": {}}) is None
        assert profile_deprecation_notice({}) is None

    def test_notice_shape(self):
        n = profile_deprecation_notice({"core": {"profile": "minimal"}})
        assert n["code"] == "profile_deprecated"
        assert n["setting"] == "core.profile"
        assert n["value"] == "minimal"
        assert "no effect" in n["message"]


class TestProfileNoticeRecordedAndSurfaced:
    """End-to-end: a non-default profile is recorded in the manifest and surfaced by
    the human-facing commands, and never raised into the host script."""

    def test_manifest_records_notice(self, isolated_cwd):
        import pubrun.noauto as pubrun
        t = pubrun.start(profile="minimal")
        pubrun.stop()
        manifest = json.loads((t.run_dir / "manifest.json").read_text(encoding="utf-8"))
        notices = manifest["config"]["notices"]
        assert any(n["code"] == "profile_deprecated" for n in notices)

    def test_default_profile_records_no_notice(self, isolated_cwd):
        import pubrun.noauto as pubrun
        t = pubrun.start()  # default profile
        pubrun.stop()
        manifest = json.loads((t.run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["config"]["notices"] == []

    def test_runinfo_and_status_surface_notice(self, isolated_cwd):
        from pubrun.status import RunInfo, render_inspect, render_short_list, scan_runs

        import pubrun.noauto as pubrun
        t = pubrun.start(profile="deep")
        pubrun.stop()

        # RunInfo parses the notice off the manifest.
        info = RunInfo(t.run_dir)
        assert any(n["code"] == "profile_deprecated" for n in info.config_notices)

        # `pubrun status <id>` detail view surfaces it.
        assert "no effect" in render_inspect(info)

        # `pubrun status` list shows a discovery hint.
        runs = scan_runs(str(t.run_dir.parent))
        assert "config notices" in render_short_list(runs)

    def test_inspect_emits_notice_finding(self):
        """`pubrun inspect` turns a recorded notice into a WARN finding (json-visible).

        Uses a hand-built manifest (no live run) to keep report-module imports isolated
        from the tracker's report machinery.
        """
        from pubrun.report.checks import manifest_findings

        manifest = {
            "config": {
                "notices": [
                    {"code": "profile_deprecated", "setting": "core.profile",
                     "value": "minimal", "message": "core.profile='minimal' has no effect."}
                ]
            }
        }
        codes = [f.get("code") for f in manifest_findings(manifest)]
        assert "profile_deprecated" in codes
