import json
import pytest
from teamkit.cli import main
from teamkit.core import init_project, sync_project, json_write
from teamkit.context_engine import discover_modules, compile_context, impact, evidence_store, evidence_status
from teamkit.orchestration import create_plan, ready_nodes, update_node, summarize_plan
from teamkit.quality import scan_assets, run_gate, check_release
from teamkit.metrics import record, summary, roas_csv
from teamkit.dispatch import prepare, run
from teamkit.skill_sources import candidates


@pytest.fixture
def project(tmp_path):
    (tmp_path / "Sources" / "Reader").mkdir(parents=True)
    (tmp_path / "Sources" / "Reader" / "ReaderView.swift").write_text("import SwiftUI\nstruct ReaderView {}")
    init_project(tmp_path)
    return tmp_path


def test_modules_context(project):
    assert 'Reader' in discover_modules(project)['modules']
    ctx = compile_context(project, 'Reader')
    assert ctx['file_count'] == 1
    assert 'ReaderView.swift' in ctx['paths'][0]['path']
    assert 'SwiftUI' not in json.dumps(ctx)
    with pytest.raises(ValueError):
        compile_context(project, '../escape')


def test_impact(project):
    assert impact(project)['changed_paths'] == []
    (project / 'Sources/Reader/ReaderView.swift').write_text('changed')
    assert 'Reader' in impact(project)['affected_modules']


def test_evidence(project):
    path = 'Sources/Reader/ReaderView.swift'
    evidence_store(project, 'unit', 'passed', source_paths=[path], report='tests', environment='A')
    assert evidence_status(project, 'unit', environment='A')['valid']
    assert not evidence_status(project, 'unit', environment='B')['valid']
    (project / path).write_text('changed')
    sync_project(project)
    assert not evidence_status(project, 'unit', environment='A')['valid']


def test_dag(project):
    plan = create_plan(project, 'TASK', '使用 Figma 设计稿实现 UI 模块')
    assert len(plan['nodes']) == 3
    assert ready_nodes(project, 'TASK')['ready'][0]['id'] == 'design'
    with pytest.raises(ValueError):
        update_node(project, 'TASK', 'implement', 'ready')
    for name in ['design','implement','review']:
        update_node(project, 'TASK', name, 'ready')
        update_node(project, 'TASK', name, 'running')
        with pytest.raises(ValueError):
            update_node(project, 'TASK', name, 'completed')
        (project / (name+'.log')).write_text('test fixture evidence')
        update_node(project, 'TASK', name, 'completed', evidence=[name+'.log'])
    assert summarize_plan(project, 'TASK')['unfinished'] == []
    with pytest.raises(FileExistsError):
        create_plan(project, 'TASK', 'duplicate')


def test_dag_budget(project):
    create_plan(project, 'TASK', 'SwiftUI code')
    update_node(project, 'TASK', 'implement', 'ready')
    update_node(project, 'TASK', 'implement', 'running', paths=['Sources/Reader'])
    with pytest.raises(ValueError):
        update_node(project, 'TASK', 'implement', 'failed', paths=['../secrets'])


def test_asset_gate(project):
    assert scan_assets(project)['status'] == 'passed'
    a = project / 'Assets.xcassets'
    a.mkdir()
    (a/'a.png').write_bytes(b'fake')
    (a/'b.png').write_bytes(b'fake')
    assert len(scan_assets(project)['duplicates']) == 1
    with pytest.raises(ValueError):
        scan_assets(project, max_bytes=1)


def test_build_gate(project):
    assert run_gate(project,'build')['status'] == 'not-run'
    json_write(project/'.teamkit/gates.json', {
        'build_command': ['python', '-c', 'print(1)'], 'test_command': None})
    assert run_gate(project,'build')['status'] == 'blocked'
    assert run_gate(project,'build',approve_command=True)['status'] == 'passed'
    assert check_release(project)['release_approved'] is False


def test_metrics_roas(project,tmp_path):
    record(project, 'TASK', input_tokens=100, output_tokens=20, cached_tokens=10)
    assert summary(project)['cached_tokens'] == 10
    with pytest.raises(ValueError):
        record(project, 'BAD', input_tokens=3, cached_tokens=4)
    csv_file=tmp_path/'data.csv'
    csv_file.write_text('cohort,spend,revenue,days_observed,currency\nA,100,120,30,USD\nB,50,75,15,USD\n')
    res=roas_csv(csv_file)
    assert res['aggregate_roas'] == '1.200000'
    assert res['complete_cohorts'] == 1


def test_codex_dry_run(project):
    assert prepare(project,'修复SwiftUI编译',module='Reader')['status']=='prepared'
    assert run(project,'修复SwiftUI编译')['status']=='dry-run'


def test_skill_sources():
    assert candidates('swiftui')['count'] > 0
    assert candidates()['install_performed'] is False


def test_cli_smoke(project):
    base=['--project',str(project)]
    assert main(['modules']+base) == 0
    assert main(['compile-context','Reader']+base) == 0
    assert main(['impact']+base) == 0
    assert main(['assets']+base) == 0
    assert main(['candidates','--capability','swiftui']) == 0
    assert main(['dag','create','TASK','swift code']+base) == 0
    assert main(['dag','ready','TASK']+base) == 0
    assert main(['metrics']+base) == 0
    assert main(['run','swift code']+base) == 0
    assert main(['release']+base) == 1
