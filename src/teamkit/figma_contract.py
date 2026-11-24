"""Bounded, read-only Figma node JSON -> machine-readable UI design contract.

Use with JSON exported by an authorized Figma MCP / file API client. This module
does not query Figma, guess missing interactions, or mutate app source code.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .core import json_write, now

MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_NODES = 3000


def contract(source: Path, *, module: str, project: Path | None = None, write: bool = False) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", module):
        raise ValueError("Invalid module name")
    if source.is_symlink() or not source.is_file():
        raise ValueError("Refuse missing or symlinked Figma JSON")
    if source.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("Figma JSON exceeds size limit")
    raw = source.read_bytes()
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Invalid Figma JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Figma JSON root must be object")
    root = payload.get("document", payload)
    if not isinstance(root, dict):
        raise ValueError("Figma document is missing")
    nodes = []
    image_refs = set()
    reactions = []
    page = None
    stack = [(root, None, None)]
    visited = 0
    while stack:
        node, parent_id, page_name = stack.pop()
        if not isinstance(node, dict):
            continue
        visited += 1
        if visited > MAX_NODES:
            raise ValueError("Figma node count exceeds safety limit")
        node_type = str(node.get("type", "UNKNOWN"))
        name = str(node.get("name", ""))[:180]
        node_id = str(node.get("id", ""))[:100]
        if node_type == "CANVAS":
            page_name = name
        bounds = node.get("absoluteBoundingBox")
        if isinstance(bounds, dict):
            bbox = {k: bounds[k] for k in ("x", "y", "width", "height")
                    if k in bounds and type(bounds[k]) in (int, float)}
        else:
            bbox = None
        fills = node.get("fills")
        if isinstance(fills, list):
            for fill in fills:
                if isinstance(fill, dict) and fill.get("type") == "IMAGE" and isinstance(fill.get("imageRef"), str):
                    image_refs.add(fill["imageRef"])
        entry = {
            "id": node_id, "name": name, "type": node_type, "parent": parent_id,
            "page": page_name, "bounds": bbox,
            "layout_mode": node.get("layoutMode"), "component_id": node.get("componentId"),
            "visible": node.get("visible", True),
        }
        if node_type == "TEXT":
            entry["text_sample"] = str(node.get("characters", ""))[:160]
        if node.get("boundVariables"):
            entry["has_bound_variables"] = True
        nodes.append(entry)
        raw_reactions = node.get("reactions")
        if isinstance(raw_reactions, list):
            for reaction in raw_reactions:
                if not isinstance(reaction, dict):
                    continue
                action = reaction.get("action")
                reactions.append({
                    "node_id": node_id,
                    "trigger": reaction.get("trigger"),
                    "action": action if isinstance(action, dict) else None,
                })
        children = node.get("children")
        if isinstance(children, list):
            stack.extend((child, node_id, page_name) for child in reversed(children))
    result = {
        "schema_version": 1, "module": module, "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_kind": "Figma node JSON", "captured_at": now(), "nodes": nodes,
        "node_count": len(nodes), "image_refs": sorted(image_refs), "reactions": reactions,
        "components": payload.get("components", {}) if isinstance(payload.get("components"), dict) else {},
        "styles": payload.get("styles", {}) if isinstance(payload.get("styles"), dict) else {},
        "variables_present": "variables" in payload,
        "verification": {
            "figma_json_parsed": True, "live_figma_mcp_access": False,
            "navigation_business_logic_verified": False,
            "ui_screenshot_verified": False, "animation_verified": False,
        },
        "notes": "Only supplied node facts are extracted. Missing states, business rules and animations must be checked against project code and live design tools.",
    }
    if write:
        if project is None:
            raise ValueError("--project required when writing a contract")
        base = project.resolve() / ".teamkit"
        if not (base / "project.json").is_file():
            raise FileNotFoundError("Run teamkit onboard first")
        destination = base / "contracts" / f"figma-{module}.json"
        if destination.is_symlink():
            raise ValueError("Refuse symlinked Figma contract")
        if destination.exists():
            old = json.loads(destination.read_text(encoding="utf-8"))
            if old.get("source_sha256") != result["source_sha256"]:
                raise FileExistsError("Existing design contract belongs to a different Figma JSON. Preserve it and review changes before replacement.")
        else:
            json_write(destination, result)
        result["contract_path"] = str(destination)
    return result
