from pathlib import Path
import pytest
from teamkit.onboarding import onboard, detach


def _scheme(root, name):
    path=root/'Example.xcodeproj/xcshareddata/xcschemes'/f'{name}.xcscheme'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('<Scheme><BuildAction><BuildActionEntries><BuildActionEntry/></BuildActionEntries></BuildAction></Scheme>')
    return path


def test_onboarding_one_command_preserves_project(tmp_path):
    source=tmp_path/'Main.swift'
    source.write_text('let a = 1')
    old=tmp_path/'AGENTS.md'
    old.write_text('# Existing rules\nDo not change signing.\n')
    _scheme(tmp_path,'Example')
    preview=onboard(tmp_path,dry_run=True)
    assert preview['status']=='dry-run'
    assert not (tmp_path/'.teamkit').exists()
    result=onboard(tmp_path)
    assert result['status']=='ready'
    assert result['xcode_scheme']['scheme']=='Example'
    assert source.read_text()=='let a = 1'
    from teamkit.core import check_project
    assert check_project(tmp_path)['status']=='passed'
    assert 'Do not change signing.' in old.read_text()
    assert onboard(tmp_path)['status']=='ready'
    detach(tmp_path)
    assert old.read_text()=='# Existing rules\nDo not change signing.\n'
    assert source.read_text()=='let a = 1'
    assert (tmp_path/'.teamkit').exists()


def test_onboarding_ambiguous_schemes_not_guessed(tmp_path):
    _scheme(tmp_path,'A')
    _scheme(tmp_path,'B')
    result=onboard(tmp_path)
    assert result['xcode_scheme'] is None
    assert result['xcode_scheme_requires_review']


def test_reject_symlink_agents(tmp_path):
    other=tmp_path/'other.txt'
    other.write_text('private')
    (tmp_path/'AGENTS.md').symlink_to(other)
    with pytest.raises(ValueError):
        onboard(tmp_path)
    assert other.read_text()=='private'


def test_refuse_existing_foreign_metadata(tmp_path):
    folder=tmp_path/'.teamkit'
    folder.mkdir()
    (folder/'custom.txt').write_text('mine')
    with pytest.raises(FileExistsError):
        onboard(tmp_path)
    assert (folder/'custom.txt').read_text()=='mine'
from teamkit.cli import main

def test_onboarding_cli(tmp_path, monkeypatch):
    install_home = tmp_path / "install-home"
    install_home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: install_home))
    (tmp_path/'Feature.swift').write_text('struct Feature {}')
    assert main(['onboard','--project',str(tmp_path),'--dry-run'])==0
    assert main(['onboard','--project',str(tmp_path)])==0
    assert main(['detach','--project',str(tmp_path)])==0


def test_autoconfig_build_only_for_explicit_ios_scheme(tmp_path):
    _scheme(tmp_path,'Example')
    pbx=tmp_path/'Example.xcodeproj/project.pbxproj'
    pbx.write_text('SDKROOT = iphoneos;')
    from teamkit.core import json_read
    onboard(tmp_path)
    gates=json_read(tmp_path/'.teamkit/gates.json')
    assert gates['build_command'][-1]=='build'
    assert 'generic/platform=iOS Simulator' in gates['build_command']
    argv = gates["build_command"]
    assert argv[argv.index("-derivedDataPath") + 1] == ".teamkit/xcode-derived"
    assert gates['test_command'] is None


def _workspace(root, name):
    workspace = root / f"{name}.xcworkspace"
    workspace.mkdir()
    (workspace / "contents.xcworkspacedata").write_text(
        '<Workspace><FileRef location="group:Example.xcodeproj"/></Workspace>'
    )
    return workspace


def test_workspace_uses_shared_project_scheme_and_preserves_custom_gate(tmp_path):
    from teamkit.core import json_read, json_write

    scheme = _scheme(tmp_path, "Example")
    (tmp_path / "Example.xcodeproj/project.pbxproj").write_text("SDKROOT = iphoneos;")
    workspace = _workspace(tmp_path, "Product")
    contents_before = (workspace / "contents.xcworkspacedata").read_bytes()
    result = onboard(tmp_path)
    assert result["xcode_scheme"]["source"] == scheme.relative_to(tmp_path).as_posix()
    config = tmp_path / ".teamkit/gates.json"
    gates = json_read(config)
    assert gates["build_command"][:5] == ["xcodebuild", "-workspace", "Product.xcworkspace", "-scheme", "Example"]
    gates["build_command"] = ["custom-build"]
    json_write(config, gates)
    onboard(tmp_path)
    assert json_read(config)["build_command"] == ["custom-build"]
    assert (workspace / "contents.xcworkspacedata").read_bytes() == contents_before


def test_multiple_workspaces_are_ambiguous_even_with_swift_package(tmp_path):
    from teamkit.core import json_read

    _scheme(tmp_path, "Example")
    _workspace(tmp_path, "Product")
    _workspace(tmp_path, "Alternate")
    (tmp_path / "Package.swift").write_text("// mixed Xcode/SPM project")
    result = onboard(tmp_path)
    assert result["xcode_scheme"] is None
    assert result["xcode_scheme_requires_review"]
    assert json_read(tmp_path / ".teamkit/gates.json")["build_command"] is None


def test_skip_symlinked_shared_scheme_directory(tmp_path):
    scheme = _scheme(tmp_path, "Example")
    schemes = scheme.parent
    moved = schemes.rename(tmp_path / "outside-schemes")
    schemes.symlink_to(moved, target_is_directory=True)
    assert onboard(tmp_path)["xcode_scheme"] is None
