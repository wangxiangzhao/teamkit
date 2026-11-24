"""Structural Skill audit with reference, manifest, and provenance checks.

Static review cannot prove model behavior, runtime tool access, or permission
to execute a third-party skill's scripts. No scripts are ever run here.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

REF = re.compile(r"references/([A-Za-z0-9_.-]+\.md)")

def _folder_audit(root: Path) -> dict:
    skill = root / "SKILL.md"
    if root.is_symlink() or skill.is_symlink():
        return {"name":root.name,"status":"failed","errors":["symlinked skill"]}
    errors = []
    try:
        if skill.stat().st_size > 256 * 1024:
            errors.append("SKILL.md too large")
        text = skill.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return {"name":root.name,"status":"failed","errors":["unreadable SKILL.md"]}
    if not text.startswith("---\n") or "\n---" not in text[4:]:
        errors.append("invalid frontmatter")
    if f"name: {root.name}" not in text:
        errors.append("name mismatch")
    if not re.search(r"(?m)^description:\s*\S+", text):
        errors.append("missing description")
    refs = sorted(set(REF.findall(text)))
    for name in refs:
        target = root / "references" / name
        if target.is_symlink() or not target.is_file():
            errors.append(f"missing reference {name}")
    manifest = root / "UPSTREAM.json"
    if manifest.is_file():
        try:
            upstream = json.loads(manifest.read_text(encoding="utf-8"))
            if not (root / "LICENSE").is_file():
                errors.append("vendored skill lacks license notice")
            if not re.fullmatch(r"[0-9a-f]{40}", str(upstream.get("commit",""))):
                errors.append("vendored skill lacks pinned commit")
        except (ValueError, OSError, TypeError):
            errors.append("invalid upstream provenance")
    return {"name":root.name,"status":"passed" if not errors else "failed",
            "errors":errors,"references_checked":len(refs),"runtime_verified":False}


def audit_skills(project: Path, *, home: Path | None = None) -> dict:
    root=project.resolve()
    user=(home or Path.home()).expanduser().resolve()
    locations=[user/".agents/skills",user/".codex/skills",
               root/".agents/skills",root/".codex/skills"]
    seen={}
    for folder in locations[::-1]:
        if not folder.is_dir() or folder.is_symlink():
            continue
        for skill in sorted(folder.iterdir()):
            if skill.is_dir() and (skill/"SKILL.md").exists():
                seen[skill.name]=skill
    reports=[_folder_audit(path) for _,path in sorted(seen.items())]
    errors=[{"skill":r["name"],"errors":r["errors"]} for r in reports if r["errors"]]
    return {"status":"passed" if not errors else "partial",
            "skills_checked":len(reports),"reports":reports,"errors":errors,
            "review_scope":"manifest, local references, attribution only",
            "model_skill_effectiveness_verified":False}
