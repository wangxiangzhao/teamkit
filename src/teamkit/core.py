"""Deterministic, stdlib-only project inspection, routing and state handling.

No model inference, remote requests, or shell execution are performed here.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROLES = {
    "product": ("research", "prd", "business-flow"),
    "design": ("figma", "design-system", "motion"),
    "ios_engineer": ("swift", "swiftui", "uikit", "performance"),
    "backend_engineer": ("api", "cloud", "etl"),
    "quality": ("testing", "code-review", "ui-fidelity"),
    "compliance": ("privacy", "security", "appstore"),
    "growth": ("iaa", "iap", "ua", "roas"),
    "analytics": ("events", "retention", "cohort", "experiments"),
}

ROUTES = {
    "ui_module": {"primary": "ios_engineer", "helpers": ["design", "quality"], "skills": ["figma-contract", "ios-delivery", "quality-gates"], "risk": "T3"},
    "ios_code": {"primary": "ios_engineer", "helpers": ["quality"], "skills": ["ios-delivery"], "risk": "T2"},
    "test": {"primary": "quality", "helpers": [], "skills": ["quality-gates"], "risk": "T2"},
    "security_review": {"primary": "compliance", "helpers": ["quality"], "skills": ["quality-gates"], "risk": "T4"},
    "data_analysis": {"primary": "analytics", "helpers": ["growth"], "skills": ["analytics-roas"], "risk": "T2"},
    "monetization": {"primary": "growth", "helpers": ["analytics"], "skills": ["analytics-roas"], "risk": "T3"},
    "backend": {"primary": "backend_engineer", "helpers": ["quality"], "skills": ["project-adaptation"], "risk": "T2"},
    "product": {"primary": "product", "helpers": [], "skills": ["project-adaptation"], "risk": "T1"},
}

KEYWORDS = {
    "security_review": ["app store review", "appstore", "拒审", "审核", "隐私", "privacy", "security", "安全审计"],
    "monetization": ["roas", "ltv", "admob", "applovin", "max聚合", "广告变现", "投放", "回收", "订阅", "iap", "monetization"],
    "data_analysis": ["埋点", "留存", "漏斗", "cohort", "analytics", "firebase", "数据分析", "神策"],
    "ui_module": ["figma", "设计稿", "设计还原", "ui模块", "ui module", "界面开发"],
    "test": ["回归测试", "uitest", "xctest", "测试报告", "regression"],
    "backend": ["cdn", "oss", "server", "backend", "数据库", "api接口", "服务端"],
    "ios_code": ["swift", "uikit", "swiftui", "xcode", "崩溃", "crash", "ios", "编译", "代码"],
}

IGNORE_DIRS = {".git", ".teamkit", ".build", "build", "DerivedData", ".venv", "node_modules", "Pods", ".swiftpm", "__pycache__"}
SCAN_SUFFIXES = {".swift", ".m", ".mm", ".h", ".plist", ".pbxproj", ".yaml", ".yml", ".json", ".md", ".xcassets", ".xctestplan"}
SCAN_FILES = {"Podfile", "Package.swift", "Cartfile", "AGENTS.md", "CORE_CONTEXT.md", "PrivacyInfo.xcprivacy"}
MAX_SCAN_FILES = 25000


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    descriptor, filename = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(filename, path)
    finally:
        Path(filename).unlink(missing_ok=True)


def json_read(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(131072), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(root: Path, filename: str) -> Path:
    path = (root / filename).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Path must stay inside the project directory")
    return path


def inventory(root: Path) -> dict[str, Any]:
    """Scan relevant project files without following symlinked directories."""
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Project directory not found: {root}")
    files: dict[str, dict[str, Any]] = {}
    swift = objc = 0
    projects: list[str] = []
    workspaces: list[str] = []
    for dirname, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS and not (Path(dirname) / d).is_symlink())
        for d in dirs:
            if d.endswith(".xcodeproj"):
                projects.append(str((Path(dirname) / d).relative_to(root)))
            elif d.endswith(".xcworkspace"):
                workspaces.append(str((Path(dirname) / d).relative_to(root)))
        for name in sorted(names):
            path = Path(dirname) / name
            if path.is_symlink() or not (path.suffix in SCAN_SUFFIXES or name in SCAN_FILES or name.endswith(".xcodeproj")):
                continue
            if len(files) >= MAX_SCAN_FILES:
                raise RuntimeError(f"Project exceeds safety scan limit ({MAX_SCAN_FILES} files)")
            relative = path.relative_to(root).as_posix()
            try:
                info = path.stat()
                files[relative] = {"sha256": _fingerprint(path), "bytes": info.st_size}
            except OSError:
                continue
            swift += path.suffix == ".swift"
            objc += path.suffix in {".m", ".mm", ".h"}
    return {"root": str(root), "generated_at": now(), "files": files, "summary": {"swift_files": swift, "objc_files": objc, "xcodeproj": sorted(set(projects)), "xcworkspace": sorted(set(workspaces)), "file_count": len(files)}}


def init_project(root: Path, *, force: bool = False) -> dict[str, Any]:
    root = root.resolve()
    workspace = root / ".teamkit"
    profile_file = workspace / "project.json"
    if profile_file.exists() and not force:
        raise FileExistsError("Already initialized; use 'teamkit sync' or --force")
    scan = inventory(root)
    profile = {
        "schema_version": 1,
        "name": root.name,
        "detected": scan["summary"],
        "build": {"scheme": None, "configuration": "Debug", "destination": None},
        "capabilities": {"ios": bool(scan["summary"]["xcodeproj"] or scan["summary"]["xcworkspace"]), "monetization": None, "analytics": None},
        "execution": {"default_subagents": 0, "max_concurrency": 4},
        "notes": "Unknown capabilities remain null until confirmed; TeamKit does not guess business features.",
    }
    workspace.mkdir(exist_ok=True)
    json_write(profile_file, profile)
    json_write(workspace / "index.json", scan)
    json_write(workspace / "extensions.json", {"agents": {}, "skills": []})
    json_write(workspace / "gates.json", {"checks": ["inventory", "references"], "build_command": None, "test_command": None})
    return {"status": "initialized", "project": str(root), "files_indexed": scan["summary"]["file_count"], "profile": str(profile_file)}


def sync_project(root: Path) -> dict[str, Any]:
    workspace = root.resolve() / ".teamkit"
    if not (workspace / "project.json").exists():
        raise FileNotFoundError("Not initialized. Run 'teamkit init' first.")
    old = json_read(workspace / "index.json", {"files": {}})["files"]
    scan = inventory(root)
    new = scan["files"]
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(k for k in set(old) & set(new) if old[k]["sha256"] != new[k]["sha256"])
    json_write(workspace / "index.json", scan)
    return {"added": added, "removed": removed, "changed": changed, "counts": {"added": len(added), "removed": len(removed), "changed": len(changed)}}


def route_task(description: str, *, explicit_intent: str | None = None, project: Path | None = None) -> dict[str, Any]:
    if not description.strip():
        raise ValueError("Task description must not be empty")
    if explicit_intent is not None and explicit_intent not in ROUTES:
        raise ValueError(f"Unsupported intent: {explicit_intent}")
    lower = description.lower()
    scores = {intent: sum(1 for term in words if term in lower) for intent, words in KEYWORDS.items()}
    best = max(scores.values(), default=0)
    intent = explicit_intent or (next((name for name in ROUTES if scores.get(name, 0) == best and best > 0), "product"))
    signals = sorted((name for name, count in scores.items() if count > 0))
    route = ROUTES[intent]
    profile = json_read(project / ".teamkit" / "project.json", {}) if project else {}
    helpers = list(route["helpers"])
    if profile.get("capabilities", {}).get("monetization") is False and "growth" in helpers:
        helpers.remove("growth")
    requires_review = route["risk"] in {"T3", "T4"}
    if requires_review and route["primary"] != "quality" and "quality" not in helpers:
        helpers.append("quality")
    return {"task": description, "intent": intent, "complexity": route["risk"], "primary_agent": route["primary"], "optional_agents": helpers, "skills": route["skills"], "signals": signals, "confidence": "rule_only", "semantic_review_required": bool(not explicit_intent and (best == 0 or len([s for s in scores.values() if s == best and s > 0]) > 1)), "dispatch_policy": "Master validates semantics and project scope before invoking native Codex agents"}


def task_plan(route: dict[str, Any]) -> dict[str, Any]:
    """Create a sequential plan; optional helpers remain optional, not auto-launched."""
    key = route["intent"]
    steps = []
    if key == "ui_module":
        steps.append({"id": "design", "agent": "design", "depends_on": [], "action": "Extract design/business contract"})
    primary_dep = ["design"] if steps else []
    steps.append({"id": "implement", "agent": route["primary_agent"], "depends_on": primary_dep, "action": "Execute task within project scope"})
    if "quality" in route["optional_agents"]:
        steps.append({"id": "review", "agent": "quality", "depends_on": ["implement"], "action": "Independently validate artifacts"})
    return {"task": route["task"], "intent": key, "steps": steps, "advisory": "TeamKit records a plan; Codex Master is responsible for actual agent dispatch"}


def checkpoint(root: Path, task_id: str, state: str, note: str = "") -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", task_id):
        raise ValueError("Invalid task ID")
    if state not in {"planned", "running", "blocked", "failed", "completed"}:
        raise ValueError("Invalid task state")
    workspace = root.resolve() / ".teamkit"
    if not (workspace / "project.json").exists():
        raise FileNotFoundError("Project is not initialized")
    file = workspace / "tasks" / (task_id + ".json")
    previous = json_read(file, {})
    entry = {"task_id": task_id, "status": state, "note": note, "updated_at": now(), "project": str(root.resolve()), "history": previous.get("history", []) + [{"status": state, "note": note, "at": now()}]}
    json_write(file, entry)
    return entry


def check_project(root: Path) -> dict[str, Any]:
    workspace = root.resolve() / ".teamkit"
    if not (workspace / "project.json").exists():
        raise FileNotFoundError("Project is not initialized")
    profile = json_read(workspace / "project.json")
    scan = json_read(workspace / "index.json", {"files": {}})
    errors = []
    actual_index = inventory(root)["files"]
    for extra in sorted(set(actual_index) - set(scan["files"])):
        errors.append({"path": extra, "reason": "new_since_index"})
    for relative, expected in scan["files"].items():
        path = _safe_relative(root, relative)
        if not path.is_file() or path.is_symlink():
            errors.append({"path": relative, "reason": "missing_or_invalid"})
        elif _fingerprint(path) != expected["sha256"]:
            errors.append({"path": relative, "reason": "changed_since_index"})
    result = {"status": "failed" if errors else "passed", "checks": {"inventory": "failed" if errors else "passed", "references": "not-run"}, "errors": errors[:100], "important": "Build/test/UI/security are NOT run by the core checker; add explicit verified gates before claiming release readiness", "project": profile["name"]}
    json_write(workspace / "reports" / "latest-check.json", result)
    return result


def project_status(root: Path) -> dict[str, Any]:
    workspace = root.resolve() / ".teamkit"
    profile = json_read(workspace / "project.json")
    if profile is None:
        return {"initialized": False, "path": str(root.resolve())}
    tasks = sorted(p.stem for p in (workspace / "tasks").glob("*.json")) if (workspace / "tasks").exists() else []
    return {"initialized": True, "name": profile["name"], "detected": profile["detected"], "tasks": tasks, "gates": json_read(workspace / "gates.json", {})}


def extend_project(root: Path, agent: str, name: str) -> dict[str, Any]:
    """Add a scoped project Skill without replacing existing user content."""
    if agent not in ROLES:
        raise ValueError(f"Unknown agent: {agent}")
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,63}", name):
        raise ValueError("Skill name must be lowercase kebab-case")
    root = root.resolve()
    workspace = root / ".teamkit"
    if not (workspace / "project.json").exists():
        raise FileNotFoundError("Project is not initialized")
    skill_dir = root / ".agents" / "skills" / name
    skill_file = skill_dir / "SKILL.md"
    created = not skill_file.exists()
    if created:
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(
            f"---\nname: {name}\ndescription: Project-specific {name} workflow for {agent}.\n---\n"
            f"# {name}\n\n## Scope\nDocument verified project-specific behaviors and paths.\n"
            "\n## Workflow\n1. Inspect the affected module and constraints.\n"
            "2. Follow project business invariants.\n3. Report evidence and unverified work.\n"
            "\n## Acceptance\nDefine real tests before marking this skill mature.\n",
            encoding="utf-8",
        )
    manifest = workspace / "extensions.json"
    data = json_read(manifest, {"agents": {}, "skills": []})
    active = data.setdefault("agents", {}).setdefault(agent, [])
    if name not in active:
        active.append(name)
        active.sort()
    skills = data.setdefault("skills", [])
    if name not in skills:
        skills.append(name)
        skills.sort()
    json_write(manifest, data)
    return {"agent": agent, "skill": name, "created": created, "path": str(skill_file), "status": "registered"}


def list_project_skills(root: Path) -> dict[str, Any]:
    project_skills = root.resolve() / ".agents" / "skills"
    found = sorted(p.parent.name for p in project_skills.glob("*/SKILL.md"))
    bundled = sorted(p.parent.name for p in (Path(__file__).resolve().parent / "assets" / "skills").glob("*/SKILL.md"))
    return {"bundled": bundled, "project": found, "extensions": json_read(root.resolve() / ".teamkit" / "extensions.json", {})}


def context_index(root: Path, module: str) -> dict[str, Any]:
    """Produce a narrow file index; don't inject arbitrary project source into prompts."""
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", module):
        raise ValueError("Invalid module identifier")
    index = json_read(root.resolve() / ".teamkit" / "index.json")
    if index is None:
        raise FileNotFoundError("Project index unavailable; run teamkit init")
    candidates = sorted(p for p in index["files"] if module.lower() in p.lower())
    return {"module": module, "matching_paths": candidates[:200], "truncated": len(candidates) > 200, "note": "Advisory file discovery only; inspect dependencies and invariants before code changes"}
