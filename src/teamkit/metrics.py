"""Task metrics and ROAS calculation without invented data."""
from __future__ import annotations
import csv
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from .core import json_read, json_write, now


def record(project: Path, task_id: str, *, input_tokens: int | None = None,
           output_tokens: int | None = None, cached_tokens: int | None = None,
           duration_seconds: float | None = None, outcome: str = 'unknown') -> dict:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', task_id):
        raise ValueError('Invalid task ID')
    for n in (input_tokens, output_tokens, cached_tokens):
        if n is not None and (not isinstance(n, int) or n < 0):
            raise ValueError('Token counts must be nonnegative integers')
    if input_tokens is not None and cached_tokens is not None and cached_tokens > input_tokens:
        raise ValueError('cached tokens exceed input tokens')
    if duration_seconds is not None and duration_seconds < 0:
        raise ValueError('negative duration')
    if outcome not in {'unknown', 'passed', 'failed', 'blocked'}:
        raise ValueError('Invalid outcome')
    base = project.resolve() / '.teamkit'
    if not (base / 'project.json').exists():
        raise FileNotFoundError('Project not initialized')
    data = {'task_id': task_id, 'input_tokens': input_tokens, 'output_tokens': output_tokens,
            'cached_tokens': cached_tokens, 'duration_seconds': duration_seconds, 'outcome': outcome,
            'captured_at': now(), 'provenance': 'user_or_tool_reported, not independently metered'}
    json_write(base / 'metrics' / f'{task_id}.json', data)
    return data


def summary(project: Path) -> dict:
    base = project.resolve() / '.teamkit' / 'metrics'
    items = [json_read(p) for p in sorted(base.glob('*.json'))]
    def sum_known(k):
        nums = [x[k] for x in items if x.get(k) is not None]
        return sum(nums) if nums else None
    return {'tasks': len(items), 'input_tokens': sum_known('input_tokens'),
            'output_tokens': sum_known('output_tokens'), 'cached_tokens': sum_known('cached_tokens'),
            'duration_seconds': sum_known('duration_seconds'),
            'reported_outcomes': {s: sum(x.get('outcome') == s for x in items)
                                  for s in ('passed', 'failed', 'blocked', 'unknown')},
            'warning': 'Missing token measurements are not imputed'}


def roas_csv(csv_path: Path, *, window: int = 30) -> dict:
    if window < 0 or window > 365:
        raise ValueError('Invalid ROAS observation window')
    rows = []
    with csv_path.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        required = {'cohort', 'spend', 'revenue', 'days_observed'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('CSV missing required columns')
        for row in reader:
            try:
                spend, rev = Decimal(row['spend']), Decimal(row['revenue'])
                observed = int(row['days_observed'])
            except (ValueError, InvalidOperation, TypeError) as exc:
                raise ValueError('Invalid numeric values in CSV') from exc
            if spend < 0 or rev < 0 or observed < 0:
                raise ValueError('Negative money or days')
            ratio = round(rev / spend, 6) if spend and observed >= window else None
            rows.append({'cohort': row['cohort'], 'currency': row.get('currency') or 'unspecified',
                         'spend': str(spend), 'revenue': str(rev),
                         'days_observed': observed, 'd_window_roas': str(ratio) if ratio is not None else None,
                         'complete_window': observed >= window})
    currencies = set(r['currency'] for r in rows)
    if len(currencies) > 1:
        raise ValueError('Mixed currencies; normalize before aggregating')
    complete = [r for r in rows if r['complete_window']]
    total_spend = sum(Decimal(r['spend']) for r in complete)
    total_rev = sum(Decimal(r['revenue']) for r in complete)
    return {'window_days': window, 'cohorts': rows, 'complete_cohorts': len(complete),
            'total_spend': str(total_spend), 'total_revenue': str(total_rev),
            'aggregate_roas': str(round(total_rev / total_spend, 6)) if total_spend else None,
            'currency': next(iter(currencies), 'unspecified'),
            'warning': 'Revenue must already be cumulative through window; incomplete cohorts excluded'}
