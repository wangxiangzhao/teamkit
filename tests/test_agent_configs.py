from pathlib import Path
import tomllib
import teamkit
from teamkit import __version__


def test_codex_role_schema():
    root=Path(teamkit.__file__).parent/'assets'/'agents'
    paths=sorted(root.glob('*.toml'))
    assert len(paths)==8
    for path in paths:
        item=tomllib.loads(path.read_text(encoding='utf-8'))
        assert item['name']==path.stem
        assert item['description'].strip()
        assert item['developer_instructions'].strip()
        assert 'model' not in item


def test_version_is_one():
    assert __version__=='1.0.0'
