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


def _optional_decimal(value: str | None, column: str) -> Decimal | None:
    if value in (None, ''):
        return None
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f'Invalid {column}') from exc
    if not number.is_finite() or number < 0:
        raise ValueError(f'{column} must be finite and nonnegative')
    return number


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
            if not spend.is_finite() or not rev.is_finite() or spend < 0 or rev < 0 or observed < 0:
                raise ValueError('Non-finite or negative money / days')
            # A D45 cumulative revenue value is not D30 revenue. Older
            # cohorts need an explicit revenue_as_of_day equal to the D-window.
            as_of_raw = row.get('revenue_as_of_day')
            try:
                revenue_as_of_day = int(as_of_raw) if as_of_raw not in (None, '') else observed
            except (TypeError, ValueError) as exc:
                raise ValueError('Invalid revenue_as_of_day') from exc
            if revenue_as_of_day < 0 or revenue_as_of_day > observed:
                raise ValueError('Revenue date cannot exceed observation window')
            eligible = observed >= window and revenue_as_of_day == window
            reason = None if eligible else (
                'cohort_not_mature' if observed < window else 'revenue_not_at_requested_window'
            )
            ratio = round(rev / spend, 6) if spend and eligible else None
            costs = _optional_decimal(row.get('other_costs'), 'other_costs')
            acquired_raw = row.get('acquired_users')
            acquired = None
            if acquired_raw not in (None, ''):
                if not re.fullmatch(r'[0-9]+', acquired_raw):
                    raise ValueError('acquired_users must be a nonnegative integer')
                acquired = int(acquired_raw)
            profit = rev - spend - costs if eligible and costs is not None else None
            ltv = round(rev / acquired, 6) if eligible and acquired else None
            rows.append({'cohort': row['cohort'], 'currency': row.get('currency') or 'unspecified',
                         'spend': str(spend), 'revenue': str(rev),
                         'days_observed': observed, 'revenue_as_of_day': revenue_as_of_day,
                         'd_window_roas': str(ratio) if ratio is not None else None,
                         'complete_window': eligible, 'excluded_reason': reason,
                         'other_costs': str(costs) if costs is not None else None,
                         'acquired_users': acquired,
                         'd_window_profit': str(profit) if profit is not None else None,
                         'd_window_revenue_per_acquired_user': str(ltv) if ltv is not None else None})
    currencies = set(r['currency'] for r in rows)
    if len(currencies) > 1:
        raise ValueError('Mixed currencies; normalize before aggregating')
    complete = [r for r in rows if r['complete_window']]
    total_spend = sum(Decimal(r['spend']) for r in complete)
    total_rev = sum(Decimal(r['revenue']) for r in complete)
    costs_complete = bool(complete) and all(r['other_costs'] is not None for r in complete)
    total_costs = sum(Decimal(r['other_costs']) for r in complete) if costs_complete else None
    users_complete = bool(complete) and all(r['acquired_users'] is not None for r in complete)
    total_users = sum(r['acquired_users'] for r in complete) if users_complete else None
    return {'window_days': window, 'cohorts': rows, 'complete_cohorts': len(complete),
            'total_spend': str(total_spend), 'total_revenue': str(total_rev),
            'aggregate_roas': str(round(total_rev / total_spend, 6)) if total_spend else None,
            'total_other_costs': str(total_costs) if total_costs is not None else None,
            'total_acquired_users': total_users,
            'aggregate_profit': str(total_rev - total_spend - total_costs) if total_costs is not None else None,
            'aggregate_revenue_per_acquired_user': str(round(total_rev / total_users, 6)) if total_users else None,
            'currency': next(iter(currencies), 'unspecified'),
            'warning': 'Revenue must be explicitly scoped to requested D-window; immature or mismatched cohorts excluded'}
