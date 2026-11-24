"""Attach current Codex sessions without restarting; explicit queue is opt-in.

The CLI cannot alter the already-loaded instruction snapshot or retroactively
register child-agent profiles inside an existing process.
"""
from __future__ import annotations
import re
import shutil
import subprocess
from pathlib import Path

from .core import json_read, ROLES
from .skill_sources import candidates

SESSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9_:\-.]{0,127}\Z")

def _project(root: Path) -> Path:
    project=root.resolve()
    if not (project/'.teamkit/project.json').is_file():
        raise FileNotFoundError("Project not initialized: run teamkit onboard from a separate terminal or inside Codex")
    return project

def attach_instruction(project: Path) -> str:
    project=_project(project)
    return (
        "在当前 Codex 会话继续原有任务，不退出、不清空上下文、不改变模型或授权。"
        f"请读取项目 {project}/AGENTS.md 中现有项目规范以及 TeamKit 区块，"
        f"读取 {project}/.teamkit/project.json 与按需相关的模块上下文。"
        "现有项目约束优先；仅按需使用当前会话已可用的 Skills 与原生子 Agent。"
        "如果当前进程无法识别新 Agent 配置，则直接执行任务，不要谎称已激活或要求重启。"
        "先简要报告实际可用的 Agent/Skills，再继续正在执行的工作。"
    )

def attach(project: Path, *, session: str | None = None, approve_queue: bool = False) -> dict:
    prompt=attach_instruction(project)
    if not session:
        return {"status":"instruction-ready","delivery":"send the prompt in the existing Codex chat",
                "prompt":prompt,"restart_required":False,
                "new_role_reload_guaranteed":False}
    if not SESSION.fullmatch(session):
        raise ValueError("Invalid Codex session identifier")
    if not approve_queue:
        return {"status":"dry-run","session":session,"requires":"--approve-queue",
                "prompt":prompt,"restart_required":False}
    codex=shutil.which('codex')
    if not codex:
        return {"status":"blocked","reason":"codex CLI unavailable"}
    try:
        result=subprocess.run([codex,'queue',session,prompt],cwd=project.resolve(),
                              capture_output=True,text=True,timeout=20,check=False,shell=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        return {"status":"blocked","reason":str(exc)}
    return {"status":"queued" if result.returncode==0 else "failed","exit_code":result.returncode,
            "session":session,"stdout_tail":result.stdout[-1000:],
            "stderr_tail":result.stderr[-1000:],
            "notice":"Queue acceptance does not prove agent/skill reload or task completion"}

def capability_report(project: Path, *, home: Path | None = None) -> dict:
    """Report actual file presence separately from unverified runtime execution."""
    project=project.resolve()
    user=(home or Path.home()).expanduser().resolve()
    local_agents=project/'.codex/agents'
    global_agents=user/'.codex/agents'
    all_agents={}
    for role in ROLES:
        paths=[local_agents/f'{role}.toml',global_agents/f'{role}.toml']
        found=next((p for p in paths if p.is_file() and not p.is_symlink()),None)
        all_agents[role]={"configured":bool(found),"path":str(found) if found else None,
                          "runtime_verified":False}
    skill_paths=[
        user/'.agents/skills',user/'.codex/skills',
        project/'.agents/skills',project/'.codex/skills'
    ]
    skills={}
    for base in skill_paths:
        if not base.is_dir() or base.is_symlink():
            continue
        for p in sorted(base.glob('*/SKILL.md')):
            if not p.is_symlink():
                skills.setdefault(p.parent.name,str(p))
    bundled=Path(__file__).resolve().parent/'assets/skills'
    bundled_names=sorted(p.parent.name for p in bundled.glob('*/SKILL.md'))
    missing_roles=[n for n,v in all_agents.items() if not v['configured']]
    # No external candidates are assumed installed or tested.
    return {"status":"partial" if missing_roles else "configured",
        "configured_roles":sum(x['configured'] for x in all_agents.values()),
        "expected_roles":len(ROLES),"roles":all_agents,
        "discovered_skill_count":len(skills),"discovered_skills":skills,
        "bundled_skill_count":len(bundled_names),"bundled_skills":bundled_names,
        "mature_external_skills_installed_and_tested":None,
        "native_agent_dispatch_verified":False,"project_autoadaptation_verified":False,
        "real_xcode_figma_integrations_verified":False,
        "note":"Presence is not proof of activation. Current Codex session capabilities cannot be inferred from disk files."}
