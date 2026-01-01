import os

import requests

import pytest

from espn_api_extractor.requests.constants import FantasySports
from espn_api_extractor.requests.exceptions import (
    ESPNAccessDenied,
    ESPNInvalidLeague,
    ESPNUnknownError,
)
from espn_api_extractor.requests.fantasy_requests import EspnFantasyRequests


@pytest.fixture
def espn_request():
    # Using empty cookies since we're doing an actual API call
    # You may need to modify this if authentication is required
    cookies = {}
    year = int(os.getenv("ESPN_TEST_YEAR", "2025"))
    league_id = int(os.getenv("ESPN_TEST_LEAGUE_ID", "10998"))

    return EspnFantasyRequests(
        sport=FantasySports.MLB,  # Use mlb instead of baseball
        year=year,
        league_id=league_id,
        cookies=cookies,
    )


@pytest.mark.integration
def test_get_pro_players_structure(espn_request):
    """
    End-to-end test that calls the actual ESPN API to verify
    that the player data structure contains the expected fields.
    """
    # Make the actual API call
    try:
        players = espn_request.get_pro_players()
    except (
        ESPNAccessDenied,
        ESPNInvalidLeague,
        ESPNUnknownError,
        requests.exceptions.RequestException,
    ) as exc:
        pytest.skip(f"ESPN API not accessible: {exc}")

    # Verify we got a response with players
    assert isinstance(players, list), "Expected a list of players"
    assert len(players) > 0, "Expected at least one player in the response"

    # Get the first player to validate structure
    player = players[0]

    # Test that the required fields exist
    required_fields = [
        "defaultPositionId",
        "eligibleSlots",
        "firstName",
        "fullName",
        "id",
        "lastName",
        "proTeamId",
    ]

    for field in required_fields:
        assert field in player, f"{field} field is missing"

    # Test the data types of each field
    assert isinstance(player["defaultPositionId"], int), (
        "defaultPositionId should be an integer"
    )
    assert isinstance(player["eligibleSlots"], list), "eligibleSlots should be a list"
    assert all(isinstance(slot, int) for slot in player["eligibleSlots"]), (
        "eligibleSlots should contain integers"
    )
    assert isinstance(player["firstName"], str), "firstName should be a string"
    assert isinstance(player["fullName"], str), "fullName should be a string"
    assert isinstance(player["id"], int), "id should be an integer"
    assert isinstance(player["lastName"], str), "lastName should be a string"
    assert isinstance(player["proTeamId"], int), "proTeamId should be an integer"

    # Additional validation - check that the name fields match the expected pattern
    assert player["fullName"] == f"{player['firstName']} {player['lastName']}", (
        "fullName should be firstName + lastName"
    )

    # Print sample data for reference/debugging
    print(f"Example player data: {player}")
    print(f"Total players retrieved: {len(players)}")


@pytest.mark.integration
def test_get_player_cards_structure(espn_request):
    try:
        players = espn_request.get_player_cards(player_ids=[39832, 42404])
    except (
        ESPNAccessDenied,
        ESPNInvalidLeague,
        ESPNUnknownError,
        requests.exceptions.RequestException,
    ) as exc:
        pytest.skip(f"ESPN API not accessible: {exc}")
    assert len(players) > 0, "Expected at least one player in the response"

    # Get the first player to validate structure
    player = players["players"][0]

    # Test that the required fields exist
    required_fields = [
        "defaultPositionId",
        "eligibleSlots",
        "firstName",
        "fullName",
        "id",
        "lastName",
        "proTeamId",
    ]

    for field in required_fields:
        assert field in player["player"], f"{field} field is missing"
