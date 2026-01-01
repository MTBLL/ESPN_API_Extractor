import json
import sys
from pathlib import Path

import pytest

# Ensure the project root is importable during tests
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def league_response_fixture():
    """Load the league_response.json fixture for reuse across tests."""
    fixture_path = PROJECT_ROOT / "tests" / "fixtures" / "league_response.json"
    with fixture_path.open() as f:
        return json.load(f)
