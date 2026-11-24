"""Deterministic safety-focused engineering gates with explicit not-run outcomes."""
from __future__ import annotations
import hashlib
import os
import subprocess
from pathlib import Path
from .core import json_read, json_write, now

BINARY_SUFFIX = {'.png', '.jpg', '.jpeg', '.webp', '.heic', '.gif', '.pdf', '.svg'}
ASSET_SKIP = {'.git', '.teamkit', 'Pods', 'node_modules', '.build', 'DerivedData', '.venv'}


def scan_assets(project: Path, *, max_bytes: int = 1024 * 1024, max_files: int = 30000) -> dict:
    if not 1024 <= max_bytes <= 1024 * 1024 * 1024:
        raise ValueError('Invalid image limit')
    out, duplicates = [], []
    fingerprints = {}
    visited = 0
    for base, dirs, files in os.walk(project.resolve(), followlinks=False):
        dirs[:] = [d for d in dirs if d not in ASSET_SKIP and not (Path(base) / d).is_symlink()]
        for filename in files:
            path = Path(base) / filename
            if path.is_symlink() or path.suffix.lower() not in BINARY_SUFFIX:
                continue
            visited += 1
            if visited > max_files:
                raise RuntimeError('Asset scan file limit exceeded')
            rel = path.relative_to(project.resolve()).as_posix()
            size = path.stat().st_size
            if size > max_bytes:
                out.append({'path': rel, 'size': size, 'limit': max_bytes})
            if size < 100 * 1024 * 1024:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if digest in fingerprints:
                    duplicates.append({'path': rel, 'same_as': fingerprints[digest]})
                else:
                    fingerprints[digest] = rel
    return {'status': 'failed' if out or duplicates else 'passed', 'files_scanned': visited,
            'oversized': out, 'duplicates': duplicates,
            'note': 'Size/byte-duplicate check only; compression, visual fidelity and decoded memory are NOT validated'}


def run_gate(project: Path, gate: str, *, timeout: int = 180, approve_command: bool = False) -> dict:
    if gate not in {'build', 'test'}:
        raise ValueError('Unsupported gate')
    if timeout < 1 or timeout > 1800:
        raise ValueError('Invalid timeout')
    base = project.resolve() / '.teamkit'
    cfg = json_read(base / 'gates.json')
    if cfg is None:
        raise FileNotFoundError('Project not initialized')
    key = 'build_command' if gate == 'build' else 'test_command'
    cmd = cfg.get(key)
    if not cmd:
        return {'gate': gate, 'status': 'not-run', 'reason': f'{key} not configured'}
    if not approve_command:
        return {'gate': gate, 'status': 'blocked', 'reason': 'Explicit --approve-command required'}
    if not isinstance(cmd, list) or not cmd or any(not isinstance(x, str) or not x or '\x00' in x for x in cmd):
        raise ValueError('Gate command must be a nonempty argv string array')
    try:
        p = subprocess.run(cmd, cwd=project.resolve(), capture_output=True, text=True,
                           timeout=timeout, check=False, shell=False)
        data = {'gate': gate, 'status': 'passed' if p.returncode == 0 else 'failed',
                'exit_code': p.returncode, 'argv': cmd, 'stdout_tail': p.stdout[-6000:],
                'stderr_tail': p.stderr[-6000:], 'at': now()}
    except subprocess.TimeoutExpired:
        data = {'gate': gate, 'status': 'failed', 'reason': 'timeout', 'timeout_seconds': timeout}
    except OSError as exc:
        data = {'gate': gate, 'status': 'blocked', 'reason': str(exc)}
    json_write(base / 'reports' / f'{gate}.json', data)
    return data


def check_release(project: Path) -> dict:
    base = project.resolve() / '.teamkit'
    if not (base / 'project.json').exists():
        raise FileNotFoundError('Project not initialized')
    results = {'inventory': 'not-run', 'assets': 'not-run', 'build': 'not-run',
               'tests': 'not-run', 'ui': 'not-run', 'privacy': 'not-run', 'store': 'not-run'}
    result = {'status': 'blocked', 'checks': results,
              'reason': 'Verified build, tests, UI, privacy, StoreKit and compliance are required',
              'release_approved': False}
    json_write(base / 'reports' / 'release.json', result)
    return result
