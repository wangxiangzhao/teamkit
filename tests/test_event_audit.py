from teamkit.core import init_project
from teamkit.event_audit import inventory_events


def test_literal_events_are_discovered_without_code_change(tmp_path):
    code=tmp_path/"Main.swift"
    original='''import FirebaseAnalytics
func sample() {
 Analytics.logEvent("reader_open", parameters: nil)
 analytics.track(event: "chapter_complete")
}
'''
    code.write_text(original)
    init_project(tmp_path)
    result=inventory_events(tmp_path)
    assert {x["event"] for x in result["literal_events"]} == {"reader_open", "chapter_complete"}
    assert all(x["line"] > 0 for x in result["literal_events"])
    assert code.read_text()==original
    assert result["downstream_delivery_verified"] is False
    assert (tmp_path/".teamkit/reports/event-inventory.json").is_file()


def test_dynamic_events_are_not_falsely_inferred(tmp_path):
    (tmp_path/"Main.swift").write_text('func track(name: String) { tracker.track(name) }')
    init_project(tmp_path)
    result=inventory_events(tmp_path)
    assert result["distinct_literal_event_names"] == 0
    assert result["potential_dynamic_events"] == ["Main.swift"]
    assert result["status"] == "partial"


def test_inventory_budget_validation(tmp_path):
    init_project(tmp_path)
    import pytest
    with pytest.raises(ValueError):
        inventory_events(tmp_path, byte_limit=1)
