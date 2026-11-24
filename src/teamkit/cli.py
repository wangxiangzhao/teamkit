"""Command line entry point. Human-facing outputs are machine-readable JSON."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from . import __version__
from .core import (ROUTES, check_project, checkpoint, context_index, extend_project, init_project, json_read, list_project_skills,
                   project_status, route_task, sync_project, task_plan)

ASSETS = Path(__file__).resolve().parent / "assets"


def install(home: Path, *, dry_run: bool = False) -> dict:
    """Install only TeamKit-owned files; never overwrite user customizations."""
    source = ASSETS / "agents"
    target = home.expanduser().resolve() / ".codex" / "agents"
    installed, skipped = [], []
    for item in sorted(source.glob("*.toml")):
        dest = target / item.name
        if dest.exists():
            skipped.append(str(dest))
            continue
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, dest)
        installed.append(str(dest))
    for skill_file in sorted((ASSETS / "skills").glob("*/SKILL.md")):
        dest = home.expanduser().resolve() / ".agents" / "skills" / skill_file.parent.name / "SKILL.md"
        if dest.exists():
            skipped.append(str(dest))
            continue
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(skill_file, dest)
        installed.append(str(dest))
    return {"status": "dry-run" if dry_run else "completed", "installed": installed, "skipped_existing": skipped, "warning": "Does not modify ~/.codex/config.toml, credentials, or global AGENTS.md. Verify Codex version and agent support separately."}


def doctor() -> dict:
    return {"teamkit_version": __version__, "python": sys.version.split()[0], "tools": {s: shutil.which(s) for s in ("git", "codex", "xcodebuild", "xcrun", "swift", "rg")}, "note": "Tool presence is not proof of runtime capability. macOS/Xcode integrations require separate validation."}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="teamkit", description="Local-first Codex project toolkit")
    p.add_argument("--version", action="version", version=__version__)
    subs = p.add_subparsers(dest="command", required=True)
    inst = subs.add_parser("install", help="Safely copy missing Agent TOML files")
    inst.add_argument("--home", type=Path, default=Path.home())
    inst.add_argument("--dry-run", action="store_true")
    subs.add_parser("doctor", help="Inspect local tool availability")
    for name in ("init", "sync", "status", "check"):
        s = subs.add_parser(name)
        s.add_argument("--project", type=Path, default=Path.cwd())
        if name == "init":
            s.add_argument("--force", action="store_true", help="Regenerate TeamKit metadata (backs up nothing; avoid on customized projects)")
    route = subs.add_parser("route", help="Return advisory role selection (not autonomous model dispatch)")
    route.add_argument("description")
    route.add_argument("--intent", choices=sorted(ROUTES), default=None)
    route.add_argument("--project", type=Path)
    plan = subs.add_parser("plan", help="Produce a conservative task dependency plan")
    plan.add_argument("description")
    plan.add_argument("--intent", choices=sorted(ROUTES))
    cp = subs.add_parser("checkpoint", help="Save resumable task state")
    cp.add_argument("task_id")
    cp.add_argument("state", choices=["planned", "running", "blocked", "failed", "completed"])
    cp.add_argument("--note", default="")
    cp.add_argument("--project", type=Path, default=Path.cwd())
    resume = subs.add_parser("resume", help="Read a task checkpoint; does not resume Codex processes")
    resume.add_argument("task_id")
    resume.add_argument("--project", type=Path, default=Path.cwd())
    ext = subs.add_parser("extend", help="Safely add project-scoped Skill to an Agent")
    ext.add_argument("agent")
    ext.add_argument("skill")
    ext.add_argument("--project", type=Path, default=Path.cwd())
    sk = subs.add_parser("skills", help="List bundled and project Skills")
    sk.add_argument("--project", type=Path, default=Path.cwd())
    ctx = subs.add_parser("context", help="Return candidate files for a project module")
    ctx.add_argument("module")
    ctx.add_argument("--project", type=Path, default=Path.cwd())
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "install":
            result = install(args.home, dry_run=args.dry_run)
        elif args.command == "doctor":
            result = doctor()
        elif args.command == "init":
            result = init_project(args.project, force=args.force)
        elif args.command == "sync":
            result = sync_project(args.project)
        elif args.command == "status":
            result = project_status(args.project)
        elif args.command == "check":
            result = check_project(args.project)
        elif args.command == "route":
            result = route_task(args.description, explicit_intent=args.intent, project=args.project)
        elif args.command == "plan":
            result = task_plan(route_task(args.description, explicit_intent=args.intent))
        elif args.command == "checkpoint":
            result = checkpoint(args.project, args.task_id, args.state, args.note)
        elif args.command == "extend":
            result = extend_project(args.project, args.agent, args.skill)
        elif args.command == "skills":
            result = list_project_skills(args.project)
        elif args.command == "context":
            result = context_index(args.project, args.module)
        elif args.command == "resume":
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.task_id):
                raise ValueError("Invalid task ID")
            result = json_read(args.project.resolve() / ".teamkit" / "tasks" / (args.task_id + ".json"))
            if result is None:
                raise FileNotFoundError("Task checkpoint not found")
        else:
            raise ValueError("Unknown command")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("status") == "failed" else 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
