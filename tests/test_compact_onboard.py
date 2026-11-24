import json
from teamkit.cli import main


def test_onboard_prints_compact_result_and_writes_full_evidence(tmp_path, monkeypatch, capsys):
    project=tmp_path/"project"
    project.mkdir()
    (project/"Feature.swift").write_text("struct Feature {}")
    home=tmp_path/"home"
    home.mkdir()
    from pathlib import Path
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    assert main(["onboard","--project",str(project)])==0
    output=capsys.readouterr().out
    assert len(output)<2400
    result=json.loads(output)
    assert result["capabilities"]["configured_roles"]==8
    assert result["capabilities"]["discovered_skill_count"]>=7
    report=project/".teamkit/reports/onboard.json"
    assert report.is_file()
    full=json.loads(report.read_text())
    assert "agent_skill_map" in full
    assert "native_environment" in full
    assert result["existing_codex_session"]["restart_required"] is False
