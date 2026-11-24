from pathlib import Path

import pytest

from teamkit.cli import install, main
from teamkit.core import (ROLES, check_project, checkpoint, init_project,
                          project_status, route_task, sync_project, task_plan)


def test_eight_roles():
    assert len(ROLES) == 8
    assert "quality" in ROLES


def test_project_lifecycle(tmp_path):
    (tmp_path / "Reader.swift").write_text("struct Reader {}", encoding="utf-8")
    (tmp_path / "App.xcodeproj").mkdir()
    result = init_project(tmp_path)
    assert result["files_indexed"] == 1
    assert project_status(tmp_path)["detected"]["swift_files"] == 1
    assert project_status(tmp_path)["detected"]["xcodeproj"] == ["App.xcodeproj"]
    assert check_project(tmp_path)["status"] == "passed"
    (tmp_path / "Reader.swift").write_text("struct Reader { var id: Int }", encoding="utf-8")
    assert check_project(tmp_path)["status"] == "failed"
    delta = sync_project(tmp_path)
    assert delta["changed"] == ["Reader.swift"]
    assert check_project(tmp_path)["status"] == "passed"
    assert sync_project(tmp_path)["counts"] == {"added": 0, "removed": 0, "changed": 0}


def test_no_overwrite(tmp_path):
    (tmp_path / "Main.swift").write_text("// source")
    init_project(tmp_path)
    with pytest.raises(FileExistsError):
        init_project(tmp_path)
    assert (tmp_path / "Main.swift").read_text() == "// source"


def test_route_and_plan():
    route = route_task("使用 Figma 设计稿实现一个 UI 模块")
    assert route["intent"] == "ui_module"
    plan = task_plan(route)
    assert [x["id"] for x in plan["steps"]] == ["design", "implement", "review"]
    assert route_task("分析 D30 ROAS 投放回收")["primary_agent"] == "growth"
    assert route_task("修复 SwiftUI 编译错误")["primary_agent"] == "ios_engineer"
    assert route_task("some unspecified task")["semantic_review_required"]


def test_checkpoint(tmp_path):
    init_project(tmp_path)
    state = checkpoint(tmp_path, "TASK-01", "running", "started")
    assert state["status"] == "running"
    later = checkpoint(tmp_path, "TASK-01", "completed", "done")
    assert len(later["history"]) == 2
    with pytest.raises(ValueError):
        checkpoint(tmp_path, "../escape", "running")


def test_install_is_idempotent_and_preserves_custom(tmp_path):
    results = install(tmp_path)
    assert len(results["installed"]) == 14
    assert len(install(tmp_path)["skipped_existing"]) == 14
    agent = tmp_path / ".codex/agents/product.toml"
    agent.write_text("custom", encoding="utf-8")
    install(tmp_path)
    assert agent.read_text() == "custom"


def test_symlink_not_followed(tmp_path):
    outside = tmp_path.parent / "outside-project.swift"
    outside.write_text("secret")
    (tmp_path / "link.swift").symlink_to(outside)
    result = init_project(tmp_path)
    assert result["files_indexed"] == 0


def test_cli_return_codes(tmp_path, capsys):
    assert main(["init", "--project", str(tmp_path)]) == 0
    assert main(["check", "--project", str(tmp_path)]) == 0
    assert main(["init", "--project", str(tmp_path)]) == 2
    assert main(["checkpoint", "T-1", "running", "--project", str(tmp_path)]) == 0
    assert main(["resume", "T-1", "--project", str(tmp_path)]) == 0


def test_resume_rejects_path_traversal(tmp_path):
    init_project(tmp_path)
    assert main(["resume", "../escape", "--project", str(tmp_path)]) == 2


def test_project_skill_extension_and_context(tmp_path):
    (tmp_path / "Reader.swift").write_text("struct Reader {}")
    init_project(tmp_path)
    assert main(["extend", "ios_engineer", "reader-workflow", "--project", str(tmp_path)]) == 0
    path = tmp_path / ".agents/skills/reader-workflow/SKILL.md"
    assert path.exists()
    path.write_text("custom content")
    assert main(["extend", "ios_engineer", "reader-workflow", "--project", str(tmp_path)]) == 0
    assert path.read_text() == "custom content"
    assert main(["skills", "--project", str(tmp_path)]) == 0
    assert main(["context", "Reader", "--project", str(tmp_path)]) == 0
    assert main(["extend", "unknown_agent", "invalid", "--project", str(tmp_path)]) == 2
    assert main(["extend", "ios_engineer", "../bad", "--project", str(tmp_path)]) == 2


def test_check_detects_unindexed_new_files(tmp_path):
    init_project(tmp_path)
    (tmp_path / "New.swift").write_text("let new = true")
    result = check_project(tmp_path)
    assert result["status"] == "failed"
    assert any(e["reason"] == "new_since_index" for e in result["errors"])
    assert result["checks"]["references"] == "not-run"
