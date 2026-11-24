from teamkit.core import init_project, json_read
from teamkit.project_inspect import inspect_project
from teamkit.onboarding import onboard


def test_framework_hints_and_ios_deployment_target(tmp_path):
    folder=tmp_path/"Sources"
    folder.mkdir()
    code=folder/"ContentView.swift"
    code.write_text("import SwiftUI\nimport StoreKit\nstruct ContentView {}\n")
    proj=tmp_path/"App.xcodeproj"
    proj.mkdir()
    (proj/"project.pbxproj").write_text("IPHONEOS_DEPLOYMENT_TARGET = 17.0;")
    before=code.read_bytes()
    result=onboard(tmp_path)
    hints=result["project_insights"]
    assert hints["framework_references"]["swiftui"]==["Sources/ContentView.swift"]
    assert hints["framework_references"]["iap"]==["Sources/ContentView.swift"]
    assert hints["deployment_targets"]["IPHONEOS_DEPLOYMENT_TARGET"]==["17.0"]
    assert hints["accuracy"].startswith("references only")
    assert code.read_bytes()==before
    assert json_read(tmp_path/".teamkit/capability-hints.json")["source_changes"] is False


def test_swiftpm_ios_platform_detection(tmp_path):
    (tmp_path/"Package.swift").write_text(
        "// swift-tools-version: 5.9\nimport PackageDescription\n"
        "let package=Package(name: \"A\", platforms: [.iOS(.v17)])\n"
    )
    init_project(tmp_path)
    hints=inspect_project(tmp_path)
    assert hints["deployment_targets"]["swiftpm_ios"]==["17.0"]
    assert hints["framework_references"]=={}
