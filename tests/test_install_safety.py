from pathlib import Path
from teamkit.cli import install


def test_global_agent_symlink_never_followed(tmp_path):
    outside=tmp_path/'outside'
    outside.mkdir()
    home=tmp_path/'home'
    home.mkdir()
    (home/'.codex').symlink_to(outside, target_is_directory=True)
    result=install(home)
    assert result['warnings']
    assert not (outside/'agents').exists()


def test_skill_dangling_symlink_is_not_overwritten(tmp_path):
    home=tmp_path/'home'
    target=home/'.agents/skills/ios-delivery'
    target.mkdir(parents=True)
    (target/'SKILL.md').symlink_to(tmp_path/'nonexistent')
    result=install(home)
    assert result['warnings']
    assert (target/'SKILL.md').is_symlink()


def test_install_no_overwrite_and_is_idempotent(tmp_path):
    home=tmp_path/'home'
    result=install(home)
    assert result['status']=='completed'
    assert len(result['installed']) >= 14
    assert len(install(home)['skipped_existing']) == len(result['installed'])
    file=home/'.codex/agents/quality.toml'
    file.write_text('custom role')
    assert install(home)['status']=='completed'
    assert file.read_text() == 'custom role'
