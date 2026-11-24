import pytest
from teamkit.core import init_project
from teamkit.orchestration import create_plan, update_node, ready_nodes, get_plan


def test_cross_plan_conflict_and_retry(tmp_path):
    init_project(tmp_path)
    for key in ("A","B"):
        create_plan(tmp_path,key,"SwiftUI",intent="ios_code")
        update_node(tmp_path,key,"implement","ready")
    update_node(tmp_path,"A","implement","running",paths=["Sources"])
    with pytest.raises(ValueError):
        update_node(tmp_path,"B","implement","running",paths=["Sources/Reader"])
    with pytest.raises(ValueError):
        update_node(tmp_path,"A","implement","completed",evidence=["nonexistent.log"])
    update_node(tmp_path,"A","implement","failed")
    assert ready_nodes(tmp_path,"A")["ready"][0]["id"]=="implement"
    update_node(tmp_path,"B","implement","running",paths=["Sources/Reader"])
    with pytest.raises(ValueError):
        update_node(tmp_path,"B","implement","completed",evidence=["../outside"])
    p=tmp_path/"result.log"
    p.write_text("fixture output")
    update_node(tmp_path,"B","implement","completed",evidence=["result.log"])
    assert len(get_plan(tmp_path,"B")["nodes"][0]["evidence"][0]["sha256"])==64
