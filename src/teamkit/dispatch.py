"""Opt-in local Codex CLI bridge; does not change credentials, model or approval config."""
from __future__ import annotations
import json
import shutil
import subprocess
import uuid
import time
from pathlib import Path
from .core import json_write, route_task, now
from .context_engine import compile_context
from .metrics import record as record_metrics
from .skill_resolver import resolve_task

MAX_OUTPUT = 12000

def parse_codex_jsonl(payload: str) -> dict:
    """Read usage from turn.completed events, without estimating missing values."""
    keys = ("input_tokens", "cached_input_tokens", "output_tokens")
    totals = {key: 0 for key in keys}
    turns = invalid = 0
    final_message = None
    for line in payload.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            invalid += 1
            continue
        if not isinstance(event, dict):
            invalid += 1
            continue
        if event.get("type") == "turn.completed":
            usage = event.get("usage")
            if not isinstance(usage, dict):
                continue
            values = [usage.get(key) for key in keys]
            if any(type(v) is not int or v < 0 for v in values):
                continue
            if values[1] > values[0]:
                continue
            for key, value in zip(keys, values):
                totals[key] += value
            turns += 1
        elif event.get("type") == "item.completed":
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                message = item.get("text")
                if isinstance(message, str):
                    final_message = message[-MAX_OUTPUT:]
    return {"token_usage": totals if turns else None,
            "turns_completed": turns, "invalid_lines": invalid,
            "final_message": final_message,
            "note": "Cached input is included in input_tokens, not additional."}



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
    payload = {'task': task, 'route': route, 'project': str(root), 'module_context': context, 'task_skills': resolve_task(root, route)}
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
    argv = [codex, 'exec', '--json', plan['prompt']]
    started = time.monotonic()
    try:
        p = subprocess.run(argv, cwd=root, capture_output=True, text=True,
                           timeout=timeout, check=False, shell=False)
        parsed = parse_codex_jsonl(p.stdout)
        result = {'status': 'completed' if p.returncode == 0 else 'failed',
                  'exit_code': p.returncode, 'task': task, 'route': plan['route'],
                  'token_usage': parsed['token_usage'], 'turns_completed': parsed['turns_completed'],
                  'invalid_jsonl_lines': parsed['invalid_lines'],
                  'final_message': parsed['final_message'], 'stderr_tail': p.stderr[-MAX_OUTPUT:],
                  'duration_seconds': round(time.monotonic() - started, 3),
                  'note': 'CLI completion is NOT proof of quality gate success', 'at': now()}
    except subprocess.TimeoutExpired:
        result = {'status': 'failed', 'reason': 'timeout', 'timeout_seconds': timeout}
    except OSError as exc:
        result = {'status': 'blocked', 'reason': str(exc)}
    base = root / '.teamkit' / 'runs'
    base.mkdir(parents=True, exist_ok=True)
    result['run_id'] = uuid.uuid4().hex[:12]
    json_write(base / (result['run_id'] + '.json'), result)
    if 'duration_seconds' in result:
        usage = result.get('token_usage') or {}
        record_metrics(
            root, result['run_id'],
            input_tokens=usage.get('input_tokens'),
            output_tokens=usage.get('output_tokens'),
            cached_tokens=usage.get('cached_input_tokens'),
            duration_seconds=result['duration_seconds'],
            outcome='failed' if result['status'] == 'failed' else 'unknown',
        )
        result['metrics_saved'] = result['run_id']
    return result
