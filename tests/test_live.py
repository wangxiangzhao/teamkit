from pathlib import Path
import pytest
from teamkit.core import init_project
from teamkit.live import attach, attach_instruction, capability_report
from teamkit.cli import main


def test_attach_existing_session_does_not_restart(tmp_path):
    init_project(tmp_path)
    result=attach(tmp_path)
    assert result["status"]=="instruction-ready"
    assert result["restart_required"] is False
    assert result["new_role_reload_guaranteed"] is False
    assert "继续原有任务" in result["prompt"]
    assert main(["attach","--project",str(tmp_path)])==0


def test_queue_is_explicit_and_validated(tmp_path):
    init_project(tmp_path)
    assert attach(tmp_path,session="test-session")["status"]=="dry-run"
    with pytest.raises(ValueError):
        attach(tmp_path,session="../unsafe",approve_queue=True)


def test_capabilities_does_not_fake_maturity(tmp_path):
    init_project(tmp_path)
    home=tmp_path/"home"
    home.mkdir()
    report=capability_report(tmp_path,home=home)
    assert report["configured_roles"]==0
    assert report["native_agent_dispatch_verified"] is False
    assert report["mature_external_skills_installed_and_tested"] is None
    agents=home/'.codex/agents'
    agents.mkdir(parents=True)
    (agents/'ios_engineer.toml').write_text('name="ios_engineer"')
    report=capability_report(tmp_path,home=home)
    assert report["configured_roles"]==1
    assert report["roles"]["ios_engineer"]["runtime_verified"] is False
