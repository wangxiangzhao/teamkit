"""Read-only mature skill discovery, never automatic installation."""
from __future__ import annotations
import json
from pathlib import Path

CATALOG = Path(__file__).resolve().parent / 'assets' / 'sources.json'


def candidates(capability: str | None = None) -> dict:
    data = json.loads(CATALOG.read_text(encoding='utf-8'))
    sources = data['sources']
    if capability:
        sources = [item for item in sources if capability.lower() in [s.lower() for s in item['capabilities']]]
    return {'policy': data['policy'], 'install_performed': False, 'candidates': sources,
            'count': len(sources), 'requirements_before_use': ['source review', 'license check',
            'SDK/platform compatibility', 'pin revision', 'run tests']}
