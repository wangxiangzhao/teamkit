"""Persistent deterministic DAG scheduling. Codex Master owns real model dispatch."""
from __future__ import annotations
import re
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
    return base / "plans" / f"{task_id}.json"


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
    return any(overlap(x, y) for x in a for y in b)


def ready_nodes(project: Path, task_id: str, max_running: int = 2) -> dict:
    if max_running < 1 or max_running > 4:
        raise ValueError("concurrency must be within 1..4")
    plan = get_plan(project, task_id)
    nodes = plan["nodes"]
    by_id = {n["id"]: n for n in nodes}
    active = [n for n in nodes if n["status"] == "running"]
    capacity = max(0, max_running - len(active))
    ready = []
    for n in nodes:
        if n["status"] not in {"pending", "ready"}:
            continue
        if not all(by_id[k]["status"] == "completed" for k in n["depends_on"]):
            continue
        if any(_conflict(n.get("paths", []), other.get("paths", [])) for other in active + ready):
            continue
        if len(ready) >= capacity:
            break
        ready.append(n)
    return {"task_id": task_id, "ready": [{"id": n["id"], "agent": n["agent"], "mode": n["mode"], "paths": n["paths"]} for n in ready], "running": len(active), "slots": capacity, "advisory": True}


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
        node["paths"] = sorted(set(paths))
    if status == "running":
        active = [n for n in plan["nodes"] if n["id"] != node_id and n["status"] == "running"]
        if any(_conflict(node["paths"], n.get("paths", [])) for n in active):
            raise ValueError("Conflicting file ownership with active task")
        node["attempts"] += 1
        if node["attempts"] > 3:
            raise ValueError("Retry budget exceeded")
    if status == "completed" and not evidence:
        raise ValueError("Completion requires actual evidence references")
    node.update(status=status, updated_at=now(), note=note)
    if evidence:
        node["evidence"].extend(evidence)
    json_write(path, plan)
    return {"task_id": task_id, "node": node_id, "status": status, "attempts": node["attempts"]}


def summarize_plan(project: Path, task_id: str) -> dict[str, Any]:
    plan = get_plan(project, task_id)
    counts = {state: sum(n["status"] == state for n in plan["nodes"]) for state in STATES}
    return {"task_id": task_id, "task": plan["task"], "statuses": counts, "unfinished": [n["id"] for n in plan["nodes"] if n["status"] not in {"completed", "skipped"}], "next": ready_nodes(project, task_id)}
