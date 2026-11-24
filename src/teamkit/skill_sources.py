"""Auditable skill discovery registry; no automatic network downloads or installs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CATALOG = Path(__file__).resolve().parent / "assets" / "sources.json"


def candidates(capability: str | None = None) -> dict[str, Any]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    sources = data["sources"]
    if capability:
        sources = [item for item in sources if capability.lower() in [c.lower() for c in item["capabilities"]]]
    return {
        "policy": data["policy"],
        "install_performed": False,
        "candidates": sources,
        "count": len(sources),
        "requirements_before_use": ["inspect full source and scripts", "verify per-skill license", "check SDK / OS compatibility", "pin upstream revision", "verify runtime dependencies", "run skill tests and representative tasks"],
    }
