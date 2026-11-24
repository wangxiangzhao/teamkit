from teamkit.core import init_project
from teamkit.audit import audit_project, safe_maintain
from teamkit.onboarding import onboard


def test_audit_never_claims_external_verification(tmp_path):
    init_project(tmp_path)
    result=audit_project(tmp_path)
    assert result['status']=='passed'
    assert result['commercial_ready'] is False
    assert result['runtime_integration_verified'] is False


def test_autonomous_index_upkeep(tmp_path):
    (tmp_path/'Feature.swift').write_text('struct Feature {}')
    init_project(tmp_path)
    (tmp_path/'Feature.swift').write_text('struct Feature { let id = 1 }')
    assert any(i['code']=='stale_index' for i in audit_project(tmp_path)['findings'])
    result=safe_maintain(tmp_path)
    assert result['index_refreshed'] is True
    assert not any(i['code']=='stale_index' for i in audit_project(tmp_path)['findings'])


def test_onboarding_runs_safe_audit_without_user_steps(tmp_path):
    (tmp_path/'Feature.swift').write_text('struct Feature {}')
    result=onboard(tmp_path)
    assert result['self_audit']['status']=='passed'


def test_corrupt_merge_block_requires_no_automatic_writes(tmp_path):
    onboard(tmp_path)
    file=tmp_path/'AGENTS.md'
    file.write_text(file.read_text().replace('Execute simple tasks','Do anything'))
    before=file.read_bytes()
    assert audit_project(tmp_path)['status']=='failed'
    assert safe_maintain(tmp_path)['status']=='failed'
    assert file.read_bytes()==before
