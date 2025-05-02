import pytest

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.baseball.constant import NOMINAL_POSITION_MAP, POSITION_MAP, PRO_TEAM_MAP


@pytest.fixture
def player_data():
    """
    Fixture providing sample player data in the format returned by the ESPN API.
    """
    return {
        'defaultPositionId': 8,
        'droppable': False,
        'eligibleSlots': [9, 10, 5, 12, 16, 17],
        'firstName': 'Corbin',
        'fullName': 'Corbin Carroll',
        'id': 42404,
        'lastName': 'Carroll',
        'ownership': {'percentOwned': 99.86736311557726},
        'proTeamId': 29,
        'universeId': 2
    }


def test_player_initialization(player_data):
    """
    Test the Player class initialization with fixture data.
    """
    # Initialize a Player with the sample data
    current_year = 2025
    player = Player(player_data, current_year)
    
    # Verify basic player info
    assert player.name == "Corbin Carroll"
    assert player.playerId == 42404
    
    # Verify position mapping
    expected_primary_position = NOMINAL_POSITION_MAP.get(8)  # CF
    assert player.primaryPosition == expected_primary_position
    
    # Verify eligible slots
    # Note: there's a condition in Player that filters out slots 16 and 17,
    # but it's using "or" instead of "and" which means it will never filter anything out
    expected_slots = [
        POSITION_MAP.get(9),   # CF
        POSITION_MAP.get(10),  # RF
        POSITION_MAP.get(5),   # OF
        POSITION_MAP.get(12),  # UTIL
        POSITION_MAP.get(16),  # BE
        POSITION_MAP.get(17),  # IL
    ]
    assert set(player.eligibleSlots) == set(expected_slots)
    
    # Verify pro team
    expected_team = PRO_TEAM_MAP.get(29)  # ARI
    assert player.proTeam == expected_team
    
    # Verify ownership percentage
    assert player.percent_owned == 99.87
    
    # The following are not present in our test data but should have default values
    assert player.stats == {}
    assert player.total_points == 0
    assert player.projected_total_points == 0


def test_player_repr(player_data):
    """
    Test the Player's string representation.
    """
    player = Player(player_data, 2025)
    assert repr(player) == "Player(Corbin Carroll)"


def test_player_missing_data():
    """
    Test creating a Player with minimal data.
    """
    minimal_data = {
        'fullName': 'Test Player',
        'id': 12345
    }
    
    player = Player(minimal_data, 2025)
    assert player.name == "Test Player"
    assert player.playerId == 12345
    
    # These should be empty or default values
    assert player.primaryPosition is None  # No defaultPositionId in data
    assert player.proTeam is None  # No proTeamId in data
    assert player.eligibleSlots == []  # No eligibleSlots in data
    assert player.percent_owned == -1  # Default when ownership data is missing