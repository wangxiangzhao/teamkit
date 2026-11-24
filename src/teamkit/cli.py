"""Command line entry point. Human-facing outputs are machine-readable JSON."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from . import __version__
from .orchestration import create_plan, ready_nodes, update_node, summarize_plan
from .context_engine import compile_context, discover_modules, impact
from .quality import scan_assets, run_gate, check_release
from .metrics import record as record_metrics, summary as metrics_summary, roas_csv
from .dispatch import run as dispatch_run
from .skill_sources import candidates
from .activation import activate, deactivate
from .visual import compare_images, optimize_image
from .onboarding import onboard, detach
from .skill_sources import candidates
from .core import (ROUTES, check_project, checkpoint, context_index, extend_project, init_project, json_read, list_project_skills,
                   project_status, route_task, sync_project, task_plan)

ASSETS = Path(__file__).resolve().parent / "assets"


def install(home: Path, *, dry_run: bool = False, repair_legacy: bool = False) -> dict:
    """Install only TeamKit-owned files; never overwrite user customizations."""
    source = ASSETS / "agents"
    target = home.expanduser().resolve() / ".codex" / "agents"
    installed, skipped, repaired = [], [], []
    for item in sorted(source.glob("*.toml")):
        dest = target / item.name
        if dest.exists():
            existing = dest.read_text(encoding="utf-8") if dest.is_file() and not dest.is_symlink() else None
            bundled = item.read_text(encoding="utf-8")
            previous = bundled.split("\n", 1)[1] if bundled.startswith('name = "') else None
            if repair_legacy and existing is not None and previous is not None and existing == previous:
                backup = home.expanduser().resolve() / ".codex" / "teamkit-backups" / "agents" / item.name
                if backup.exists():
                    skipped.append(str(dest))
                    continue
                if not dry_run:
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    backup.write_text(existing, encoding="utf-8")
                    dest.write_text(bundled, encoding="utf-8")
                repaired.append(str(dest))
                continue
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
    return {"status": "dry-run" if dry_run else "completed", "installed": installed, "repaired_legacy_roles": repaired, "skipped_existing": skipped, "warning": "Does not modify ~/.codex/config.toml, credentials, or global AGENTS.md. Verify Codex version and agent support separately."}


def doctor() -> dict:
    return {"teamkit_version": __version__, "python": sys.version.split()[0], "tools": {s: shutil.which(s) for s in ("git", "codex", "xcodebuild", "xcrun", "swift", "rg")}, "note": "Tool presence is not proof of runtime capability. macOS/Xcode integrations require separate validation."}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="teamkit", description="Local-first Codex project toolkit")
    p.add_argument("--version", action="version", version=__version__)
    subs = p.add_subparsers(dest="command", required=True)
    inst = subs.add_parser("install", help="Safely copy missing Agent TOML files")
    inst.add_argument("--home", type=Path, default=Path.home())
    inst.add_argument("--dry-run", action="store_true")
    inst.add_argument("--repair-legacy-roles", action="store_true", help="Back up and repair unmodified v0.1 roles")
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
    cand = subs.add_parser("candidates", help="Read-only mature Skill candidates")
    cand.add_argument("--capability")
    mods = subs.add_parser("modules", help="Discover path-derived modules")
    mods.add_argument("--project", type=Path, default=Path.cwd())
    context = subs.add_parser("compile-context", help="Create bounded module context")
    context.add_argument("module")
    context.add_argument("--project", type=Path, default=Path.cwd())
    imp = subs.add_parser("impact", help="Identify changed files and affected modules")
    imp.add_argument("--project", type=Path, default=Path.cwd())
    assets = subs.add_parser("assets", help="Scan image size and duplicate bytes")
    assets.add_argument("--project", type=Path, default=Path.cwd())
    assets.add_argument("--max-bytes", type=int, default=1024*1024)
    gate = subs.add_parser("gate", help="Run explicitly approved build/test command")
    gate.add_argument("gate", choices=["build","test"])
    gate.add_argument("--project", type=Path, default=Path.cwd())
    gate.add_argument("--approve-command", action="store_true")
    gate.add_argument("--timeout", type=int, default=180)
    rel = subs.add_parser("release", help="Conservative release readiness report")
    rel.add_argument("--project", type=Path, default=Path.cwd())
    dag = subs.add_parser("dag", help="Persistent task DAG and transitions")
    dag.add_argument("action", choices=["create","ready","status","update"])
    dag.add_argument("task_id")
    dag.add_argument("description", nargs="?")
    dag.add_argument("--project", type=Path, default=Path.cwd())
    dag.add_argument("--node")
    dag.add_argument("--state")
    dag.add_argument("--evidence", action="append", default=[])
    dag.add_argument("--path", action="append", default=[])
    dag.add_argument("--intent", choices=sorted(ROUTES))
    dag.add_argument("--max-concurrency", type=int, default=2)
    metrics = subs.add_parser("metrics", help="Record or report measured usage")
    metrics.add_argument("--project", type=Path, default=Path.cwd())
    metrics.add_argument("--task-id")
    metrics.add_argument("--input-tokens", type=int)
    metrics.add_argument("--output-tokens", type=int)
    metrics.add_argument("--cached-tokens", type=int)
    metrics.add_argument("--duration-seconds", type=float)
    metrics.add_argument("--outcome", default="unknown")
    roas = subs.add_parser("roas", help="Calculate ROAS for complete cohorts in CSV")
    roas.add_argument("csv", type=Path)
    roas.add_argument("--window", type=int, default=30)
    run = subs.add_parser("run", help="Opt-in Codex execution, dry-run by default")
    run.add_argument("description")
    run.add_argument("--project", type=Path, default=Path.cwd())
    run.add_argument("--module")
    run.add_argument("--intent", choices=sorted(ROUTES))
    run.add_argument("--approve-execution", action="store_true")
    run.add_argument("--timeout", type=int, default=3600)
    on = subs.add_parser("activate", help="Opt-in project Master instructions")
    on.add_argument("--project", type=Path, default=Path.cwd())
    on.add_argument("--approve", action="store_true")
    off = subs.add_parser("deactivate", help="Remove TeamKit instructions only")
    off.add_argument("--project", type=Path, default=Path.cwd())
    off.add_argument("--approve", action="store_true")
    visual = subs.add_parser("visual", help="Compare two screenshots by pixel difference")
    visual.add_argument("reference", type=Path)
    visual.add_argument("actual", type=Path)
    visual.add_argument("--tolerance", type=float, default=0.02)
    opt = subs.add_parser("optimize-image", help="Non-destructive image optimization")
    opt.add_argument("source", type=Path)
    opt.add_argument("output", type=Path)
    opt.add_argument("--quality", type=int, default=85)
    opt.add_argument("--approve", action="store_true")
    bootstrap = subs.add_parser("onboard", help="One-command safe existing-project adaptation")
    bootstrap.add_argument("--project", type=Path, default=Path.cwd())
    bootstrap.add_argument("--dry-run", action="store_true")
    detached = subs.add_parser("detach", help="Remove only TeamKit's AGENTS instructions")
    detached.add_argument("--project", type=Path, default=Path.cwd())
    detached.add_argument("--dry-run", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "install":
            result = install(args.home, dry_run=args.dry_run, repair_legacy=args.repair_legacy_roles)
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
        elif args.command == "candidates":
            result = candidates(args.capability)
        elif args.command == "modules":
            result = discover_modules(args.project)
        elif args.command == "compile-context":
            result = compile_context(args.project, args.module)
        elif args.command == "impact":
            result = impact(args.project)
        elif args.command == "assets":
            result = scan_assets(args.project, max_bytes=args.max_bytes)
        elif args.command == "gate":
            result = run_gate(args.project, args.gate, timeout=args.timeout, approve_command=args.approve_command)
        elif args.command == "release":
            result = check_release(args.project)
        elif args.command == "dag":
            if args.action == "create":
                if not args.description:
                    raise ValueError("dag create requires description")
                result = create_plan(args.project, args.task_id, args.description, intent=args.intent)
            elif args.action == "ready":
                result = ready_nodes(args.project, args.task_id, max_running=args.max_concurrency)
            elif args.action == "status":
                result = summarize_plan(args.project, args.task_id)
            else:
                if not args.node or not args.state:
                    raise ValueError("dag update requires --node and --state")
                result = update_node(args.project, args.task_id, args.node, args.state,
                                     paths=args.path or None, evidence=args.evidence)
        elif args.command == "metrics":
            result = record_metrics(args.project, args.task_id, input_tokens=args.input_tokens,
                                    output_tokens=args.output_tokens, cached_tokens=args.cached_tokens,
                                    duration_seconds=args.duration_seconds, outcome=args.outcome) if args.task_id else metrics_summary(args.project)
        elif args.command == "roas":
            result = roas_csv(args.csv, window=args.window)
        elif args.command == "run":
            result = dispatch_run(args.project, args.description, approve=args.approve_execution,
                                  timeout=args.timeout, module=args.module, intent=args.intent)
        elif args.command == "activate":
            result = activate(args.project, approve=args.approve)
        elif args.command == "deactivate":
            result = deactivate(args.project, approve=args.approve)
        elif args.command == "visual":
            result = compare_images(args.reference, args.actual, tolerance=args.tolerance)
        elif args.command == "optimize-image":
            result = optimize_image(args.source, args.output, quality=args.quality, approve=args.approve)
        elif args.command == "onboard":
            result = onboard(args.project, dry_run=args.dry_run)
        elif args.command == "detach":
            result = detach(args.project, dry_run=args.dry_run)
        elif args.command == "resume":
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.task_id):
                raise ValueError("Invalid task ID")
            result = json_read(args.project.resolve() / ".teamkit" / "tasks" / (args.task_id + ".json"))
            if result is None:
                raise FileNotFoundError("Task checkpoint not found")
        else:
            raise ValueError("Unknown command")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("status") in {"failed", "blocked"} else 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
