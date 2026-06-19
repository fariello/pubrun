import pytest
from pubrun.report.methods import generate_report, bytes_to_gb, extract_highlighted_packages

def test_bytes_to_gb():
    assert bytes_to_gb(0) == 0.0
    assert bytes_to_gb(1024 ** 3) == 1.0
    assert bytes_to_gb(2 * 1024 ** 3) == 2.0
    assert bytes_to_gb(1.5 * 1024 ** 3) == 1.5

def test_extract_highlighted_packages():
    manifest = {
        "packages": {
            "records": [
                {"name": "numpy", "version": "1.21.0"},
                {"name": "pandas", "version": "1.3.0"},
                {"name": "invalid-pkg", "version": "0.1.0"},
                {"name": "torch", "version": "1.9.0"}
            ]
        }
    }
    extracted = extract_highlighted_packages(manifest)
    assert "numpy (v1.21.0)" in extracted
    assert "pandas (v1.3.0)" in extracted
    assert "torch (v1.9.0)" in extracted
    assert len(extracted) == 3

def test_generate_report_markdown():
    manifest = {
        "host": {
            "os_name": "Ubuntu_Linux"
        },
        "hardware": {
            "cpu": {"model": "Intel Core i7"},
            "memory_total_bytes": 16 * 1024 ** 3
        },
        "python": {
            "version": "3.10.2 final",
            "implementation": "cpython"
        },
        "git": {
            "commit": "abcdef1234567890",
            "remote_url": {"value": "https://github.com/user/repo"}
        },
        "packages": {
            "records": [
                {"name": "numpy", "version": "1.21.0"}
            ]
        }
    }
    
    report = generate_report(manifest, format_type="markdown")
    assert "Ubuntu_Linux" in report
    assert "Intel Core i7" in report
    assert "16.0 GB of RAM" in report
    assert "Python 3.10.2" in report
    assert "Cpython" in report
    assert "numpy (v1.21.0)" in report
    assert "abcdef12" in report
    assert "https://github.com/user/repo" in report
    assert "Computational Methods" in report

def test_generate_report_latex_escaping():
    manifest = {
        "host": {
            "os_name": "Ubuntu_Linux"
        },
        "hardware": {
            "cpu": {"model": "Intel Core i7"},
            "memory_total_bytes": 16 * 1024 ** 3
        },
        "python": {
            "version": "3.10.2 final",
            "implementation": "cpython"
        },
        "git": {
            "commit": "abcdef1234567890",
            "remote_url": {"value": "https://github.com/user/repo_name"}
        },
        "packages": {
            "records": []
        }
    }
    
    report = generate_report(manifest, format_type="latex")
    # LaTeX template should escape underscores
    assert "Ubuntu\\_Linux" in report
    assert "repo\\_name" in report
    assert "Standard library dependencies were utilized." in report
    assert "fariello_pubrun_2026" in report
