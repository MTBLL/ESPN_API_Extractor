import json
import sys
from datetime import datetime
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


@pytest.fixture
def kona_playercard_fixture_data():
    """Load the kona_playercard projections fixture"""
    with open("tests/fixtures/kona_playercard_projections_fixture.json", "r") as f:
        return json.load(f)


@pytest.fixture
def corbin_carroll_kona_card(kona_playercard_fixture_data):
    # parse out the json object for corbin carroll
    return next(
        player
        for player in kona_playercard_fixture_data["players"]
        if player.get("id") == 42404
    )


@pytest.fixture
def josh_hader_kona_card(kona_playercard_fixture_data):
    # parse out the json object for jeff hader
    return next(
        player
        for player in kona_playercard_fixture_data["players"]
        if player.get("id") == 32760
    )


@pytest.fixture
def corbin_carroll_season(corbin_carroll_kona_card):
    stats = corbin_carroll_kona_card.get("player", {}).get("stats", [])
    season_ids = [
        entry.get("seasonId")
        for entry in stats
        if isinstance(entry.get("seasonId"), int)
    ]
    return max(season_ids) if season_ids else datetime.now().year


@pytest.fixture
def athlete_fixture_data():
    """Load the kona_playercard fixture"""
    with open("tests/fixtures/athlete_response_fixture.json", "r") as f:
        return json.load(f)
