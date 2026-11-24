from teamkit.core import init_project
from teamkit.cli import install
from teamkit.skill_audit import audit_skills


def test_audit_complete_installed_skill_bundles(tmp_path):
    home=tmp_path/"home"
    project=tmp_path/"project"
    project.mkdir()
    init_project(project)
    install(home)
    report=audit_skills(project,home=home)
    assert report["status"]=="passed",report["errors"]
    assert report["skills_checked"]>=7
    mature=next(x for x in report["reports"] if x["name"]=="swiftui-pro")
    assert mature["references_checked"]>=10
    assert mature["runtime_verified"] is False


def test_partial_audit_does_not_touch_user_skill(tmp_path):
    project=tmp_path/"project"
    project.mkdir()
    init_project(project)
    root=project/".agents/skills/custom"
    root.mkdir(parents=True)
    file=root/"SKILL.md"
    file.write_text("---\nname: custom\ndescription: custom\n---\nSee references/missing.md")
    original=file.read_bytes()
    report=audit_skills(project,home=tmp_path)
    assert report["status"]=="partial"
    assert report["errors"]
    assert file.read_bytes()==original
