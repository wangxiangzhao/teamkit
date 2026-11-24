from pathlib import Path
import pytest
from teamkit.core import init_project
from teamkit.activation import activate, deactivate, inspect, START


def test_existing_agents_preserved_exactly(tmp_path):
    init_project(tmp_path)
    path=tmp_path/'AGENTS.md'
    original=b'\xef\xbb\xbf# Existing\r\nKeep project requirements.\r\n\r\n'
    path.write_bytes(original)
    assert inspect(tmp_path)['status']=='mergeable'
    assert activate(tmp_path,approve=True)['status']=='active'
    assert path.read_bytes().startswith(original)
    assert path.read_bytes().count(START.encode())==1
    assert activate(tmp_path,approve=True)['status']=='already-active'
    assert deactivate(tmp_path,approve=True)['status']=='inactive'
    assert path.read_bytes()==original


def test_undo_preserves_user_append_after_block(tmp_path):
    init_project(tmp_path)
    path=tmp_path/'AGENTS.md'
    path.write_text('Existing rules\n')
    activate(tmp_path,approve=True)
    with path.open('ab') as stream:
        stream.write(b'\n# Later user rule\n')
    assert deactivate(tmp_path,approve=True)['status']=='inactive'
    assert path.read_bytes()==b'Existing rules\n\n# Later user rule\n'


def test_modified_teamkit_block_never_deleted(tmp_path):
    init_project(tmp_path)
    path=tmp_path/'AGENTS.md'
    path.write_text('Important')
    activate(tmp_path,approve=True)
    path.write_text(path.read_text().replace('Execute simple tasks','Always execute tasks'))
    with pytest.raises(ValueError):
        deactivate(tmp_path,approve=True)
    assert 'Always execute tasks' in path.read_text()


def test_legacy_marker_kept_not_duplicated(tmp_path):
    init_project(tmp_path)
    path=tmp_path/'AGENTS.md'
    path.write_text('Existing\n'+START+'\nLegacy\n<!-- TEAMKIT MASTER END -->')
    assert activate(tmp_path,approve=True)['status']=='already-active'
    with pytest.raises(ValueError):
        deactivate(tmp_path,approve=True)


def test_missing_agents_removal(tmp_path):
    init_project(tmp_path)
    activate(tmp_path,approve=True)
    assert deactivate(tmp_path,approve=True)['status']=='inactive'
    assert not (tmp_path/'AGENTS.md').exists()
