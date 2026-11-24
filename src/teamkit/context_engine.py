"""Project-scoped context compilation, change impact and evidence cache."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from .core import json_read, json_write, inventory, now, _fingerprint


def _project_files(project: Path) -> tuple[dict, Path]:
    base = project.resolve() / '.teamkit'
    data = json_read(base / 'index.json')
    if data is None:
        raise FileNotFoundError('teamkit init required')
    return data['files'], base


def discover_modules(project: Path) -> dict:
    files, base = _project_files(project)
    modules = {}
    for p in sorted(files):
        parts = Path(p).parts
        if not parts:
            continue
        if len(parts) >= 3 and parts[0] in ('Sources', 'App', 'Modules', 'Features'):
            name = parts[1]
        elif len(parts) > 1:
            name = parts[0]
        else:
            name = 'root'
        modules.setdefault(name, []).append(p)
    result = {'modules': {m: {'paths': paths, 'count': len(paths)} for m, paths in modules.items()},
              'generated_at': now(), 'source': 'path-derived, verify business boundaries'}
    json_write(base / 'modules.json', result)
    return result


def compile_context(project: Path, module: str, *, max_files: int = 30, max_chars: int = 5000) -> dict:
    if max_files < 1 or max_files > 200 or max_chars < 100 or max_chars > 100000:
        raise ValueError('Invalid context budget')
    if not re.fullmatch(r'[\w-]{1,64}', module, re.UNICODE):
        raise ValueError('Invalid module')
    files, base = _project_files(project)
    modules = discover_modules(project)
    exact = modules['modules'].get(module, {}).get('paths', [])
    matches = exact or [p for p in files if module.lower() in p.lower()]
    matches = sorted(matches, key=lambda p: (not p.endswith('.swift'), len(p), p))
    selected = matches[:max_files]
    relevant = [{'path': p, 'bytes': files[p]['bytes'], 'sha256': files[p]['sha256'][:12]} for p in selected]
    invariants = json_read(base / 'contracts' / f'{module}.json', {})
    summary = {'module': module, 'paths': relevant, 'business_invariants': invariants.get('invariants', []),
               'truncated': len(matches) > len(selected), 'file_count': len(matches),
               'provenance': 'project index; source code not injected'}
    payload = json.dumps(summary, ensure_ascii=False)
    while len(payload) > max_chars and relevant:
        relevant.pop()
        summary['truncated'] = True
        payload = json.dumps(summary, ensure_ascii=False)
    if len(payload) > max_chars:
        raise ValueError('Budget smaller than mandatory context; increase max_chars')
    return summary


def impact(project: Path, *, base_index: Path | None = None) -> dict:
    files, base = _project_files(project)
    current = inventory(project)['files']
    before = json_read(base_index, {})['files'] if base_index else files
    changed = sorted(p for p in set(before) | set(current) if before.get(p) != current.get(p))
    modules = json_read(base / 'modules.json') or discover_modules(project)
    affected = []
    for name, info in modules['modules'].items():
        if set(info['paths']) & set(changed):
            affected.append(name)
    risk = 'high' if any(('Shared/' in p or 'Core/' in p or 'Package.swift' in p or '.pbxproj' in p or 'StoreKit' in p) for p in changed) else 'normal'
    return {'changed_paths': changed, 'affected_modules': affected, 'risk': risk,
            'scope_confidence': 'path-only; dependencies may expand scope',
            'requires_manual_dependency_review': True}


def evidence_store(project: Path, key: str, status: str, *, source_paths: list[str], report: str, environment: str = '') -> dict:
    if not re.fullmatch(r'[\w-]{1,64}', key):
        raise ValueError('Invalid evidence key')
    if status not in {'passed', 'failed', 'blocked', 'not-run', 'not-applicable'}:
        raise ValueError('Invalid evidence status')
    files, base = _project_files(project)
    files = inventory(project)['files']
    if not source_paths:
        raise ValueError('Evidence requires source paths')
    if any(p not in files for p in source_paths):
        raise ValueError('Source not included in index')
    dig = hashlib.sha256()
    for p in sorted(set(source_paths)):
        dig.update((p + ':' + files[p]['sha256']).encode())
    dig.update(environment.encode())
    # Include the complete source inventory so additions/deletions also invalidate evidence.
    dig.update(json.dumps(files, sort_keys=True).encode())
    result = {'key': key, 'status': status, 'source_paths': sorted(set(source_paths)), 'digest': dig.hexdigest(),
              'environment': environment, 'report': report, 'created_at': now(),
              'note': 'Evidence is invalidated by changed source digests; external dependencies still require revalidation'}
    json_write(base / 'evidence' / f'{key}.json', result)
    return result


def evidence_status(project: Path, key: str, *, environment: str = '') -> dict:
    if not re.fullmatch(r'[\w-]{1,64}', key):
        raise ValueError('Invalid evidence key')
    files, base = _project_files(project)
    files = inventory(project)['files']
    previous = json_read(base / 'evidence' / f'{key}.json')
    if previous is None:
        return {'key': key, 'valid': False, 'reason': 'missing'}
    dig = hashlib.sha256()
    for p in previous['source_paths']:
        if p not in files:
            return {'key': key, 'valid': False, 'reason': 'source_missing'}
        dig.update((p + ':' + files[p]['sha256']).encode())
    dig.update(environment.encode())
    dig.update(json.dumps(files, sort_keys=True).encode())
    return {'key': key, 'valid': dig.hexdigest() == previous['digest'], 'status': previous['status'],
            'reason': 'hash_match' if dig.hexdigest() == previous['digest'] else 'source_or_environment_changed',
            'caution': 'Live local source hashes checked; external systems and toolchain changes require revalidation'}
