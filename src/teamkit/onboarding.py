"""One-command, conservative project onboarding and safe detach.

No code execution, network requests, source editing, or credential changes.
The only project-visible hook is a delimited AGENTS.md section, removable with detach.
"""
from __future__ import annotations

import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from .activation import activate, deactivate, START, END
from .core import init_project, json_read, json_write, project_status, sync_project
from .audit import safe_maintain
from .native import probe_native
from .project_inspect import inspect_project
from .privacy_audit import inspect_privacy


def _discover_shared_schemes(project: Path) -> dict:
    """Read shared Xcode scheme XML; never invoke an Xcode build."""
    root = project.resolve()
    result = []
    candidates = sorted(root.glob("*.xcodeproj")) + sorted(root.glob("*.xcworkspace"))
    for container in candidates:
        if container.is_symlink():
            continue
        schemes = container / "xcshareddata" / "xcschemes"
        if not schemes.is_dir() or schemes.is_symlink():
            continue
        for scheme in sorted(schemes.glob("*.xcscheme")):
            if scheme.is_symlink() or scheme.stat().st_size > 1024 * 1024:
                continue
            try:
                parsed = ET.parse(scheme)
                has_build = parsed.find(".//BuildActionEntry") is not None
            except (ET.ParseError, OSError):
                continue
            if has_build:
                result.append({
                    "container": container.relative_to(root).as_posix(),
                    "kind": "workspace" if container.suffix == ".xcworkspace" else "project",
                    "scheme": scheme.stem,
                    "source": scheme.relative_to(root).as_posix(),
                })
    # Prefer workspace if one explicit workspace has the desired scheme.
    # Multiple valid combinations remain ambiguous, never guess.
    pairs = {(x["container"], x["scheme"]) for x in result}
    result = [x for x in result if (x["container"], x["scheme"]) in pairs]
    return {"candidates": result, "ambiguous": len(result) != 1}


def inspect_onboarding(project: Path) -> dict:
    root = project.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Project not found: {root}")
    target = root / "AGENTS.md"
    if target.is_symlink():
        raise ValueError("Refuse symlinked AGENTS.md")
    if target.exists():
        text = target.read_text(encoding="utf-8")
        if (START in text) != (END in text) or text.count(START) > 1 or text.count(END) > 1:
            raise ValueError("Existing AGENTS.md has conflicting TeamKit markers")
    else:
        text = ""
    workspace = root / ".teamkit"
    if workspace.is_symlink():
        raise ValueError("Refuse symlinked .teamkit")
    if workspace.exists() and not workspace.is_dir():
        raise ValueError(".teamkit exists and is not a directory")
    profile = workspace / "project.json"
    if profile.is_symlink():
        raise ValueError("Refuse symlinked project metadata")
    # Only unambiguously owned metadata can be reused; never overwrite arbitrary directories.
    if workspace.exists() and not profile.exists() and any(workspace.iterdir()):
        raise FileExistsError("Non-empty .teamkit directory is not initialized by TeamKit")
    schemes = _discover_shared_schemes(root)
    return {
        "project": str(root),
        "already_initialized": profile.exists(),
        "already_active": START in text and END in text,
        "has_existing_agents": target.exists(),
        "shared_schemes": schemes,
        "will_write": (
            ([] if profile.exists() else [".teamkit/{project,index,extensions,gates}.json"])
            + ([] if START in text else ["AGENTS.md"])
        ),
        "will_not_touch": ["business source", "Xcode project settings", "Podfile", "Package.swift", "Codex credentials", "global Codex settings"],
    }


