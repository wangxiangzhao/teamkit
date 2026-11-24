import pytest
from teamkit import native
from teamkit.cli import main


def test_native_missing_tools_report_not_available(monkeypatch):
    monkeypatch.setattr(native.shutil, "which", lambda name: None)
    result = native.probe_native()
    assert result["codex_cli_discovered"] is False
    assert result["native_subagent_spawn_verified"] is False
    assert result["tools"]["xcode"]["status"] == "not-available"


def test_native_probe_handles_cli_success_and_failure(monkeypatch):
    monkeypatch.setattr(native.shutil, "which", lambda name: "/bin/true")
    class Fake:
        returncode = 0
        stdout = "codex-cli 0.x"
        stderr = ""
    monkeypatch.setattr(native.subprocess, "run", lambda *args, **kwargs: Fake())
    result = native.probe_native(skip_simulator=True)
    assert result["codex_cli_discovered"] is True
    assert result["codex_exec_interface_checked"] is True
    assert result["native_subagent_spawn_verified"] is False


def test_native_cli_json(capsys):
    assert main(["verify-native", "--skip-simulator"]) == 0
    assert "real_project_build_verified" in capsys.readouterr().out
