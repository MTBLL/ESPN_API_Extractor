import pytest

from espn_api_extractor.baseball.constants import (
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
    assert player.primary_position == expected_primary_position

    # Verify eligible slots
    # Now correctly filtering out bench (BE) and injured list (IL) slots
    expected_slots = [
        POSITION_MAP.get(9),  # CF
        POSITION_MAP.get(10),  # RF
        POSITION_MAP.get(5),  # OF
        POSITION_MAP.get(12),  # UTIL
        # BE and IL are excluded
    ]
    assert set(player.eligible_slots) == set(expected_slots)

    # Verify pro team
    expected_team = PRO_TEAM_MAP.get(29)  # ARI
    assert player.pro_team == expected_team

    # Verify ownership percentage
    assert player.percent_owned == 99.87

    # The following are not present in our test data but should have default values
    assert player.stats == {}


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
    assert player.primary_position is None  # No defaultPositionId in data
    assert player.pro_team is None  # No proTeamId in data
    assert player.eligible_slots == []  # No eligibleSlots in data
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
        "birthPlace": {"city": "Seattle", "country": "USA"},
        "debutYear": 2022,
        "jersey": "7",
        "position": {
            "name": "Center Fielder",
            "displayName": "Center Fielder",
            "abbreviation": "CF",
        },
        "bats": {"displayValue": "Left"},
        "throws": {"displayValue": "Left"},
        "active": True,
        "status": {"name": "Active", "type": "active"},
        "experience": {"years": 3},
        "headshot": {
            "href": "https://a.espncdn.com/i/headshots/mlb/players/full/42404.png"
        },
    }


def test_player_hydration(player_data, player_details_data):
    """
    Test the Player hydration with additional details data.
    """
    # Initialize a player
    player = Player(player_data)

    # Initial state should not have detailed attributes
    assert not hasattr(player, "display_name")
    assert not hasattr(player, "short_name")
    assert not hasattr(player, "date_of_birth")

    # Hydrate the player
    player.hydrate_bio(player_details_data)

    # Verify basic attributes are now set
    assert player.display_name == "Corbin Carroll"
    assert player.short_name == "C. Carroll"
    assert player.nickname == "Clutch Corbin"

    # Verify physical attributes
    assert player.weight == 165
    assert player.display_weight == "165 lbs"
    assert player.height == 69
    assert player.display_height == "5' 9\""

    # Verify biographical information
    assert player.date_of_birth == "2000-08-21"
    assert player.birth_place == {"city": "Seattle", "country": "USA"}
    assert player.debut_year == 2022

    # Verify jersey and position
    assert player.jersey == "7"
    assert player.position_name == "Center Fielder"
    assert player.pos == "CF"

    # Verify playing characteristics
    assert player.bats == "Left"
    assert player.throws == "Left"

    # Verify status
    assert player.active is True
    assert player.status == "active"

    # Verify headshot
    assert (
        player.headshot
        == "https://a.espncdn.com/i/headshots/mlb/players/full/42404.png"
    )


def test_player_model_conversion(player_data, player_details_data):
    """
    Test converting between Player and PlayerModel instances.
    """
    # Initialize and hydrate a player
    player = Player(player_data)
    player.hydrate_bio(player_details_data)

    # Add some stats for testing (using string keys as expected by PlayerModel)
    player.stats = {
        "projections": {"AB": 600, "H": 190, "HR": 30},
        "preseason": {"AB": 550, "H": 175, "HR": 25},
        "regular_season": {"AB": 500, "H": 160, "HR": 22},
        "previous_season": {"AB": 580, "H": 180, "HR": 28}
    }

    # Convert to a PlayerModel
    model = player.to_model()

    # Verify basic attributes
    assert model.id == player.id
    assert model.name == player.name
    assert model.pro_team == player.pro_team
    assert model.primary_position == player.primary_position

    # Verify stats conversion
    assert model.stats["projections"]["HR"] == 30
    assert model.stats["preseason"]["AB"] == 550


def test_player_from_model():
    """
    Test converting PlayerModel back to Player instance using Player.from_model().
    
    This tests the basic conversion functionality for the primary use case:
    converting validated PlayerModel objects from GraphQL back to Player objects.
    """
    # Create a PlayerModel directly (simulating what comes from GraphQL)
    player_model_data = {
        "id": 42404,
        "name": "Corbin Carroll",
        "first_name": "Corbin", 
        "last_name": "Carroll",
        "injured": False,
        "active": True,
        "percent_owned": 99.87,
        "stats": {
            "projections": {"AB": 600, "H": 190, "HR": 30, "RBI": 95},
            "preseason": {"AB": 550, "H": 175, "HR": 25, "RBI": 90},
            "regular_season": {"AB": 500, "H": 160, "HR": 22, "RBI": 80}, 
            "previous_season": {"AB": 580, "H": 180, "HR": 28, "RBI": 85}
        }
    }
    
    from espn_api_extractor.models.player_model import PlayerModel
    player_model = PlayerModel(**player_model_data)

    # Convert to Player using from_model
    player = Player.from_model(player_model)

    # Verify core attributes that Player constructor handles
    assert player.id == 42404
    assert player.name == "Corbin Carroll"
    assert player.first_name == "Corbin"
    assert player.last_name == "Carroll"
    assert player.injured is False
    assert player.percent_owned == 99.87

    # Verify stats are preserved
    assert player.stats == player_model_data["stats"]
    assert player.stats["projections"]["HR"] == 30
    assert player.stats["preseason"]["AB"] == 550

    # Verify the converted player is a proper Player instance with all methods
    assert hasattr(player, 'hydrate_bio')
    assert hasattr(player, 'hydrate_statistics') 
    assert hasattr(player, 'to_model')
    assert isinstance(player, Player)

    # Test that we can convert back to PlayerModel (the key round-trip functionality)
    round_trip_model = player.to_model()
    assert round_trip_model.id == player_model.id
    assert round_trip_model.name == player_model.name
    assert round_trip_model.first_name == player_model.first_name
    
    # Most importantly, verify that the from_model method creates a functional Player
    # that can be used in the existing codebase workflows
    assert callable(getattr(player, 'to_model'))
    
    # Verify the Player can be used for hydration (the main use case)
    # This simulates the workflow: GraphQL PlayerModel -> Player -> hydration -> processing
    sample_bio_data = {
        "displayName": "Corbin Carroll",
        "weight": 165,
        "height": 69
    }
    
    # Should not raise an exception
    player.hydrate_bio(sample_bio_data)
    
    # After hydration, these attributes should be set
    assert hasattr(player, 'display_name')
    assert player.display_name == "Corbin Carroll"
    assert player.weight == 165