def onboard(project: Path, *, dry_run: bool = False) -> dict:
    root = project.resolve()
    preview = inspect_onboarding(root)
    if dry_run:
        return {"status": "dry-run", **preview}
    # Validate AGENTS compatibility before writes; do not auto-install external Skills.
    initialized_here = False
    try:
        if not preview["already_initialized"]:
            init_project(root)
            initialized_here = True
        schemes = preview["shared_schemes"]
        # Auto-configure safe simulator build argv only when one shared scheme
        # and explicit iOS SDK indicators are present. Never execute on onboarding.
        if not schemes["ambiguous"]:
            selected = schemes["candidates"][0]
            xcodeproj = selected["container"] if selected["kind"] == "project" else None
            pbx = root / xcodeproj / "project.pbxproj" if xcodeproj else None
            if pbx and pbx.is_file() and not pbx.is_symlink():
                content = pbx.read_text(encoding="utf-8", errors="replace")
                if "iphoneos" in content or "iphonesimulator" in content:
                    gates_file = root / ".teamkit" / "gates.json"
                    gates = json_read(gates_file, {})
                    if gates.get("build_command") is None:
                        gates["build_command"] = ["xcodebuild", "-project", xcodeproj,
                                                  "-scheme", selected["scheme"],
                                                  "-configuration", "Debug",
                                                  "-destination", "generic/platform=iOS Simulator",
                                                  "CODE_SIGNING_ALLOWED=NO", "build"]
                        json_write(gates_file, gates)
        # SwiftPM-only projects should not need hand-edited gates.json.
        # The scratch path lives inside TeamKit metadata, not .build in source.
        if not schemes["candidates"] and (root / "Package.swift").is_file():
            gates_file = root / ".teamkit" / "gates.json"
            gates = json_read(gates_file, {})
            scratch = ".teamkit/swift-build"
            if gates.get("build_command") is None:
                gates["build_command"] = ["swift", "build", "--scratch-path", scratch]
            if gates.get("test_command") is None and (root / "Tests").is_dir():
                gates["test_command"] = ["swift", "test", "--scratch-path", scratch]
            json_write(gates_file, gates)
        # Automatic configuration never means the build was actually run.
        # Store discovery as an informational hint, not as a falsely verified build gate.
        workspace = root / ".teamkit"
        json_write(workspace / "discovery.json", {
            "shared_schemes": schemes,
            "build_not_run": True,
            "codex_available": shutil.which("codex") is not None,
            "xcodebuild_available": shutil.which("xcodebuild") is not None,
            "notes": "Build and simulator compatibility require real execution; no scheme is guessed when ambiguous.",
        })
        activated = activate(root, approve=True)
        # Establish the baseline *after* adding the optional AGENTS hook.
        # Otherwise the first 'teamkit check' incorrectly reports the hook as a user change.
        sync_project(root)
        maintenance = safe_maintain(root)
        project_insights = inspect_project(root)
        privacy_preflight = inspect_privacy(root)
        return {
            "status": "ready",
            "self_audit": maintenance,
            "project_insights": project_insights,
            "privacy_preflight": privacy_preflight,
            "project": str(root),
            "initialized": initialized_here,
            "activation": activated["status"],
            "xcode_scheme": schemes["candidates"][0] if not schemes["ambiguous"] else None,
            "xcode_scheme_requires_review": schemes["ambiguous"],
            "how_to_use": "Run codex in this project; TeamKit rules are available in AGENTS.md",
            "native_environment": probe_native(skip_simulator=False),
            "limitations": "No build, authenticated native subagent, Figma or StoreKit execution verified during onboarding",
        }
    except Exception:
        # If this command created metadata but failed before activation, don't leave a
        # partially initialized project behind; never destroy pre-existing metadata.
        if initialized_here and not (root / "AGENTS.md").is_file():
            from shutil import rmtree
            rmtree(root / ".teamkit")
        raise


def detach(project: Path, *, dry_run: bool = False) -> dict:
    root = project.resolve()
    info = inspect_onboarding(root)
    if dry_run:
        return {"status": "dry-run", "will_remove_teamkit_marker": info["already_active"],
                "will_keep_project_metadata": True, "project": str(root)}
    result = deactivate(root, approve=True)
    return {
        "status": "detached", "activation": result["status"], "project": str(root),
        "metadata_preserved": True,
        "note": ".teamkit metadata is deliberately left intact; manual cleanup is optional after reviewing customized data",
    }
