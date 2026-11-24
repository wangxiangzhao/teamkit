import plistlib
from teamkit.core import init_project
from teamkit.privacy_audit import inspect_privacy
from teamkit.onboarding import onboard


def test_att_preflight_flags_missing_user_description(tmp_path):
    (tmp_path/"Feature.swift").write_text("import AppTrackingTransparency\nATTrackingManager.requestTrackingAuthorization {}")
    (tmp_path/"Info.plist").write_bytes(plistlib.dumps({"CFBundleName":"Example"}))
    init_project(tmp_path)
    result=inspect_privacy(tmp_path)
    issues={x["issue"] for x in result["findings"]}
    assert "att_usage_description_not_found" in issues
    assert result["apple_review_verified"] is False


def test_valid_manifest_and_usage_no_att_warning(tmp_path):
    (tmp_path/"Feature.swift").write_text("import AppTrackingTransparency\nATTrackingManager.requestTrackingAuthorization {}")
    (tmp_path/"Info.plist").write_bytes(plistlib.dumps({"NSUserTrackingUsageDescription":"Ads usage"}))
    (tmp_path/"PrivacyInfo.xcprivacy").write_bytes(plistlib.dumps({
        "NSPrivacyTracking":False,"NSPrivacyAccessedAPITypes":[],"NSPrivacyCollectedDataTypes":[]
    }))
    result=onboard(tmp_path)
    assert result["privacy_preflight"]["status"]=="no-static-findings"
    assert result["privacy_preflight"]["apple_review_verified"] is False


def test_malformed_manifest_is_not_reported_pass(tmp_path):
    (tmp_path/"PrivacyInfo.xcprivacy").write_text("not a plist")
    init_project(tmp_path)
    issues={x["issue"] for x in inspect_privacy(tmp_path)["findings"]}
    assert "malformed_plist" in issues
