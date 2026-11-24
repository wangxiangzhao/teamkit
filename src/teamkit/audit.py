"""Read-only self-audit; conservative conclusions, no project mutations."""
from __future__ import annotations
import hashlib
import shutil
from pathlib import Path
from .activation import START, END
from .core import json_read, inventory


def audit_project(project: Path, *, full_scan: bool = True) -> dict:
    root = project.resolve()
    findings = []
    def report(code, severity, message):
        findings.append({'code':code,'severity':severity,'message':message})
    if not root.is_dir():
        raise FileNotFoundError(f'Project not found: {root}')
    base = root / '.teamkit'
    if base.is_symlink():
        report('metadata_symlink','critical','Metadata directory cannot be a symlink')
        return {'status':'failed','findings':findings,'commercial_ready':False}
    meta=base/'project.json'
    if not meta.is_file() or meta.is_symlink():
        report('not_initialized','error','Project is not initialized by TeamKit')
        return {'status':'failed','findings':findings,'commercial_ready':False}
    try:
        data=json_read(meta)
        if not isinstance(data,dict) or data.get('schema_version')!=1:
            report('invalid_profile','error','Invalid project schema')
    except (OSError,ValueError,TypeError):
        report('invalid_profile','error','Corrupted project metadata')
    ag=root/'AGENTS.md'
    manifest=base/'agents-merge.json'
    if ag.is_symlink() or manifest.is_symlink():
        report('symlinked_instructions','critical','Symlinked AGENTS or metadata: unsafe')
    elif ag.is_file():
        raw=ag.read_bytes()
        if raw.count(START.encode())!=raw.count(END.encode()) or raw.count(START.encode())>1:
            report('instruction_markers','error','Inconsistent TeamKit markers')
        if START.encode() in raw and not manifest.exists():
            report('unmanaged_legacy_block','warning','Legacy TeamKit block has no safe rollback metadata')
        elif manifest.is_file():
            try:
                m=json_read(manifest)
                offset=m['original_length'];end=offset+m['added_length']
                if hashlib.sha256(raw[:offset]).hexdigest()!=m['original_sha256'] or hashlib.sha256(raw[offset:end]).hexdigest()!=m['added_sha256']:
                    report('instruction_drift','error','Project instructions have changed from saved merge baseline')
            except (OSError,ValueError,KeyError,TypeError):
                report('instruction_manifest','error','Invalid merge manifest')
    elif manifest.exists():
        report('orphaned_manifest','error','Merge manifest exists without AGENTS.md')
    if full_scan:
        saved=json_read(base/'index.json',{})
        if not isinstance(saved,dict) or not isinstance(saved.get('files'),dict):
            report('missing_index','warning','No valid source index')
        else:
            current=inventory(root)['files']
            existing=saved['files']
            if any(existing.get(p)!=current.get(p) for p in set(current)|set(existing)):
                report('stale_index','warning','Project source inventory changed; needs incremental sync')
    if not shutil.which('codex'):
        report('codex_not_available','warning','Codex CLI not available in this environment')
    if not shutil.which('xcodebuild'):
        report('xcode_not_available','warning','Xcode command line tools unavailable')
    # A passing local configuration audit is not equivalent to full external SDK validation.
    blocked=any(f['severity'] in ('critical','error') for f in findings)
    return {'status':'failed' if blocked else 'passed','findings':findings,
            'commercial_ready':False,'runtime_integration_verified':False,
            'notice':'Local configuration audit only; never claims Figma/Xcode/subagent or release readiness'}


def safe_maintain(project: Path) -> dict:
    """Automatically refresh only TeamKit's own index when safe."""
    from .core import sync_project
    before=audit_project(project)
    changed=False
    if before['status'] == 'passed' and any(i['code']=='stale_index' for i in before['findings']):
        sync_project(project)
        changed=True
    after=audit_project(project)
    return {'status':after['status'],'index_refreshed':changed,'findings':after['findings'],
            'manual_project_changes':False,'commercial_ready':False}
