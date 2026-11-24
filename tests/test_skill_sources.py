from teamkit.skill_sources import candidates
from teamkit.cli import main


def test_catalog_lists_candidates_without_install():
    result = candidates()
    assert result["install_performed"] is False
    assert result["count"] >= 5
    assert all(item["repository"].startswith("https://github.com/") for item in result["candidates"])


def test_filter_skills_by_capability(capsys):
    result = candidates("swiftui")
    assert any(item["id"] == "twostraws-swiftui" for item in result["candidates"])
    assert all("swiftui" in item["capabilities"] for item in result["candidates"])
    assert main(["candidates", "--capability", "swiftui"]) == 0
    assert "twostraws-swiftui" in capsys.readouterr().out
