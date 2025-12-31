import json
from unittest.mock import MagicMock

from espn_api_extractor.utils.utils import write_models_to_json


def test_write_models_to_json_writes_file(tmp_path):
    model_a = MagicMock()
    model_a.model_dump.return_value = {"id": 1, "name": "A"}
    model_b = MagicMock()
    model_b.model_dump.return_value = {"id": 2, "name": "B"}

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    file_name = "players.json"

    write_models_to_json([model_a, model_b], str(output_dir), file_name)

    output_file = output_dir / file_name
    assert output_file.exists()

    with output_file.open() as f:
        data = json.load(f)

    assert data == [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
    model_a.model_dump.assert_called_once_with()
    model_b.model_dump.assert_called_once_with()
