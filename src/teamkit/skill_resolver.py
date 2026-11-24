"""Installed Skill discovery, conservative capability resolution, and explicit gaps.

Skills are read as metadata only; third-party scripts are never executed here.
Project Skill entries shadow global entries. A path being present does NOT
prove capability maturity, tool access, license compliance or runtime activation.
"""
from __future__ import annotations
import re
from pathlib import Path
from .core import ROLES, json_write, json_read

ROLE_SKILLS = {
    "product": ["project-adaptation"],
    "design": ["figma-contract", "quality-gates"],
    "ios_engineer": ["ios-delivery", "swiftui-pro", "token-efficiency", "figma-contract"],
    "backend_engineer": ["project-adaptation"],
    "quality": ["quality-gates", "token-efficiency"],
    "compliance": ["quality-gates"],
    "growth": ["analytics-roas"],
    "analytics": ["analytics-roas"],
}
GAPS = {
    "product": ["market research and business specifications"],
    "design": ["production Figma MCP extraction and transition reviews"],
    "ios_engineer": ["real Xcode build, native gesture, performance profiling"],
    "backend_engineer": ["backend API and ETL production verification"],
    "quality": ["XCTest/XCUITest and independent visual regression"],
    "compliance": ["App Store/privacy current guidance verification"],
    "growth": ["ad mediation/MMP/StoreKit live reporting"],
    "analytics": ["event dictionary and production data reconciliation"],
}
NAME = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{1,63}\Z")

def _read_name(path: Path) -> str | None:
    try:
        if path.stat().st_size > 256 * 1024:
            return None
        with path.open(encoding="utf-8") as f:
            first=f.readline()
            if first.strip() != "---":
                return None
            for i, line in enumerate(f):
                if i > 60 or line.strip() == "---":
                    break
                if line.startswith("name:"):
                    name=line.partition(":")[2].strip().strip("'\"")
                    return name if NAME.fullmatch(name) else None
    except (OSError, UnicodeError):
        return None
    return None

def resolve(project: Path, *, home: Path | None = None, persist: bool = False) -> dict:
    root=project.resolve()
    user=(home or Path.home()).expanduser().resolve()
    directories=[
        (root / ".agents/skills", "project"),
        (root / ".codex/skills", "project"),
        (user / ".agents/skills", "global"),
        (user / ".codex/skills", "global"),
    ]
    available={}
    warnings=[]
    for folder, scope in directories:
        if not folder.is_dir() or folder.is_symlink():
            continue
        for entry in sorted(folder.iterdir()):
            skill=entry/"SKILL.md"
            if not entry.is_dir() or entry.is_symlink() or not skill.is_file() or skill.is_symlink():
                continue
            name=_read_name(skill)
            if name is None:
                warnings.append(f"Invalid Skill metadata: {skill}")
                continue
            if name != entry.name:
                warnings.append(f"Skill name/directory mismatch: {skill}")
                continue
            available.setdefault(name,{"path":str(skill),"scope":scope,
                                        "verified":False,"provenance":"filesystem"})
    extensions = json_read(root / ".teamkit/extensions.json", {})
    registered = extensions.get("agents", {})
    agents={}
    for role in ROLES:
        extra = registered.get(role, [])
        if not isinstance(extra, list) or any(not isinstance(x, str) or not NAME.fullmatch(x) for x in extra):
            warnings.append(f"Invalid project skill mapping: {role}")
            extra = []
        expected=list(dict.fromkeys(ROLE_SKILLS[role] + extra))
        agents[role]={
            "available_skills":[{"name":k, **available[k]} for k in expected if k in available],
            "missing_skills":[k for k in expected if k not in available],
            "unverified_expertise":GAPS[role],
            "runtime_verified":False,
            "project_extensions":extra,
        }
    report={"schema_version":1,"project":str(root),"skills_found":len(available),
            "agents":agents,"warnings":warnings,
            "note":"Skills are installed files; external maturity and runtime loading remain unverified."}
    if persist:
        base=root/".teamkit"
        if not (base/"project.json").is_file():
            raise FileNotFoundError("Run teamkit onboard first")
        json_write(base/"skill-map.json",report)
    return report


def resolve_task(project: Path, route: dict, *, home: Path | None = None) -> dict:
    """Resolve only route-required skills and registered role extensions."""
    mapping = resolve(project, home=home)
    roles = list(dict.fromkeys([route["primary_agent"], *route.get("optional_agents", [])]))
    requested = set(route.get("skills", []))
    selected = {}
    for role in roles:
        entry = mapping["agents"][role]
        wanted = requested | set(entry["project_extensions"])
        selected[role] = {
            "skills": [item for item in entry["available_skills"] if item["name"] in wanted],
            "missing": [name for name in entry["missing_skills"] if name in wanted],
        }
    return {"roles":selected,"runtime_verified":False,
            "note":"Read only relevant skill instructions; existing project rules override them."}
