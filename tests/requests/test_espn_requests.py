import datetime
import pytest

from espn_api_extractor.requests.fantasy_requests import EspnFantasyRequests
from espn_api_extractor.utils.logger import Logger


@pytest.fixture
def espn_request():
    # Using empty cookies since we're doing an actual API call
    # You may need to modify this if authentication is required
    cookies = {}
    # Get the current year
    current_year = datetime.datetime.now().year
    
    return EspnFantasyRequests(
        sport="mlb",  # Use mlb instead of baseball
        year=current_year,  # Use the current year
        league_id=None,  # Not needed for get_pro_players
        cookies=cookies,
        logger=Logger("test", debug=False),
    )


def test_get_pro_players_structure(espn_request):
    """
    End-to-end test that calls the actual ESPN API to verify 
    that the player data structure contains the expected fields.
    """
    # Make the actual API call
    players = espn_request.get_pro_players()
    
    # Verify we got a response with players
    assert isinstance(players, list), "Expected a list of players"
    assert len(players) > 0, "Expected at least one player in the response"
    
    # Get the first player to validate structure
    player = players[0]
    
    # Test that the required fields exist
    required_fields = [
        'defaultPositionId', 
        'eligibleSlots', 
        'firstName', 
        'fullName', 
        'id', 
        'lastName', 
        'proTeamId'
    ]
    
    for field in required_fields:
        assert field in player, f"{field} field is missing"
    
    # Test the data types of each field
    assert isinstance(player['defaultPositionId'], int), "defaultPositionId should be an integer"
    assert isinstance(player['eligibleSlots'], list), "eligibleSlots should be a list"
    assert all(isinstance(slot, int) for slot in player['eligibleSlots']), "eligibleSlots should contain integers"
    assert isinstance(player['firstName'], str), "firstName should be a string"
    assert isinstance(player['fullName'], str), "fullName should be a string"
    assert isinstance(player['id'], int), "id should be an integer"
    assert isinstance(player['lastName'], str), "lastName should be a string"
    assert isinstance(player['proTeamId'], int), "proTeamId should be an integer"
    
    # Additional validation - check that the name fields match the expected pattern
    assert player['fullName'] == f"{player['firstName']} {player['lastName']}", "fullName should be firstName + lastName"
    
    # Print sample data for reference/debugging
    print(f"Example player data: {player}")
    print(f"Total players retrieved: {len(players)}")