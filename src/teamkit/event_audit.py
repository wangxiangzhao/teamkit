"""Read-only, bounded analytics event inventory from literal Swift/ObjC call sites.

It does not infer dynamic event names or claim SDK delivery, timestamp correctness,
privacy consent, attribution, or accurate downstream analytics.
"""
from __future__ import annotations

import re
from pathlib import Path
from .core import json_read, json_write, now

# Narrow literal-call patterns only: avoids indiscriminately treating all
# project strings as events and keeps false positives explainable.
SWIFT_CALLS = [
    re.compile(r'\b(?:Analytics|FirebaseAnalytics)\.logEvent\s*\(\s*"([^"\n]{1,120})"'),
    re.compile(r'\b(?:analytics|tracker|sensorsAnalytics|SensorsAnalytics)\.track\s*\(\s*"([^"\n]{1,120})"'),
    re.compile(r'\b(?:analytics|tracker)\.track\s*\(\s*event\s*:\s*"([^"\n]{1,120})"'),
]
OBJC_CALLS = [
    re.compile(r'\[\s*FIRAnalytics\s+logEventWithName\s*:\s*@"([^"\n]{1,120})"'),
]
DYNAMIC_HINT = re.compile(r'\b(?:logEvent|track)\s*\(')


def inventory_events(project: Path, *, file_limit: int = 15000,
                     byte_limit: int = 8_000_000) -> dict:
    root = project.resolve()
    base = root / ".teamkit"
    index = json_read(base / "index.json")
    if not isinstance(index, dict) or not isinstance(index.get("files"), dict):
        raise FileNotFoundError("Run teamkit onboard before event inventory")
    if not 1 <= file_limit <= 50000 or not 4096 <= byte_limit <= 100_000_000:
        raise ValueError("Invalid inventory budget")
    entries = []
    unknown = []
    visited = 0
    remaining = byte_limit
    truncated = False
    for rel in sorted(index["files"]):
        p = root / rel
        if p.suffix not in {".swift", ".m", ".mm"} or p.is_symlink() or not p.is_file():
            continue
        visited += 1
        if visited > file_limit:
            truncated = True
            break
        size = p.stat().st_size
        if size > 300_000 or size > remaining:
            truncated = True
            continue
        remaining -= size
        text = p.read_text(encoding="utf-8", errors="replace")
        covered = set()
        patterns = SWIFT_CALLS if p.suffix == ".swift" else OBJC_CALLS
        for pat in patterns:
            for match in pat.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                key = (line, match.group(1))
                if key not in covered:
                    covered.add(key)
                    entries.append({"event": match.group(1), "path": rel, "line": line,
                                    "confidence": "literal_call_site"})
        if DYNAMIC_HINT.search(text) and not covered:
            unknown.append(rel)
    result = {
        "status": "partial" if truncated or unknown else "scanned",
        "captured_at": now(), "files_scanned": visited, "source_bytes_read": byte_limit-remaining,
        "literal_events": sorted(entries, key=lambda x: (x["event"], x["path"], x["line"])),
        "distinct_literal_event_names": len({x["event"] for x in entries}),
        "potential_dynamic_events": unknown[:50], "truncated": truncated,
        "downstream_delivery_verified": False, "event_dictionary_completeness_verified": False,
        "note": "Static literal call-site discovery only; inspect wrappers, consent, dynamic names and SDK debug logs before claiming accurate tracking.",
    }
    json_write(base / "reports" / "event-inventory.json", result)
    return result
