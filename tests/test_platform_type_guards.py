"""Behavioral tests for cross-platform mypy guards and the _sysconf helpers."""
import os
import sys
from typing import Any, List, Tuple

import pytest

from pubrun.capture import liveness, resources, subprocesses, system_metrics


def test_get_load_average_is_none_on_windows_without_calling_getloadavg(
    monkeypatch: Any,
) -> None:
    calls: List[int] = []

    def fake_getloadavg() -> Tuple[float, float, float]:
        calls.append(1)
        return (1.0, 2.0, 3.0)

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "getloadavg", fake_getloadavg, raising=False)

    assert system_metrics.get_load_average() is None
    assert calls == []


def test_decode_wait_status_returns_raw_status_on_windows(monkeypatch: Any) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delattr(os, "waitstatus_to_exitcode", raising=False)

    assert subprocesses._decode_wait_status(256) == 256


@pytest.mark.parametrize("module", [liveness, resources], ids=["liveness", "resources"])
def test_sysconf_helper_raises_attribute_error_without_os_sysconf(
    monkeypatch: Any, module: Any
) -> None:
    monkeypatch.delattr(os, "sysconf", raising=False)

    with pytest.raises(AttributeError, match="module 'os' has no attribute 'sysconf'"):
        module._sysconf("SC_CLK_TCK")


@pytest.mark.parametrize("module", [liveness, resources], ids=["liveness", "resources"])
def test_sysconf_helper_returns_int_from_os_sysconf(
    monkeypatch: Any, module: Any
) -> None:
    def fake_sysconf(name: str) -> int:
        assert name == "SC_PAGE_SIZE"
        return 4096

    monkeypatch.setattr(os, "sysconf", fake_sysconf, raising=False)

    result = module._sysconf("SC_PAGE_SIZE")
    assert result == 4096
    assert type(result) is int


def test_resource_watcher_clock_ticks_zero_without_os_sysconf(monkeypatch: Any) -> None:
    monkeypatch.delattr(os, "sysconf", raising=False)

    watcher = resources.ResourceWatcher(
        run_tracker=None,
        interval_seconds=1.0,
        system_metrics=False,
    )
    assert watcher._clk_tck == 0
