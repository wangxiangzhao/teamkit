from pathlib import Path
import pytest
from teamkit.onboarding import onboard, detach


def _scheme(root, name):
    path=root/'Example.xcodeproj/xcshareddata/xcschemes'/f'{name}.xcscheme'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('<Scheme><BuildAction><BuildActionEntries><BuildActionEntry/></BuildActionEntries></BuildAction></Scheme>')
    return path


def test_onboarding_one_command_preserves_project(tmp_path):
    source=tmp_path/'Main.swift'
    source.write_text('let a = 1')
    old=tmp_path/'AGENTS.md'
    old.write_text('# Existing rules\nDo not change signing.\n')
    _scheme(tmp_path,'Example')
    preview=onboard(tmp_path,dry_run=True)
    assert preview['status']=='dry-run'
    assert not (tmp_path/'.teamkit').exists()
    result=onboard(tmp_path)
    assert result['status']=='ready'
    assert result['xcode_scheme']['scheme']=='Example'
    assert source.read_text()=='let a = 1'
    assert 'Do not change signing.' in old.read_text()
    assert onboard(tmp_path)['status']=='ready'
    detach(tmp_path)
    assert old.read_text()=='# Existing rules\nDo not change signing.\n'
    assert source.read_text()=='let a = 1'
    assert (tmp_path/'.teamkit').exists()


def test_onboarding_ambiguous_schemes_not_guessed(tmp_path):
    _scheme(tmp_path,'A')
    _scheme(tmp_path,'B')
    result=onboard(tmp_path)
    assert result['xcode_scheme'] is None
    assert result['xcode_scheme_requires_review']


def test_reject_symlink_agents(tmp_path):
    other=tmp_path/'other.txt'
    other.write_text('private')
    (tmp_path/'AGENTS.md').symlink_to(other)
    with pytest.raises(ValueError):
        onboard(tmp_path)
    assert other.read_text()=='private'


def test_refuse_existing_foreign_metadata(tmp_path):
    folder=tmp_path/'.teamkit'
    folder.mkdir()
    (folder/'custom.txt').write_text('mine')
    with pytest.raises(FileExistsError):
        onboard(tmp_path)
    assert (folder/'custom.txt').read_text()=='mine'
from teamkit.cli import main

def test_onboarding_cli(tmp_path):
    (tmp_path/'Feature.swift').write_text('struct Feature {}')
    assert main(['onboard','--project',str(tmp_path),'--dry-run'])==0
    assert main(['onboard','--project',str(tmp_path)])==0
    assert main(['detach','--project',str(tmp_path)])==0
