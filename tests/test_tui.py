"""Tests for pubrun TUI CLI command and dynamic dependency imports."""
import sys
import pytest
from unittest import mock
import argparse

def test_tui_cli_parser_and_run():
    """Verify that pubrun tui parses correctly and launches when dependencies exist."""
    from pubrun.__main__ import main
    
    with mock.patch("sys.argv", ["pubrun", "tui", "--dir", "/tmp/runs"]):
        with mock.patch("pubrun.tui.app.PubrunTUIApp") as mock_app:
            # Inject mocked module
            mock_module = mock.Mock()
            mock_module.PubrunTUIApp = mock_app
            sys.modules["pubrun.tui.app"] = mock_module
            
            try:
                main()
            except SystemExit as e:
                # main() might exit 0 after executing command
                assert e.code in (0, None)
                
            mock_app.assert_called_once_with(output_dir="/tmp/runs")
            mock_app.return_value.run.assert_called_once()


def test_tui_missing_dependencies_prints_notice(capsys):
    """Verify that when TUI dependencies are missing, a friendly explanation is printed and exits 1."""
    from pubrun.__main__ import main
    
    # Remove mock module if populated
    if "pubrun.tui.app" in sys.modules:
        del sys.modules["pubrun.tui.app"]
        
    with mock.patch("sys.argv", ["pubrun", "tui"]):
        # Mock import to raise ImportError
        original_import = __import__
        
        def mock_import(name, *args, **kwargs):
            if "pubrun.tui" in name or "textual" in name:
                raise ImportError("No module named 'textual'")
            return original_import(name, *args, **kwargs)
            
        with mock.patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(SystemExit) as exc_info:
                main()
                
            assert exc_info.value.code == 1
            
            captured = capsys.readouterr()
            assert "pubrun is by default zero-dependency based" in captured.err
            assert "Run `pip install textual rich`" in captured.err
