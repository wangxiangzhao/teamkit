from teamkit.core import init_project
from teamkit.activation import activate, deactivate, START
from teamkit.cli import main


def test_activate_preserves_old_content(tmp_path):
    init_project(tmp_path)
    file=tmp_path/'AGENTS.md'
    file.write_text('# Existing rules\nDo not touch credentials.\n')
    assert activate(tmp_path)['status']=='dry-run'
    assert START not in file.read_text()
    assert activate(tmp_path,approve=True)['status']=='active'
    assert START in file.read_text()
    assert '# Existing rules' in file.read_text()
    assert activate(tmp_path,approve=True)['status']=='already-active'
    assert deactivate(tmp_path,approve=True)['status']=='inactive'
    assert file.read_text() == '# Existing rules\nDo not touch credentials.\n'


def test_activation_cli(tmp_path):
    init_project(tmp_path)
    assert main(['activate','--project',str(tmp_path),'--approve']) == 0
    assert main(['deactivate','--project',str(tmp_path),'--approve']) == 0


def test_activate_empty_project(tmp_path):
    init_project(tmp_path)
    assert activate(tmp_path,approve=True)['status']=='active'
    assert deactivate(tmp_path,approve=True)['status']=='inactive'
    assert not (tmp_path/'AGENTS.md').exists()
