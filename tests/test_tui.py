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


def test_tui_toml_serialization():
    """Verify that the dict_to_toml helper serializes configurations correctly."""
    from pubrun.tui.widgets.config import dict_to_toml
    
    test_dict = {
        "core": {
            "profile": "default",
            "auto_start": True,
            "sample_int": 15
        },
        "capture": {
            "environment": {
                "mode": "filtered"
            }
        }
    }
    
    toml_str = dict_to_toml(test_dict)
    
    # Assert section headers are generated correctly
    assert "[core]" in toml_str
    assert "[capture.environment]" in toml_str
    
    # Assert values are serialized correctly
    assert 'profile = "default"' in toml_str
    assert 'auto_start = true' in toml_str
    assert 'sample_int = 15' in toml_str
    assert 'mode = "filtered"' in toml_str
