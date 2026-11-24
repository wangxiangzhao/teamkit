"""Opt-in local Codex CLI bridge; does not change credentials, model or approval config."""
from __future__ import annotations
import json
import shutil
import subprocess
import uuid
from pathlib import Path
from .core import json_write, route_task, now
from .context_engine import compile_context

MAX_OUTPUT = 12000


def prepare(project: Path, task: str, *, module: str | None = None, intent: str | None = None) -> dict:
    root = project.resolve()
    if not (root / '.teamkit' / 'project.json').exists():
        raise FileNotFoundError('Run teamkit init first')
    route = route_task(task, explicit_intent=intent, project=root)
    context = compile_context(root, module, max_files=20, max_chars=5000) if module else None
    instructions = (
        'You are Codex Master executing a TeamKit project task. Read project AGENTS.md if present. '
        'Use Skills selectively, respect business invariants, and prefer direct edits for small tasks. '
        'For large independent work delegate only if this Codex runtime supports native subagents. '
        'Avoid overlapping file writes; route is advisory and needs semantic validation. '
        'Use actual builds/tests, never claim success without evidence. '
        'Do not change credentials, publish apps or mutate production systems. '
        'Keep handoffs concise and log significant results.\n\n'
    )
    payload = {'task': task, 'route': route, 'project': str(root), 'module_context': context}
    prompt = instructions + json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    return {'status': 'prepared', 'route': route, 'module_context': context,
            'prompt': prompt, 'estimated_prompt_chars': len(prompt)}


def run(project: Path, task: str, *, approve: bool = False, timeout: int = 3600,
        module: str | None = None, intent: str | None = None) -> dict:
    if timeout < 30 or timeout > 14400:
        raise ValueError('Timeout out of allowed range')
    plan = prepare(project, task, module=module, intent=intent)
    if not approve:
        return {'status': 'dry-run', 'route': plan['route'],
                'estimated_prompt_chars': plan['estimated_prompt_chars'],
                'preview': plan['prompt'][:1800], 'note': 'Use --approve-execution to run local Codex'}
    codex = shutil.which('codex')
    if not codex:
        return {'status': 'blocked', 'reason': 'codex executable not available'}
    root = project.resolve()
    argv = [codex, 'exec', plan['prompt']]
    try:
        p = subprocess.run(argv, cwd=root, capture_output=True, text=True,
                           timeout=timeout, check=False, shell=False)
        result = {'status': 'completed' if p.returncode == 0 else 'failed',
                  'exit_code': p.returncode, 'task': task, 'route': plan['route'],
                  'stdout_tail': p.stdout[-MAX_OUTPUT:], 'stderr_tail': p.stderr[-MAX_OUTPUT:],
                  'note': 'CLI completion is NOT proof of quality gate success', 'at': now()}
    except subprocess.TimeoutExpired:
        result = {'status': 'failed', 'reason': 'timeout', 'timeout_seconds': timeout}
    except OSError as exc:
        result = {'status': 'blocked', 'reason': str(exc)}
    base = root / '.teamkit' / 'runs'
    base.mkdir(parents=True, exist_ok=True)
    result['run_id'] = uuid.uuid4().hex[:12]
    json_write(base / (result['run_id'] + '.json'), result)
    return result
