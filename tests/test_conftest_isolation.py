"""Regression test proving tests/conftest.py tears down leftover runs and process hooks."""
import shutil
from pathlib import Path

pytest_plugins = ["pytester"]

_CONFTEST_SRC = Path(__file__).resolve().parent / "conftest.py"


def test_conftest_teardown_stops_active_run_and_restores_hooks(pytester):
    """A test that leaks an active run and bare SignalExitCapture must not pollute the next test."""
    shutil.copy2(_CONFTEST_SRC, pytester.path / "conftest.py")
    pytester.makeini("[pytest]\naddopts = -p no:randomly\n")
    pytester.makepyfile(
        test_inner="""
        import signal
        import sys
        import types

        import pubrun
        import pubrun.tracker
        from pubrun.capture.signals import SignalExitCapture, _TARGET_SIGNALS

        _leaked_runs = []


        def test_01_leaks_active_run_and_signal_capture():
            run = pubrun.start()
            _leaked_runs.append(run)
            assert run.is_active is True
            cap = SignalExitCapture()
            cap.install()
            assert cap._installed is True


        def test_02_sees_clean_process_state():
            assert len(_leaked_runs) == 1
            assert _leaked_runs[0].is_active is False
            assert pubrun.tracker._active_run is None
            assert sys.excepthook is sys.__excepthook__
            assert isinstance(sys.exit, types.BuiltinFunctionType)
            assert getattr(sys.exit, "__module__", None) == "sys"
            for sig_name in _TARGET_SIGNALS:
                sig = getattr(signal, sig_name, None)
                if sig is None:
                    continue
                handler = signal.getsignal(sig)
                assert getattr(handler, "__module__", None) != "pubrun.capture.signals", (
                    f"{sig_name} handler leaked from pubrun.capture.signals"
                )
        """
    )

    result = pytester.runpytest_subprocess("-v")
    result.assert_outcomes(passed=2)
