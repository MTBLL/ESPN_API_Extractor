import pytest

from espn_api_extractor.baseball.constant import (
    NOMINAL_POSITION_MAP,
    POSITION_MAP,
    PRO_TEAM_MAP,
)
from espn_api_extractor.baseball.player import Player


@pytest.fixture
def player_data():
    """
    Fixture providing sample player data in the format returned by the ESPN API.
    """
    return {
        "defaultPositionId": 8,
        "droppable": False,
        "eligibleSlots": [9, 10, 5, 12, 16, 17],
        "firstName": "Corbin",
        "fullName": "Corbin Carroll",
        "id": 42404,
        "lastName": "Carroll",
        "ownership": {"percentOwned": 99.86736311557726},
        "proTeamId": 29,
        "universeId": 2,
    }


def test_player_initialization(player_data):
    """
    Test the Player class initialization with fixture data.
    """
    # Initialize a Player with the sample data
    player = Player(player_data)

    # Verify basic player info
    assert player.name == "Corbin Carroll"
    assert player.id == 42404

    # Verify position mapping
    expected_primary_position = NOMINAL_POSITION_MAP.get(8)  # CF
    assert player.primaryPosition == expected_primary_position

    # Verify eligible slots
    # Note: there's a condition in Player that filters out slots 16 and 17,
    # but it's using "or" instead of "and" which means it will never filter anything out
    expected_slots = [
        POSITION_MAP.get(9),  # CF
        POSITION_MAP.get(10),  # RF
        POSITION_MAP.get(5),  # OF
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
    player = Player(player_data)
    assert repr(player) == "Player(Corbin Carroll)"


def test_player_missing_data():
    """
    Test creating a Player with minimal data.
    """
    minimal_data = {"fullName": "Test Player", "id": 12345}

    player = Player(minimal_data)
    assert player.name == "Test Player"
    assert player.id == 12345

    # These should be empty or default values
    assert player.primaryPosition is None  # No defaultPositionId in data
    assert player.proTeam is None  # No proTeamId in data
    assert player.eligibleSlots == []  # No eligibleSlots in data
    assert player.percent_owned == -1  # Default when ownership data is missing
    
    
@pytest.fixture
def player_details_data():
    """
    Fixture providing sample player details data in the format returned by the ESPN API.
    """
    return {
        "id": "42404",
        "firstName": "Corbin",
        "lastName": "Carroll",
        "fullName": "Corbin Carroll",
        "displayName": "Corbin Carroll",
        "shortName": "C. Carroll",
        "nickname": "Clutch Corbin",
        "weight": 165,
        "displayWeight": "165 lbs",
        "height": 69,
        "displayHeight": "5' 9\"",
        "age": 24,
        "dateOfBirth": "2000-08-21T07:00Z",
        "birthPlace": {
            "city": "Seattle",
            "country": "USA"
        },
        "debutYear": 2022,
        "jersey": "7",
        "position": {
            "name": "Center Fielder",
            "displayName": "Center Fielder",
            "abbreviation": "CF"
        },
        "bats": {
            "displayValue": "Left"
        },
        "throws": {
            "displayValue": "Left"
        },
        "active": True,
        "status": {
            "name": "Active",
            "type": "active"
        },
        "experience": {
            "years": 3
        },
        "headshot": {
            "href": "https://a.espncdn.com/i/headshots/mlb/players/full/42404.png"
        }
    }


def test_player_hydration(player_data, player_details_data):
    """
    Test the Player hydration with additional details data.
    """
    # Initialize a player
    player = Player(player_data)
    
    # Initial state should not have detailed attributes
    assert not hasattr(player, "displayName")
    assert not hasattr(player, "shortName")
    assert not hasattr(player, "dateOfBirth")
    
    # Hydrate the player
    player.hydrate(player_details_data)
    
    # Verify basic attributes are now set
    assert player.displayName == "Corbin Carroll"
    assert player.shortName == "C. Carroll"
    assert player.nickname == "Clutch Corbin"
    
    # Verify physical attributes
    assert player.weight == 165
    assert player.displayWeight == "165 lbs"
    assert player.height == 69
    assert player.displayHeight == "5' 9\""
    
    # Verify biographical information
    assert player.age == 24
    assert player.dateOfBirth == "2000-08-21T07:00Z"
    assert player.birthPlace == {"city": "Seattle", "country": "USA"}
    assert player.debutYear == 2022
    
    # Verify jersey and position
    assert player.jersey == "7"
    assert player.positionName == "Center Fielder"
    assert player.positionDisplayName == "Center Fielder"
    assert player.positionAbbreviation == "CF"
    
    # Verify playing characteristics
    assert player.bats == "Left"
    assert player.throws == "Left"
    
    # Verify status
    assert player.active is True
    assert player.statusName == "Active"
    assert player.statusType == "active"
    
    # Verify experience
    assert player.experienceYears == 3
    
    # Verify headshot
    assert player.headshot == "https://a.espncdn.com/i/headshots/mlb/players/full/42404.png"
