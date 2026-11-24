import pytest
from teamkit.core import init_project
from teamkit import activation


def test_merge_metadata_failure_restores_original(tmp_path, monkeypatch):
    init_project(tmp_path)
    path=tmp_path/'AGENTS.md'
    original=b'# Keep my original rules\r\n'
    path.write_bytes(original)
    real=activation.Path.write_text
    def fail_metadata(self, *args, **kwargs):
        if self.name=='agents-merge.json':
            raise PermissionError('simulated manifest write failure')
        return real(self, *args, **kwargs)
    monkeypatch.setattr(activation.Path, 'write_text', fail_metadata)
    with pytest.raises(PermissionError):
        activation.activate(tmp_path, approve=True)
    assert path.read_bytes()==original
    assert not (tmp_path/'.teamkit/agents-merge.json').exists()


def test_merge_failure_without_original_removes_new_file(tmp_path, monkeypatch):
    init_project(tmp_path)
    real=activation.Path.write_text
    def fail_metadata(self, *args, **kwargs):
        if self.name=='agents-merge.json':
            raise PermissionError('simulated')
        return real(self, *args, **kwargs)
    monkeypatch.setattr(activation.Path, 'write_text', fail_metadata)
    with pytest.raises(PermissionError):
        activation.activate(tmp_path, approve=True)
    assert not (tmp_path/'AGENTS.md').exists()
