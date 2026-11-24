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


def test_ready_counts_running_work_in_the_same_plan(tmp_path):
    init_project(tmp_path)
    create_plan(tmp_path, "UI", "Reader", intent="ui_module")
    update_node(tmp_path, "UI", "design", "ready")
    update_node(tmp_path, "UI", "design", "running", paths=["Design"])
    assert ready_nodes(tmp_path, "UI", max_running=1)["slots"] == 0
    with pytest.raises(ValueError, match="path ownership"):
        update_node(tmp_path, "UI", "design", "failed", paths=["Sources"])


def test_changed_evidence_blocks_completion_and_can_be_replaced(tmp_path):
    from teamkit.orchestration import summarize_plan

    init_project(tmp_path)
    create_plan(tmp_path, "UI", "Reader", intent="ui_module")
    evidence = tmp_path / "design.log"
    evidence.write_text("first design")
    update_node(tmp_path, "UI", "design", "ready")
    update_node(tmp_path, "UI", "design", "running")
    update_node(tmp_path, "UI", "design", "completed", evidence=["design.log"])
    update_node(tmp_path, "UI", "implement", "ready")
    update_node(tmp_path, "UI", "implement", "running")

    evidence.write_text("updated design")
    assert summarize_plan(tmp_path, "UI")["stale_completions"] == ["design"]
    with pytest.raises(ValueError, match="current completion evidence"):
        update_node(tmp_path, "UI", "implement", "completed", evidence=["design.log"])
    with pytest.raises(ValueError, match="running dependent"):
        update_node(tmp_path, "UI", "design", "ready")
    update_node(tmp_path, "UI", "implement", "failed")
    update_node(tmp_path, "UI", "design", "ready")
    update_node(tmp_path, "UI", "design", "running")
    update_node(tmp_path, "UI", "design", "completed", evidence=["design.log"])

    assert summarize_plan(tmp_path, "UI")["stale_completions"] == []
    assert ready_nodes(tmp_path, "UI")["ready"][0]["id"] == "implement"
