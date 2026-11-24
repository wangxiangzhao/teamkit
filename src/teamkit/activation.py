"""Safe, reversible AGENTS.md merge: project instructions always win."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

START = "<!-- TEAMKIT MASTER START -->"
END = "<!-- TEAMKIT MASTER END -->"
RULES = """<!-- TEAMKIT MASTER START -->
## TeamKit Master (project extension)
Existing project, ancestor and nested AGENTS.md rules have precedence over TeamKit.
Never override project business rules, model, sandbox, approvals, signing or CI.
Execute simple tasks directly. Delegate only independent tasks where native
Codex subagents are available and existing project rules permit delegation.
Choose the minimum useful roles and skills. Keep context scoped and preserve
user changes. Treat absent build, test, device, Figma or external data as
blocked/not-run, not success. Do not change production services.
<!-- TEAMKIT MASTER END -->
"""


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _paths(project: Path):
    root = project.resolve()
    return root / "AGENTS.md", root / ".teamkit" / "agents-merge.json"


def _inspect(raw: bytes) -> bool:
    if raw.count(START.encode()) != raw.count(END.encode()) or raw.count(START.encode()) > 1:
        raise ValueError("Conflicting TeamKit markers; manual review required")
    if START.encode() in raw and raw.index(START.encode()) > raw.index(END.encode()):
        raise ValueError("Reversed TeamKit markers")
    return START.encode() in raw


def inspect(project: Path) -> dict:
    path, metadata = _paths(project)
    if path.is_symlink() or metadata.is_symlink():
        raise ValueError("Cannot merge symlinked AGENTS or metadata")
    raw = path.read_bytes() if path.exists() else b""
    active = _inspect(raw)
    if metadata.exists() and not active:
        raise ValueError("Stale TeamKit merge metadata; manual review required")
    return {"status": "already-active" if active else "mergeable",
            "has_existing_agents": path.exists(), "preserve_original": True,
            "project_rules_override_teamkit": True}


def activate(project: Path, *, approve: bool = False) -> dict:
    path, metadata = _paths(project)
    if not (project.resolve() / ".teamkit" / "project.json").exists():
        raise FileNotFoundError("Run teamkit init first")
    state = inspect(project)
    if state["status"] == "already-active":
        return {"status": "already-active", "path": str(path)}
    if not approve:
        return {"status": "dry-run", "path": str(path), "required": "--approve"}
    existed = path.exists()
    original = path.read_bytes() if existed else b""
    newline = b"\r\n" if b"\r\n" in original else b"\n"
    separator = b"" if not original or original.endswith(newline * 2) else (newline if original.endswith(newline) else newline * 2)
    block = RULES.replace("\n", newline.decode()).encode()
    added = separator + block
    backup = project.resolve() / ".teamkit" / "AGENTS.backup.md"
    if existed and not backup.exists():
        backup.write_bytes(original)
    # Commit in a guarded transaction. If the manifest cannot be persisted,
    # restore the exact original bytes and never strand an unknown insertion.
    try:
        path.write_bytes(original + added)
        metadata.write_text(json.dumps({"version": 2, "original_existed": existed,
            "original_length": len(original), "original_sha256": _hash(original),
            "added_sha256": _hash(added), "added_length": len(added)}, indent=2)+"\n")
    except Exception:
        if metadata.exists():
            metadata.unlink()
        if existed:
            path.write_bytes(original)
        elif path.exists():
            path.unlink()
        raise
    return {"status": "active", "path": str(path), "original_preserved": True,
            "project_rules_override_teamkit": True}


def deactivate(project: Path, *, approve: bool = False) -> dict:
    path, metadata = _paths(project)
    if path.is_symlink() or metadata.is_symlink():
        raise ValueError("Cannot edit symlinked instructions")
    if not path.exists():
        return {"status": "not-active", "path": str(path)}
    raw = path.read_bytes()
    if not _inspect(raw):
        return {"status": "not-active", "path": str(path)}
    if not metadata.exists():
        raise ValueError("Legacy TeamKit block without merge metadata; manual review required")
    info = json.loads(metadata.read_text())
    if info.get("version") != 2:
        raise ValueError("Unsupported TeamKit merge metadata")
    length = info["original_length"]
    end = length + info["added_length"]
    if len(raw) < end or _hash(raw[:length]) != info["original_sha256"] or _hash(raw[length:end]) != info["added_sha256"]:
        raise ValueError("AGENTS.md edited inside or before TeamKit block; refuse destructive removal")
    if not approve:
        return {"status": "dry-run", "path": str(path), "required": "--approve"}
    remainder = raw[:length] + raw[end:]
    if info["original_existed"] or remainder:
        path.write_bytes(remainder)
    else:
        path.unlink()
    metadata.unlink()
    return {"status": "inactive", "path": str(path), "other_instructions_preserved": True}
