from pathlib import Path
from teamkit import __file__ as package_file
from teamkit.cli import install


def test_swiftui_pro_complete_vendor_bundle(tmp_path):
    skill = Path(package_file).parent / "assets/skills/swiftui-pro"
    assert (skill / "SKILL.md").is_file()
    assert (skill / "LICENSE").is_file()
    assert (skill / "UPSTREAM.json").is_file()
    references = sorted((skill / "references").glob("*.md"))
    assert len(references) >= 10
    head = (skill / "SKILL.md").read_text(encoding="utf-8")
    assert "name: swiftui-pro" in head
    assert "MIT" in (skill / "LICENSE").read_text(encoding="utf-8")
    for reference in references:
        assert reference.stat().st_size > 100
    result = install(tmp_path)
    assert result["status"] == "completed"
    dest = tmp_path / ".agents/skills/swiftui-pro"
    assert (dest / "references/navigation.md").read_bytes() == (skill / "references/navigation.md").read_bytes()
    custom = dest / "references/navigation.md"
    custom.write_text("project custom override", encoding="utf-8")
    second = install(tmp_path)
    assert second["status"] == "completed"
    assert custom.read_text(encoding="utf-8") == "project custom override"
