"""Tests for the benchmark-result Issue Form (IPD 20260721-2255-01, Step 3).

The form must fit the existing ISSUE_TEMPLATE chooser convention (name/title/labels), apply
the benchmark-submission marker label the workflow gates on, require the attachment field and
the privacy checkbox, and NOT change config.yml. Avoids a hard PyYAML dependency.
"""
import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_FORM = _REPO / ".github" / "ISSUE_TEMPLATE" / "benchmark-result.yml"
_CONFIG = _REPO / ".github" / "ISSUE_TEMPLATE" / "config.yml"


def test_form_exists():
    assert _FORM.is_file()


def test_form_front_matter_matches_sibling_convention():
    text = _FORM.read_text(encoding="utf-8")
    assert re.search(r"^name:\s*\S", text, re.M)
    assert re.search(r'^title:\s*"\[BENCH\]: "', text, re.M)
    # Applies the marker label the workflow gates on, plus a pending status.
    assert "type:benchmark-submission" in text
    assert "status:pending" in text


def test_form_requires_attachment_and_privacy_ack():
    text = _FORM.read_text(encoding="utf-8")
    # Required attachment field.
    assert "attachment" in text
    # A required privacy-acknowledgment checkbox.
    assert re.search(r"required:\s*true", text)
    assert "redacted" in text and "did NOT attach the unredacted" in text


def test_config_still_allows_blank_issues():
    # Do not disable blank issues; the form is additive.
    assert "blank_issues_enabled: true" in _CONFIG.read_text(encoding="utf-8")


def test_form_parses_as_yaml_when_available():
    yaml = pytest.importorskip("yaml")
    data = yaml.safe_load(_FORM.read_text(encoding="utf-8"))
    assert data["name"]
    assert data["labels"] == ["type:benchmark-submission", "status:pending"]
    ids = {b.get("id") for b in data["body"] if isinstance(b, dict)}
    assert "attachment" in ids and "privacy" in ids
    # The privacy checkbox is required.
    privacy = next(b for b in data["body"] if b.get("id") == "privacy")
    assert privacy["attributes"]["options"][0]["required"] is True
