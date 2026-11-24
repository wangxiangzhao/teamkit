from pathlib import Path
import json
import os
from teamkit.cli import main
from teamkit.core import ROLES


def test_one_command_installs_roles_skills_without_overwriting(tmp_path, monkeypatch, capsys):
    home=tmp_path/'home'
    home.mkdir()
    project=tmp_path/'project'
    project.mkdir()
    (project/'Main.swift').write_text('struct Main {}')
    monkeypatch.setenv('HOME',str(home))
    monkeypatch.setattr(Path,'home',classmethod(lambda cls: home))
    assert main(['onboard','--project',str(project)])==0
    result=json.loads(capsys.readouterr().out)
    assert result['status']=='ready'
    assert result['capabilities']['configured_roles']==8
    assert result['capabilities']['discovered_skill_count']>=6
    assert (home/'.codex/agents/product.toml').exists()
    assert (home/'.agents/skills/ios-delivery/SKILL.md').exists()
    assert result['existing_codex_session']['restart_required'] is False
    original=home/'.codex/agents/product.toml'
    original.write_text('custom role')
    assert main(['onboard','--project',str(project)])==0
    assert original.read_text()=='custom role'


def test_dry_run_does_not_change_home_or_project(tmp_path, monkeypatch, capsys):
    home=tmp_path/'home'
    home.mkdir()
    project=tmp_path/'project'
    project.mkdir()
    (project/'Main.swift').write_text('struct Main {}')
    monkeypatch.setattr(Path,'home',classmethod(lambda cls:home))
    assert main(['onboard','--project',str(project),'--dry-run'])==0
    result=json.loads(capsys.readouterr().out)
    assert result['global_install']['status']=='dry-run'
    assert not (home/'.codex').exists()
    assert not (project/'.teamkit').exists()
    assert not (project/'AGENTS.md').exists()
