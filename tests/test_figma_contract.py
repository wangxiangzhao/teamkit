import json
import pytest
from teamkit.core import init_project
from teamkit.figma_contract import contract


def test_figma_contract_extracts_facts_not_inference(tmp_path):
    src=tmp_path/"figma.json"
    payload={"document":{"id":"0:0","name":"root","type":"DOCUMENT","children":[
        {"id":"1:1","name":"Reader","type":"CANVAS","children":[
            {"id":"2:2","name":"Home","type":"FRAME","absoluteBoundingBox":{"x":0,"y":0,"width":390,"height":844},"children":[
                {"id":"3:3","name":"Title","type":"TEXT","characters":"Continue Reading"},
                {"id":"4:4","name":"Artwork","type":"RECTANGLE","fills":[{"type":"IMAGE","imageRef":"img_1"}],
                 "reactions":[{"trigger":{"type":"ON_CLICK"},"action":{"type":"NODE","destinationId":"5:5"}}]}
            ]}
        ]}
    ]},"components":{"some":"component"}}
    src.write_text(json.dumps(payload))
    init_project(tmp_path)
    out=contract(src,module="reader",project=tmp_path,write=True)
    assert out["node_count"] == 5
    assert out["image_refs"] == ["img_1"]
    assert len(out["reactions"]) == 1
    assert any(x["text_sample"]=="Continue Reading" for x in out["nodes"] if x["type"]=="TEXT")
    assert out["verification"]["live_figma_mcp_access"] is False
    assert (tmp_path/".teamkit/contracts/figma-reader.json").is_file()
    assert contract(src,module="reader",project=tmp_path,write=True)["contract_path"]


def test_figma_contract_does_not_overwrite_new_design(tmp_path):
    init_project(tmp_path)
    src=tmp_path/"figma.json"
    src.write_text('{"document":{"id":"1","type":"FRAME","name":"Before"}}')
    contract(src,module="reader",project=tmp_path,write=True)
    src.write_text('{"document":{"id":"1","type":"FRAME","name":"After"}}')
    with pytest.raises(FileExistsError):
        contract(src,module="reader",project=tmp_path,write=True)


def test_figma_contract_rejects_unsafe_inputs(tmp_path):
    f=tmp_path/"figma.json"
    f.write_text("not-json")
    with pytest.raises(ValueError):
        contract(f,module="reader")
    f.write_text('{"document":{}}')
    with pytest.raises(ValueError):
        contract(f,module="../escape")
