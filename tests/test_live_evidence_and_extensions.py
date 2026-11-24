from teamkit.core import init_project, extend_project, route_task
from teamkit.context_engine import evidence_store, evidence_status
from teamkit.skill_resolver import resolve_task
from teamkit.dispatch import prepare


def test_evidence_invalidates_without_sync(tmp_path):
    p=tmp_path/"A.swift"
    p.write_text("let a=1")
    init_project(tmp_path)
    evidence_store(tmp_path,"test","passed",source_paths=["A.swift"],report="test")
    assert evidence_status(tmp_path,"test")["valid"]
    p.write_text("let a=2")
    assert not evidence_status(tmp_path,"test")["valid"]
    p.write_text("let a=1")
    (tmp_path/"B.swift").write_text("let b=2")
    assert not evidence_status(tmp_path,"test")["valid"]


def test_project_extension_is_selected_for_task(tmp_path):
    init_project(tmp_path)
    extend_project(tmp_path,"ios_engineer","reader-flow")
    route=route_task("SwiftUI",explicit_intent="ios_code")
    result=resolve_task(tmp_path,route,home=tmp_path)
    assert "reader-flow" in [s["name"] for s in result["roles"]["ios_engineer"]["skills"]]
    assert "reader-flow" not in [s["name"] for s in result["roles"]["quality"]["skills"]]
    assert "reader-flow" in prepare(tmp_path,"SwiftUI",intent="ios_code")["prompt"]
