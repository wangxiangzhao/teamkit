"""Persistent deterministic DAG scheduling. Codex Master owns real model dispatch."""
from __future__ import annotations
import re
import hashlib
import fcntl
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any
from .core import json_read, json_write, now, route_task

STATES = {"pending", "ready", "running", "completed", "failed", "blocked", "skipped"}
ALLOWED = {
    "pending": {"ready", "blocked", "skipped"},
    "ready": {"running", "blocked", "skipped"},
    "running": {"completed", "failed", "blocked"},
    "failed": {"ready", "blocked"},
    "blocked": {"ready", "skipped"},
    "completed": set(), "skipped": set(),
}
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


def _storage(project: Path, task_id: str) -> Path:
    if not NAME.fullmatch(task_id):
        raise ValueError("Invalid task ID")
    base = project.resolve() / ".teamkit"
    if not (base / "project.json").exists():
        raise FileNotFoundError("Initialize project first")
    path = base / "plans" / f"{task_id}.json"
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError("Unsafe plan storage")
    return path


def _validate(nodes: list[dict]) -> None:
    keys = [n["id"] for n in nodes]
    if len(keys) != len(set(keys)) or not all(NAME.fullmatch(k) for k in keys):
        raise ValueError("Invalid or duplicate node IDs")
    graph = {n["id"]: n.get("depends_on", []) for n in nodes}
    for key, deps in graph.items():
        if key in deps or any(dep not in graph for dep in deps):
            raise ValueError(f"Invalid dependency for {key}")
    temporary, permanent = set(), set()
    def visit(k):
        if k in temporary:
            raise ValueError("Cyclic dependency")
        if k not in permanent:
            temporary.add(k)
            for dep in graph[k]:
                visit(dep)
            temporary.remove(k)
            permanent.add(k)
    for k in graph:
        visit(k)


@contextmanager
def _project_lock(project: Path):
    base = project.resolve() / ".teamkit"
    if base.is_symlink() or not (base / "project.json").is_file():
        raise ValueError("Unsafe or uninitialized project metadata")
    lock = base / "scheduler.lock"
    import os
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "rb+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _serialized(fn):
    @wraps(fn)
    def wrapped(project, *args, **kwargs):
        with _project_lock(project):
            return fn(project, *args, **kwargs)
    return wrapped


def _running(project: Path, excluding_task: str, excluding_node: str = "") -> list:
    base = project.resolve() / ".teamkit/plans"
    if base.is_symlink():
        raise ValueError("Unsafe plan directory")
    out = []
    for file in sorted(base.glob("*.json")):
        if file.is_symlink():
            raise ValueError("Unsafe plan file")
        plan = json_read(file)
        for node in plan["nodes"]:
            if node["status"] == "running" and not (plan["task_id"] == excluding_task and node["id"] == excluding_node):
                out.append(node)
    return out


def _evidence(project: Path, references: list[str]) -> list[dict]:
    root = project.resolve()
    result = []
    for ref in references:
        path = root / ref
        if Path(ref).is_absolute() or ".." in Path(ref).parts or not path.resolve().is_relative_to(root) or path.is_symlink() or not path.is_file():
            raise ValueError("Evidence must be an existing local project file: " + ref)
        from .core import _fingerprint
        result.append({"path": ref, "sha256": _fingerprint(path)})
    return result


@_serialized
def create_plan(project: Path, task_id: str, description: str, *, intent: str | None = None) -> dict:
    path = _storage(project, task_id)
    if path.exists():
        raise FileExistsError("Plan already exists; do not silently replace progress")
    route = route_task(description, explicit_intent=intent, project=project)
    nodes = []
    if route["intent"] == "ui_module":
        nodes.append({"id": "design", "agent": "design", "depends_on": [], "paths": [], "mode": "design_contract"})
    deps = ["design"] if nodes else []
    nodes.append({"id": "implement", "agent": route["primary_agent"], "depends_on": deps, "paths": [], "mode": "execution"})
    if "quality" in route["optional_agents"]:
        nodes.append({"id": "review", "agent": "quality", "depends_on": ["implement"], "paths": [], "mode": "independent_review"})
    _validate(nodes)
    for node in nodes:
        node.update(status="pending", attempts=0, evidence=[], updated_at=now())
    plan = {"schema_version": 1, "task_id": task_id, "task": description, "route": route, "nodes": nodes, "created_at": now(), "dispatch": "advisory; Master invokes native Codex agents", "source_version": None}
    json_write(path, plan)
    return plan


