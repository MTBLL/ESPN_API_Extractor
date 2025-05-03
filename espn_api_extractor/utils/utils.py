# Helper functions for json parsing
from typing import Any, List


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
