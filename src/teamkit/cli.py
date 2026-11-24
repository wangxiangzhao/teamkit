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
from .audit import audit_project, safe_maintain
from .live import attach, capability_report
from .native import probe_native
from .figma_contract import contract as figma_contract
from .skill_audit import audit_skills
from .privacy_audit import inspect_privacy
from .skill_resolver import resolve as resolve_project_skills
from .core import (ROUTES, check_project, checkpoint, context_index, extend_project, init_project, json_read, json_write, list_project_skills,
                   project_status, route_task, sync_project, task_plan)

ASSETS = Path(__file__).resolve().parent / "assets"


def install(home: Path, *, dry_run: bool = False, repair_legacy: bool = False) -> dict:
    """Install only missing bundled files, refusing symlinked destinations.

    Uses exclusive file creation so pre-existing user content is never replaced.
    Unmodified 0.1 role repairs are separately backed up.
    """
    import os
    source = ASSETS / "agents"
    home = home.expanduser().resolve()
    if not home.exists() and not dry_run:
        home.mkdir(parents=True)
    installed, skipped, repaired, warnings = [], [], [], []

    def safe_parent(parts):
        current = home
        for part in parts:
            current = current / part
            if current.is_symlink() or (current.exists() and not current.is_dir()):
                return None
            if not dry_run:
                current.mkdir(exist_ok=True)
        return current

    def create_exclusive(dest, content):
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(dest, flags, 0o644)
        except FileExistsError:
            return False
        with os.fdopen(fd, "wb") as out:
            out.write(content)
        return True

    def copy_missing(item, parts):
        parent = safe_parent(parts)
        dest = home.joinpath(*parts, item.name)
        if parent is None or dest.is_symlink():
            warnings.append(f"Unsafe symlink or non-directory destination: {dest}")
            skipped.append(str(dest))
            return
        if dest.exists():
            skipped.append(str(dest))
            return
        if dry_run or create_exclusive(dest, item.read_bytes()):
            installed.append(str(dest))
        else:
            skipped.append(str(dest))

    for item in sorted(source.glob("*.toml")):
        dest = home / ".codex" / "agents" / item.name
        if repair_legacy and dest.is_file() and not dest.is_symlink():
            bundled = item.read_bytes()
            prev = bundled[len(bundled.splitlines(keepends=True)[0]):] if bundled.startswith(b'name = "') else None
            if prev is not None and dest.read_bytes() == prev:
                backup_dir = safe_parent([".codex", "teamkit-backups", "agents"])
                backup = home / ".codex" / "teamkit-backups" / "agents" / item.name
                if backup_dir is None or backup.is_symlink():
                    warnings.append(f"Cannot safely back up legacy role: {dest}")
                    skipped.append(str(dest))
                    continue
                if backup.exists() and backup.read_bytes() != prev:
                    warnings.append(f"Backup conflict for legacy role: {dest}")
                    skipped.append(str(dest))
                    continue
                if not dry_run:
                    if not backup.exists() and not create_exclusive(backup, prev):
                        warnings.append(f"Unable to create backup: {backup}")
                        skipped.append(str(dest))
                        continue
                    # Avoid repairing when another process altered the role meanwhile.
                    if dest.read_bytes() != prev:
                        warnings.append(f"Legacy role changed during repair: {dest}")
                        skipped.append(str(dest))
                        continue
                    # write a unique temporary file and replace the recognized version.
                    temp = dest.with_name(dest.name + ".teamkit-upgrade")
                    if temp.exists() or temp.is_symlink():
                        warnings.append(f"Upgrade temp path exists: {temp}")
                        skipped.append(str(dest))
                        continue
                    if not create_exclusive(temp, bundled):
                        skipped.append(str(dest))
                        continue
                    os.replace(temp, dest)
                repaired.append(str(dest))
                continue
        copy_missing(item, [".codex", "agents"])
    for skill_dir in sorted((ASSETS / "skills").iterdir()):
        if not skill_dir.is_dir() or skill_dir.is_symlink():
            continue
        if not (skill_dir / "SKILL.md").is_file():
            continue
        # Include references and license notices in mature Skill bundles.
        # Preserve all existing user files and forbid symlink traversal.
        for source_file in sorted(skill_dir.rglob("*")):
            if not source_file.is_file() or source_file.is_symlink():
                continue
            relative = source_file.relative_to(skill_dir)
            parts = [".agents", "skills", skill_dir.name, *relative.parts[:-1]]
            parent = safe_parent(parts)
            dest = home.joinpath(*parts, relative.name)
            if parent is None or dest.is_symlink():
                warnings.append(f"Unsafe Skill destination: {dest}")
                skipped.append(str(dest))
            elif dest.exists():
                skipped.append(str(dest))
            elif dry_run or create_exclusive(dest, source_file.read_bytes()):
                installed.append(str(dest))
            else:
                skipped.append(str(dest))
    return {
        "status": "dry-run" if dry_run else ("partial" if warnings else "completed"),
        "installed": installed, "repaired_legacy_roles": repaired,
        "skipped_existing": skipped, "warnings": warnings,
        "note": "No overwrite of customized files or Codex config, model, approvals or credentials.",
    }

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
    aud = subs.add_parser("audit", help="Read-only self-check of project integration")
    aud.add_argument("--project", type=Path, default=Path.cwd())
    maintain = subs.add_parser("maintain", help="Safe automatic upkeep of owned project metadata")
    maintain.add_argument("--project", type=Path, default=Path.cwd())
    hot = subs.add_parser("attach", help="Prepare or queue live-session TeamKit instructions without restarting Codex")
    hot.add_argument("--project", type=Path, default=Path.cwd())
    hot.add_argument("--session", help="Existing Codex session UUID or exact name")
    hot.add_argument("--approve-queue", action="store_true")
    caps = subs.add_parser("capabilities", help="Audit installed Agent and Skill files, without claiming runtime activation")
    caps.add_argument("--project", type=Path, default=Path.cwd())
    caps.add_argument("--home", type=Path)
    resolve = subs.add_parser("resolve-skills", help="Report available vs missing professional Skills")
    resolve.add_argument("--project", type=Path, default=Path.cwd())
    native = subs.add_parser("verify-native", help="Probe Codex/Xcode/Swift CLI availability without changing anything")
    native.add_argument("--skip-simulator", action="store_true")
    figma = subs.add_parser("figma-contract", help="Extract a bounded design contract from Figma node JSON")
    figma.add_argument("json_file", type=Path)
    figma.add_argument("--module", required=True)
    figma.add_argument("--project", type=Path)
    figma.add_argument("--write", action="store_true")
    skillaudit = subs.add_parser("audit-skills", help="Inspect installed Skill metadata, references and provenance")
    skillaudit.add_argument("--project", type=Path, default=Path.cwd())
    privacy = subs.add_parser("privacy", help="Non-destructive iOS Info.plist and privacy-manifest preflight")
    privacy.add_argument("--project", type=Path, default=Path.cwd())
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
            # Single entrypoint: auto-install missing *bundled* capabilities without
            # touching existing Codex settings, credentials or customized Skills.
            # This is performed only after successful project preflight/adaptation.
            if result["status"] in {"ready", "dry-run"}:
                result["global_install"] = install(Path.home(), dry_run=args.dry_run, repair_legacy=True)
                if not args.dry_run:
                    result["capabilities"] = capability_report(args.project)
                    result["agent_skill_map"] = resolve_project_skills(args.project, persist=True)
                    result["skill_audit"] = audit_skills(args.project)
                    result["existing_codex_session"] = {
                        "restart_required": False,
                        "new_agent_hot_registration_verified": False,
                        "instruction": attach(args.project)["prompt"],
                        "note": "When invoked by an active Codex session, process this instruction in that session; external shells cannot inject into an existing interactive session.",
                    }
        elif args.command == "detach":
            result = detach(args.project, dry_run=args.dry_run)
        elif args.command == "audit":
            result = audit_project(args.project)
        elif args.command == "maintain":
            result = safe_maintain(args.project)
        elif args.command == "attach":
            result = attach(args.project, session=args.session, approve_queue=args.approve_queue)
        elif args.command == "capabilities":
            result = capability_report(args.project, home=args.home)
        elif args.command == "resolve-skills":
            result = resolve_project_skills(args.project)
        elif args.command == "verify-native":
            result = probe_native(skip_simulator=args.skip_simulator)
        elif args.command == "figma-contract":
            result = figma_contract(args.json_file, module=args.module, project=args.project, write=args.write)
        elif args.command == "audit-skills":
            result = audit_skills(args.project)
        elif args.command == "privacy":
            result = inspect_privacy(args.project)
        elif args.command == "resume":
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.task_id):
                raise ValueError("Invalid task ID")
            result = json_read(args.project.resolve() / ".teamkit" / "tasks" / (args.task_id + ".json"))
            if result is None:
                raise FileNotFoundError("Task checkpoint not found")
        else:
            raise ValueError("Unknown command")
        if args.command == "onboard" and result.get("status") == "ready":
            # Keep full evidence locally; don't flood Codex context with huge
            # installed-file lists, simulator inventory, and every role matrix.
            full = result
            report = args.project.resolve() / ".teamkit" / "reports" / "onboard.json"
            json_write(report, full)
            caps = full.get("capabilities", {})
            session = full.get("existing_codex_session", {})
            install_summary = full.get("global_install", {})
            result = {
                "status": "ready", "project": full.get("project"),
                "capabilities": {
                    "configured_roles": caps.get("configured_roles"),
                    "discovered_skill_count": caps.get("discovered_skill_count"),
                },
                "global_install": {
                    "status": install_summary.get("status"),
                    "installed_count": len(install_summary.get("installed", [])),
                    "skipped_existing_count": len(install_summary.get("skipped_existing", [])),
                    "warnings": install_summary.get("warnings", [])[:5],
                },
                "existing_codex_session": {
                    "restart_required": False,
                    "new_agent_hot_registration_verified": False,
                    "instruction": "Continue this Codex task; read AGENTS.md TeamKit section and .teamkit/reports/onboard.json as needed. Preserve existing context and settings.",
                },
                "self_audit_status": full.get("self_audit", {}).get("status"),
                "skill_audit_status": full.get("skill_audit", {}).get("status"),
                "full_report": str(report),
                "notice": "Connected tools are not equivalent to live authenticated agent/Figma verification.",
            }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("status") in {"failed", "blocked"} else 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
