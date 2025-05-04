# Helper functions for json parsing
import json
from typing import Any, List

from espn_api_extractor.models import PlayerModel


def json_parsing(obj, key) -> Any | None:
    """Recursively pull values of specified key from nested JSON."""
    arr = []

    def extract(obj, arr, key) -> List:
        """Return all matching values in an object."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict)) or (
                    isinstance(v, (list)) and v and isinstance(v[0], (list, dict))
                ):
                    extract(v, arr, key)
                elif k == key:
                    arr.append(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    results = extract(obj, arr, key)
    return results[0] if len(results) > 0 else None


def write_models_to_json(
    models: List[PlayerModel], output_path: str, pretty: bool = False
) -> None:
    """
    Write a list of Pydantic models to a JSON file.

    Args:
        models: List of PlayerModel instances to serialize
        output_path: Path to write the JSON output
        pretty: Whether to pretty-print the JSON output with indentation
    """
    if pretty:
        # Pretty print with indentation
        json_data = "[\n"
        for i, model in enumerate(models):
            model_json = model.model_dump_json(indent=2)
            json_data += "  " + model_json.replace("\n", "\n  ")
            if i < len(models) - 1:
                json_data += ",\n"
            else:
                json_data += "\n"
        json_data += "]\n"

        with open(output_path, "w") as f:
            f.write(json_data)
    else:
        # Use standard JSON serialization
        json_list = [model.model_dump() for model in models]
        with open(output_path, "w") as f:
            json.dump(json_list, f, indent=2)
