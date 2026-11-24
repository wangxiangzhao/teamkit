"""Opt-in, reversible integration into the project's AGENTS.md."""
from __future__ import annotations
from pathlib import Path

START = '<!-- TEAMKIT MASTER START -->'
END = '<!-- TEAMKIT MASTER END -->'
RULES = """<!-- TEAMKIT MASTER START -->
## TeamKit Master (project-local, opt-in)
Use .teamkit/project.json and .teamkit/index.json plus project Skills only when relevant.
Perform small tasks directly. For independent, high-value tasks, delegate to native
Codex subagents if this runtime supports them. Use professional roles: product,
design, ios_engineer, backend_engineer, quality, compliance, growth, analytics.
Identify business invariants and affected modules before edits; keep context scoped.
No parallel edits of the same file. Run real builds/tests; label blocked/not-run
checks honestly. Protect credentials, user changes and production systems.
Never claim Figma, device, payments or store verification without evidence.
<!-- TEAMKIT MASTER END -->
"""


def activate(project: Path, *, approve: bool = False) -> dict:
    root = project.resolve()
    if not (root / '.teamkit' / 'project.json').is_file():
        raise FileNotFoundError('Run teamkit init first')
    path = root / 'AGENTS.md'
    if path.is_symlink():
        raise ValueError('Refuse to edit symlinked AGENTS.md')
    old = path.read_text(encoding='utf-8') if path.exists() else ''
    if START in old and END in old:
        return {'status':'already-active','path':str(path)}
    if (START in old) != (END in old):
        raise ValueError('Incomplete TeamKit marker; manual review required')
    if not approve:
        return {'status':'dry-run','path':str(path),'required':'--approve'}
    if path.exists():
        backup = root / '.teamkit' / 'AGENTS.backup.md'
        if backup.exists():
            raise FileExistsError('AGENTS backup exists; cannot overwrite')
        backup.write_text(old, encoding='utf-8')
    path.write_text(old.rstrip() + ('\n\n' if old.strip() else '') + RULES, encoding='utf-8')
    return {'status':'active','path':str(path),'original_preserved':True}


def deactivate(project: Path, *, approve: bool = False) -> dict:
    path = project.resolve() / 'AGENTS.md'
    if not path.exists():
        return {'status':'not-active','path':str(path)}
    if path.is_symlink():
        raise ValueError('Refuse to edit symlinked AGENTS.md')
    data = path.read_text(encoding='utf-8')
    if START not in data and END not in data:
        return {'status':'not-active','path':str(path)}
    if data.count(START)!=1 or data.count(END)!=1 or data.index(START)>data.index(END):
        raise ValueError('Invalid TeamKit markers; manual review required')
    if not approve:
        return {'status':'dry-run','path':str(path),'required':'--approve'}
    start=data.index(START)
    end=data.index(END)+len(END)
    remainder=(data[:start]+data[end:]).rstrip()
    if remainder:
        path.write_text(remainder+'\n',encoding='utf-8')
    else:
        path.unlink()
    return {'status':'inactive','path':str(path),'other_instructions_preserved':True}
