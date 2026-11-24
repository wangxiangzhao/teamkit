from pathlib import Path
from teamkit.core import init_project, route_task
from teamkit.cli import install, main
from teamkit.skill_resolver import resolve


def test_role_skill_map_from_bundled_files(tmp_path, capsys):
    project=tmp_path/'project'
    project.mkdir()
    init_project(project)
    home=tmp_path/'home'
    install(home)
    result=resolve(project, home=home, persist=True)
    assert result['skills_found'] >= 6
    assert result['agents']['ios_engineer']['available_skills']
    assert result['agents']['quality']['available_skills']
    assert result['agents']['ios_engineer']['runtime_verified'] is False
    assert (project/'.teamkit/skill-map.json').exists()
    assert main(['resolve-skills','--project',str(project)]) == 0


def test_routes_use_bundled_skill_names(tmp_path):
    project=tmp_path/'project'
    project.mkdir()
    init_project(project)
    all_routes=[
        route_task("用figma还原UI模块"),
        route_task("修复swiftui代码崩溃"),
        route_task("检查App Store审核安全风险"),
        route_task("分析D30 ROAS投放回收"),
    ]
    names=set(p.parent.name for p in (Path(__file__).resolve().parents[1]/
          'src/teamkit/assets/skills').glob('*/SKILL.md'))
    for route in all_routes:
        assert set(route['skills']).issubset(names)
