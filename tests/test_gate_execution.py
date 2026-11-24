import sys
import time

import pytest

from teamkit.cli import main
from teamkit.core import init_project, json_write
from teamkit.quality import run_gate


def configure(project, code):
    init_project(project)
    json_write(project / ".teamkit/gates.json", {
        "build_command": [sys.executable, "-c", code],
    })


def test_unconfigured_gate_fails_ci(tmp_path):
    init_project(tmp_path)
    assert main(["gate", "test", "--project", str(tmp_path), "--approve-command"]) == 1


def test_gate_keeps_bounded_output_and_exit_code(tmp_path):
    configure(tmp_path, "import os, sys; os.write(1, b'x' * 7000 + b'end'); os.write(2, b'\\xff'); sys.exit(7)")
    result = run_gate(tmp_path, "build", approve_command=True)
    assert result["exit_code"] == 7
    assert result["status"] == "failed"
    assert len(result["stdout_tail"]) == 6000
    assert result["stdout_tail"].endswith("end")
    assert result["stderr_tail"] == "\ufffd"


def test_gate_timeout_terminates_child_before_it_can_write(tmp_path):
    child = "import time; from pathlib import Path; time.sleep(1.7); Path('survived').touch()"
    configure(tmp_path, "import subprocess, sys, time; "
              f"subprocess.Popen([sys.executable, '-c', {child!r}]); "
              "time.sleep(10)")
    result = run_gate(tmp_path, "build", approve_command=True, timeout=1)
    assert result["reason"] == "timeout"
    time.sleep(1)
    assert not (tmp_path / "survived").exists()


def test_gate_rejects_symlinked_report_directory(tmp_path):
    configure(tmp_path, "raise SystemExit(0)")
    reports = tmp_path / ".teamkit/reports"
    if reports.exists():
        reports.rmdir()
    reports.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="Unsafe gate metadata"):
        run_gate(tmp_path, "build", approve_command=True)
