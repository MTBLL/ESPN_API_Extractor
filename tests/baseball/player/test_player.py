import pytest

from espn_api_extractor.baseball.constants import (
    LINEUP_SLOT_MAP,
    NOMINAL_POSITION_MAP,
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
        LINEUP_SLOT_MAP.get(9),  # CF
        LINEUP_SLOT_MAP.get(10),  # RF
        LINEUP_SLOT_MAP.get(5),  # OF
        LINEUP_SLOT_MAP.get(12),  # UTIL
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

    # Initial state should have fields initialized to None
    assert player.display_name is None
    assert player.short_name is None
    assert player.date_of_birth is None

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

    # Add some stats for testing (using semantic keys as expected by PlayerModel)
    player.stats = {
        "projections": {"AB": 600, "H": 190, "HR": 30},
        "current_season": {"AB": 550, "H": 175, "HR": 25},
        "last_7_games": {"AB": 500, "H": 160, "HR": 22},
        "previous_season": {"AB": 580, "H": 180, "HR": 28},
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
    assert model.stats["current_season"]["AB"] == 550


@pytest.fixture
def hasura_fixture_data():
    """Load Hasura GraphQL player data fixture"""
    import json
    import os

    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "fixtures",
        "graphql_players_response.json",
    )
    with open(fixture_path, "r") as f:
        return json.load(f)


def test_player_from_model_with_hasura_fixture(hasura_fixture_data):
    """
    Test the runner's logic for converting PlayerModel objects from Hasura to Player objects.
    Validates every single field from PlayerModel with correct data types.

    This tests the specific workflow:
    players: List[Player] = [Player.from_model(model) for model in player_models]
    """
    from typing import List

    from espn_api_extractor.models.player_model import BirthPlace, PlayerModel

    # Extract the raw player data from the fixture
    raw_players_data = hasura_fixture_data["data"]["players"]

    # Create PlayerModel instances directly from raw hasura data
    player_models: List[PlayerModel] = [
        PlayerModel(**raw_player) for raw_player in raw_players_data
    ]

    # Execute the runner logic: cast PlayerModel to Player
    players: List[Player] = [Player.from_model(model) for model in player_models]

    # Verify we have the expected number of players
    assert len(players) == 3

    # Test each PlayerModel field with correct data types
    for i, (player_model, player) in enumerate(zip(player_models, players)):
        
        # Basic player info
        assert isinstance(player_model.id, (int, type(None)))
        if player_model.id is not None:
            assert player.id == player_model.id
            
        assert isinstance(player_model.name, (str, type(None)))
        if player_model.name is not None:
            assert player.name == player_model.name
            
        assert isinstance(player_model.first_name, (str, type(None)))
        assert isinstance(player_model.last_name, (str, type(None)))
        
        # Display information
        assert isinstance(player_model.display_name, (str, type(None)))
        assert isinstance(player_model.short_name, (str, type(None)))
        assert isinstance(player_model.nickname, (str, type(None)))
        assert isinstance(player_model.slug, (str, type(None)))
        
        # Position information
        assert isinstance(player_model.primary_position, (str, type(None)))
        assert isinstance(player_model.eligible_slots, list)
        for slot in player_model.eligible_slots:
            assert isinstance(slot, str)
        assert isinstance(player_model.position_name, (str, type(None)))
        assert isinstance(player_model.pos, (str, type(None)))
        
        # Team information
        assert isinstance(player_model.pro_team, (str, type(None)))
        
        # Status information
        assert isinstance(player_model.injury_status, (str, type(None)))
        assert isinstance(player_model.status, (str, type(None)))
        assert isinstance(player_model.injured, bool)
        assert isinstance(player_model.active, bool)
        
        # Ownership statistics
        assert isinstance(player_model.percent_owned, (int, float))
        
        # Physical attributes
        assert isinstance(player_model.weight, (float, type(None)))
        assert isinstance(player_model.display_weight, (str, type(None)))
        assert isinstance(player_model.height, (int, type(None)))
        assert isinstance(player_model.display_height, (str, type(None)))
        
        # Playing characteristics
        assert isinstance(player_model.bats, (str, type(None)))
        assert isinstance(player_model.throws, (str, type(None)))
        
        # Biographical information
        assert isinstance(player_model.date_of_birth, (str, type(None)))
        assert isinstance(player_model.birth_place, (BirthPlace, type(None)))
        if player_model.birth_place is not None:
            assert isinstance(player_model.birth_place.city, (str, type(None)))
            assert isinstance(player_model.birth_place.state, (str, type(None)))
            assert isinstance(player_model.birth_place.country, (str, type(None)))
        assert isinstance(player_model.debut_year, (int, type(None)))
        
        # Jersey information
        assert isinstance(player_model.jersey, str)  # Always string due to validator
        
        # Media information
        assert isinstance(player_model.headshot, (str, type(None)))
        
        # Projections and outlook
        assert isinstance(player_model.season_outlook, (str, type(None)))
        
        # Fantasy and draft information from kona_playercard
        assert isinstance(player_model.draft_auction_value, (int, type(None)))
        assert isinstance(player_model.on_team_id, (int, type(None)))
        assert isinstance(player_model.draft_ranks, dict)
        assert isinstance(player_model.games_played_by_position, dict)
        for position, games in player_model.games_played_by_position.items():
            assert isinstance(position, str)
            assert isinstance(games, int)
        assert isinstance(player_model.auction_value_average, (float, type(None)))
        
        # Statistics - kona stats with semantic keys
        assert isinstance(player_model.stats, dict)
        expected_stat_keys = {"projections", "current_season", "previous_season", "last_7_games", "last_15_games", "last_30_games"}
        for key in player_model.stats.keys():
            assert key in expected_stat_keys or isinstance(key, str)
            assert isinstance(player_model.stats[key], dict)
        
        # Season statistics from the statistics endpoint
        if player_model.season_stats is not None:
            assert isinstance(player_model.season_stats.split_id, (str, type(None)))
            assert isinstance(player_model.season_stats.split_name, (str, type(None)))
            assert isinstance(player_model.season_stats.split_abbreviation, (str, type(None)))
            assert isinstance(player_model.season_stats.split_type, (str, type(None)))
            assert isinstance(player_model.season_stats.categories, dict)
        
        # Verify the conversion worked and players are functional
        assert isinstance(player, Player)
        assert hasattr(player, "from_model")
        assert hasattr(player, "to_model")
        assert hasattr(player, "hydrate_bio")
        assert callable(getattr(player, "from_model"))
        assert callable(getattr(player, "to_model"))
        assert callable(getattr(player, "hydrate_bio"))
        
        # Test specific values from fixture data
        if i == 0:  # First player (Test Player 1)
            assert player_model.id == 12345
            assert player_model.name == "Test Player 1"
            assert player_model.active is True
            assert player_model.injured is False
            assert player_model.primary_position == "1B"
            assert player_model.pro_team == "NYY"
            assert player_model.height == 74
            assert player_model.weight == 220.0
            assert player_model.bats == "Right"
            assert player_model.throws == "Right"
            
        elif i == 2:  # Third player (Test Player 3 - inactive/injured)
            assert player_model.id == 11111
            assert player_model.active is False
            assert player_model.status == "injured"


class TestPlayerEdgeCasesAndSadPaths:
    """Test edge cases and sad paths for Player class to increase code coverage."""

    def test_player_with_split_type_5_individual_game_stats(self):
        """Test that split type 5 (individual game stats) are skipped."""
        from datetime import datetime
        current_year = datetime.now().year

        player_data = {
            "id": 12345,
            "fullName": "Test Player",
            "playerPoolEntry": {
                "player": {
                    "stats": [
                        {
                            "seasonId": current_year,
                            "statSplitTypeId": 5,  # Individual game stats - should be skipped
                            "statSourceId": 0,
                            "stats": {
                                "0": 100,  # AB
                                "1": 30,   # H
                            }
                        },
                        {
                            "seasonId": current_year,
                            "statSplitTypeId": 0,  # Season stats - should be processed
                            "statSourceId": 0,
                            "stats": {
                                "0": 200,  # AB
                                "1": 60,   # H
                            }
                        }
                    ]
                }
            }
        }

        player = Player(player_data)

        # Verify that split type 5 was skipped and only split type 0 was processed
        assert "current_season" in player.stats
        assert player.stats["current_season"]["AB"] == 200  # From split type 0, not 100 from split type 5
        assert player.stats["current_season"]["H"] == 60

    def test_player_with_unmapped_stat_key(self):
        """Test that stats with unmapped season/split combinations are skipped."""
        from datetime import datetime
        current_year = datetime.now().year
        future_year = current_year + 1

        player_data = {
            "id": 12345,
            "fullName": "Test Player",
            "playerPoolEntry": {
                "player": {
                    "stats": [
                        {
                            "seasonId": future_year,  # Future season - not mapped
                            "statSplitTypeId": 0,
                            "statSourceId": 0,
                            "stats": {
                                "0": 100,
                                "1": 30,
                            }
                        },
                        {
                            "seasonId": current_year,
                            "statSplitTypeId": 10,  # Unknown split type - not mapped
                            "statSourceId": 0,
                            "stats": {
                                "0": 150,
                                "1": 45,
                            }
                        },
                        {
                            "seasonId": current_year,
                            "statSplitTypeId": 0,  # Valid stats
                            "statSourceId": 0,
                            "stats": {
                                "0": 200,
                                "1": 60,
                            }
                        }
                    ]
                }
            }
        }

        player = Player(player_data)

        # Verify that only valid stats were processed
        assert "current_season" in player.stats
        assert player.stats["current_season"]["AB"] == 200
        assert player.stats["current_season"]["H"] == 60

    def test_player_projections_with_applied_average(self):
        """Test that projections include appliedAverage when present."""
        from datetime import datetime
        current_year = datetime.now().year

        player_data = {
            "id": 12345,
            "fullName": "Test Player",
            "playerPoolEntry": {
                "player": {
                    "stats": [
                        {
                            "seasonId": current_year,
                            "statSplitTypeId": 0,
                            "statSourceId": 1,  # Projected stats
                            "appliedStats": {
                                "0": 600,  # AB
                                "1": 180,  # H
                            },
                            "appliedTotal": 450.5,
                            "appliedAverage": 7.8,
                        }
                    ]
                }
            }
        }

        player = Player(player_data)

        # Verify projections were created with both appliedTotal and appliedAverage
        assert "projections" in player.stats
        assert "_fantasy_scoring" in player.stats["projections"]
        assert player.stats["projections"]["_fantasy_scoring"]["applied_total"] == 450.5
        assert player.stats["projections"]["_fantasy_scoring"]["applied_average"] == 7.8

    def test_player_with_previous_year_non_season_stats(self):
        """Test that previous year stats with non-zero split type are skipped."""
        from datetime import datetime
        current_year = datetime.now().year
        previous_year = current_year - 1

        player_data = {
            "id": 12345,
            "fullName": "Test Player",
            "playerPoolEntry": {
                "player": {
                    "stats": [
                        {
                            "seasonId": previous_year,
                            "statSplitTypeId": 1,  # Last 7 games from previous year - should be skipped
                            "statSourceId": 0,
                            "stats": {
                                "0": 20,
                                "1": 5,
                            }
                        },
                        {
                            "seasonId": previous_year,
                            "statSplitTypeId": 0,  # Previous season full stats - should be processed
                            "statSourceId": 0,
                            "stats": {
                                "0": 500,
                                "1": 150,
                            }
                        }
                    ]
                }
            }
        }

        player = Player(player_data)

        # Verify that only split type 0 from previous year was processed
        # Use dynamic key with year suffix (e.g., "previous_season_24")
        previous_season_key = f"previous_season_{str(previous_year)[-2:]}"
        assert previous_season_key in player.stats
        assert player.stats[previous_season_key]["AB"] == 500
        assert player.stats[previous_season_key]["H"] == 150
        # Last 7 games from previous year should not create any stats entry
        assert "last_7_games" not in player.stats