def get_plan(project: Path, task_id: str) -> dict:
    path = _storage(project, task_id)
    plan = json_read(path)
    if plan is None:
        raise FileNotFoundError(f"Plan {task_id} does not exist")
    _validate(plan["nodes"])
    return plan


def _conflict(a: list[str], b: list[str]) -> bool:
    def overlap(x, y):
        x, y = x.strip("/"), y.strip("/")
        return x == y or x.startswith(y + "/") or y.startswith(x + "/")
    # Unknown write scope is exclusive, not permission to overlap.
    return not a or not b or any(overlap(x, y) for x in a for y in b)


def ready_nodes(project: Path, task_id: str, max_running: int = 2) -> dict:
    if max_running < 1 or max_running > 4:
        raise ValueError("concurrency must be within 1..4")
    plan = get_plan(project, task_id)
    nodes = plan["nodes"]
    by_id = {n["id"]: n for n in nodes}
    active = _running(project, task_id)
    capacity = max(0, max_running - len(active))
    ready = []
    for n in nodes:
        if n["status"] not in {"pending", "ready"} and not (n["status"] == "failed" and n.get("retry_eligible")):
            continue
        if not all(by_id[k]["status"] == "completed" for k in n["depends_on"]):
            continue
        if any(_conflict(n.get("paths", []), other.get("paths", [])) for other in active + ready):
            continue
        if len(ready) >= capacity:
            break
        ready.append(n)
    return {"task_id": task_id, "ready": [{"id": n["id"], "agent": n["agent"], "mode": n["mode"], "paths": n["paths"]} for n in ready], "running": len(active), "slots": capacity, "advisory": True}


@_serialized
def update_node(project: Path, task_id: str, node_id: str, status: str, *, paths: list[str] | None = None, evidence: list[str] | None = None, note: str = "") -> dict:
    if status not in STATES:
        raise ValueError("Unknown status")
    path = _storage(project, task_id)
    plan = get_plan(project, task_id)
    by_id = {n["id"]: n for n in plan["nodes"]}
    if node_id not in by_id:
        raise ValueError("Unknown node")
    node = by_id[node_id]
    previous = node["status"]
    if status not in ALLOWED[previous]:
        raise ValueError(f"Disallowed transition {previous} -> {status}")
    if status in {"ready", "running"} and any(by_id[k]["status"] != "completed" for k in node["depends_on"]):
        raise ValueError("Dependencies have not completed")
    if paths is not None:
        if any(not isinstance(p, str) or not p or p.startswith("/") or ".." in Path(p).parts for p in paths):
            raise ValueError("Unsafe path scope")
        root = project.resolve()
        canonical = [(root / p).resolve() for p in paths]
        if any(not p.is_relative_to(root) for p in canonical):
            raise ValueError("Path scope escapes project")
        node["paths"] = sorted(set(p.relative_to(root).as_posix() for p in canonical))
    if status == "running":
        active = _running(project, task_id, node_id)
        if len(active) >= 4:
            raise ValueError("Project concurrency limit reached")
        if any(_conflict(node["paths"], n.get("paths", [])) for n in active):
            raise ValueError("Conflicting file ownership with active task")
        node["attempts"] += 1
        if node["attempts"] > 3:
            raise ValueError("Retry budget exceeded")
    if status == "completed" and not evidence:
        raise ValueError("Completion requires actual evidence references")
    verified = _evidence(project, evidence) if evidence else []
    node.update(status=status, updated_at=now(), note=note)
    if verified:
        node["evidence"].extend(verified)
    if status == "failed" and node["attempts"] < 3:
        node["retry_eligible"] = True
    elif status == "failed":
        node["retry_eligible"] = False
    json_write(path, plan)
    return {"task_id": task_id, "node": node_id, "status": status, "attempts": node["attempts"]}


def summarize_plan(project: Path, task_id: str) -> dict[str, Any]:
    plan = get_plan(project, task_id)
    counts = {state: sum(n["status"] == state for n in plan["nodes"]) for state in STATES}
    return {"task_id": task_id, "task": plan["task"], "statuses": counts, "unfinished": [n["id"] for n in plan["nodes"] if n["status"] not in {"completed", "skipped"}], "next": ready_nodes(project, task_id)}
