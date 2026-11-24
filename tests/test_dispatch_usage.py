import json
from teamkit import dispatch
from teamkit.core import init_project
from teamkit.metrics import summary


def test_jsonl_parsing_real_token_fields():
    lines = [
        {"type": "thread.started", "thread_id": "abc"},
        {"type": "turn.completed", "usage": {"input_tokens": 100, "cached_input_tokens": 40, "output_tokens": 20}},
        {"type": "turn.completed", "usage": {"input_tokens": 60, "cached_input_tokens": 30, "output_tokens": 10}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "fixed"}},
    ]
    payload = "\n".join(json.dumps(line) for line in lines) + "\nnot-json"
    result = dispatch.parse_codex_jsonl(payload)
    assert result["token_usage"] == {"input_tokens": 160, "cached_input_tokens": 70, "output_tokens": 30}
    assert result["turns_completed"] == 2
    assert result["invalid_lines"] == 1
    assert result["final_message"] == "fixed"


def test_missing_token_usage_is_not_fabricated():
    result = dispatch.parse_codex_jsonl('{"type":"turn.completed","usage":{"input_tokens":100}}')
    assert result["token_usage"] is None
    assert result["turns_completed"] == 0


def test_codex_execution_autorecords_usage(tmp_path, monkeypatch):
    init_project(tmp_path)
    monkeypatch.setattr(dispatch.shutil, "which", lambda name: "/usr/bin/codex")
    class Completed:
        returncode = 0
        stderr = ""
        stdout = (
            '{"type":"turn.completed","usage":{"input_tokens":120,'
            '"cached_input_tokens":80,"output_tokens":25}}\n'
            '{"type":"item.completed","item":{"type":"agent_message","text":"OK"}}'
        )
    def fake_run(argv, **kwargs):
        assert argv[1:3] == ["exec", "--json"]
        assert kwargs["shell"] is False
        return Completed()
    monkeypatch.setattr(dispatch.subprocess, "run", fake_run)
    result = dispatch.run(tmp_path, "修复 SwiftUI 编译", approve=True, timeout=90)
    assert result["status"] == "completed"
    assert result["token_usage"]["input_tokens"] == 120
    assert result["metrics_saved"] == result["run_id"]
    data = summary(tmp_path)
    assert data["input_tokens"] == 120
    assert data["cached_tokens"] == 80
    assert data["output_tokens"] == 25
