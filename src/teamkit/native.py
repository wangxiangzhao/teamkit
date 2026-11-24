"""Non-invasive native tool probes with explicit, reproducible evidence.

Probes commands only; never contacts an authenticated model, modifies Xcode
settings, starts simulators, downloads runtimes, or changes user credentials.
"""
from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any


PROBES = {
    "codex_version": ["codex", "--version"],
    "codex_exec": ["codex", "exec", "--help"],
    "xcode": ["xcodebuild", "-version"],
    "simctl": ["xcrun", "simctl", "list", "devices", "available"],
    "swift": ["swift", "--version"],
}


def _probe(args: list[str], *, timeout: int = 12) -> dict[str, Any]:
    binary = shutil.which(args[0])
    if binary is None:
        return {"status": "not-available", "binary": args[0], "command": args}
    try:
        completed = subprocess.run(
            [binary, *args[1:]],
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"status": "blocked", "reason": "probe timeout", "command": args}
    except OSError as exc:
        return {"status": "blocked", "reason": str(exc), "command": args}
    return {
        "status": "passed" if completed.returncode == 0 else "failed",
        "command": args,
        "exit_code": completed.returncode,
        "stdout_tail": completed.stdout[-1400:],
        "stderr_tail": completed.stderr[-700:],
    }


def probe_native(*, skip_simulator: bool = False) -> dict[str, Any]:
    probes = {name: _probe(command) for name, command in PROBES.items()
              if not (skip_simulator and name == "simctl")}
    return {
        "platform": platform.platform(),
        "tools": probes,
        "codex_cli_discovered": probes["codex_version"]["status"] == "passed",
        "codex_exec_interface_checked": probes["codex_exec"]["status"] == "passed",
        "xcode_command_checked": probes["xcode"]["status"] == "passed",
        "simulator_listing_checked": (probes.get("simctl") or {}).get("status") == "passed",
        "native_subagent_spawn_verified": False,
        "real_project_build_verified": False,
        "real_figma_mcp_verified": False,
        "warning": "Help/version/simulator inventory checks do NOT verify authenticated Codex dispatch, build correctness, or screenshot fidelity.",
    }
