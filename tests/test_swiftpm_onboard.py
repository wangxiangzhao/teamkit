from teamkit.onboarding import onboard
from teamkit.core import json_read


def test_swiftpm_auto_build_test_without_source_changes(tmp_path):
    (tmp_path/"Package.swift").write_text("// swift-tools-version: 5.9\n")
    testdir=tmp_path/"Tests"
    testdir.mkdir()
    (testdir/"Example.swift").write_text("import XCTest\n")
    package=(tmp_path/"Package.swift").read_bytes()
    result=onboard(tmp_path)
    assert result["status"]=="ready"
    gates=json_read(tmp_path/".teamkit/gates.json")
    assert gates["build_command"]==["swift","build","--scratch-path",".teamkit/swift-build"]
    assert gates["test_command"]==["swift","test","--scratch-path",".teamkit/swift-build"]
    assert (tmp_path/"Package.swift").read_bytes()==package
    assert not (tmp_path/".build").exists()
    assert onboard(tmp_path)["status"]=="ready"
    assert json_read(tmp_path/".teamkit/gates.json")==gates


def test_swiftpm_does_not_override_custom_gate(tmp_path):
    (tmp_path/"Package.swift").write_text("// swift-tools-version: 5.9\n")
    from teamkit.core import init_project, json_write
    init_project(tmp_path)
    cfg=json_read(tmp_path/".teamkit/gates.json")
    cfg["build_command"]=["my-custom-build"]
    json_write(tmp_path/".teamkit/gates.json",cfg)
    onboard(tmp_path)
    assert json_read(tmp_path/".teamkit/gates.json")["build_command"]==["my-custom-build"]
