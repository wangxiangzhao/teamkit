from pathlib import Path
from teamkit.cli import install
from teamkit import __file__ as pkgfile


def test_safe_legacy_repair(tmp_path):
    source=Path(pkgfile).parent/'assets/agents/ios_engineer.toml'
    old=source.read_text().split('\n',1)[1]
    path=tmp_path/'.codex/agents/ios_engineer.toml'
    path.parent.mkdir(parents=True)
    path.write_text(old)
    assert install(tmp_path)['repaired_legacy_roles']==[]
    assert path.read_text()==old
    assert str(path) in install(tmp_path,dry_run=True,repair_legacy=True)['repaired_legacy_roles']
    assert path.read_text()==old
    assert str(path) in install(tmp_path,repair_legacy=True)['repaired_legacy_roles']
    assert path.read_text()==source.read_text()
    assert (tmp_path/'.codex/teamkit-backups/agents/ios_engineer.toml').read_text()==old


def test_never_overwrite_custom(tmp_path):
    install(tmp_path)
    path=tmp_path/'.codex/agents/product.toml'
    path.write_text('custom')
    assert install(tmp_path,repair_legacy=True)['repaired_legacy_roles']==[]
    assert path.read_text()=='custom'
