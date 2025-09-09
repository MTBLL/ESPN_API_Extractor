import pytest

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.models.player_model import BirthPlace, PlayerModel, StatPeriod


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
        "throws": {"displayValue": "Right"},
        "active": True,
        "status": {"name": "Active", "type": "active"},
        "experience": {"years": 3},
        "headshot": {
            "href": "https://a.espncdn.com/i/headshots/mlb/players/full/42404.png"
        },
    }


def test_player_model_from_dict():
    """Test creating a PlayerModel directly from a dictionary"""
    player_dict = {
        "id": 42404,
        "name": "Corbin Carroll",
        "first_name": "Corbin",
        "last_name": "Carroll",
        "display_name": "Corbin Carroll",
        "pro_team": "ARI",
        "primary_position": "CF",
        "eligible_slots": ["CF", "OF", "UTIL"],
        "percent_owned": 99.87,
        "active": True,
        "bats": "Left",
        "throws": "Right",
        "stats": {
            0: {
                "points": 250.5,
                "projected_points": 300.0,
                "breakdown": {"AB": 550, "H": 175, "HR": 25},
                "projected_breakdown": {"AB": 600, "H": 190, "HR": 30},
            }
        },
    }

    model = PlayerModel(**player_dict)

    assert model.id == 42404
    assert model.name == "Corbin Carroll"
    assert model.pro_team == "ARI"
    assert model.primary_position == "CF"
    assert "CF" in model.eligible_slots
    assert model.percent_owned == 99.87
    assert model.active is True
    assert model.bats == "Left"

    # Test stats (key was converted to string by validator)
    assert model.stats["0"]["points"] == 250.5
    assert model.stats["0"]["projected_points"] == 300.0
    assert model.stats["0"]["breakdown"]["HR"] == 25
    assert model.stats["0"]["projected_breakdown"]["AB"] == 600


def test_player_model_from_player_object(player_data, player_details_data):
    """Test converting a Player object to a PlayerModel and back"""
    # Create and hydrate a Player object
    player = Player(player_data)
    player.hydrate_bio(player_details_data)

    # Add some stats for testing
    player.stats = {
        "0": {
            "points": 250.5,
            "projected_points": 300.0,
            "breakdown": {"AB": 550, "H": 175, "HR": 25},
            "projected_breakdown": {"AB": 600, "H": 190, "HR": 30},
        }
    }

    # Convert to PlayerModel
    model = PlayerModel.from_player(player)

    # Verify basic attributes
    assert model.id == player.id
    assert model.name == player.name
    assert model.pro_team == player.pro_team
    assert model.primary_position == player.primary_position
    assert model.bats == player.bats
    assert model.throws == player.throws

    # Verify stats conversion
    assert model.stats["0"]["points"] == 250.5
    assert model.stats["0"]["breakdown"]["HR"] == 25

    # Convert back to dict for Player initialization
    player_dict = model.to_player_dict()

    # Verify the dict has the necessary fields
    assert player_dict["id"] == player.id
    assert player_dict["name"] == player.name
    assert "stats" in player_dict
    assert player_dict["stats"][0]["points"] == 250.5


def test_player_model_json_serialization(player_data, player_details_data):
    """Test JSON serialization and deserialization of PlayerModel"""
    # Create and hydrate a Player object
    player = Player(player_data)
    player.hydrate_bio(player_details_data)

    # Convert to PlayerModel
    model = PlayerModel.from_player(player)

    # Serialize to JSON
    json_data = model.model_dump_json()

    # Deserialize from JSON
    deserialized_model = PlayerModel.model_validate_json(json_data)

    # Verify the models match
    assert deserialized_model.id == model.id
    assert deserialized_model.name == model.name
    assert deserialized_model.pro_team == model.pro_team
    assert deserialized_model.primary_position == model.primary_position

    # Check nested object deserialization
    if model.birth_place and deserialized_model.birth_place:
        assert model.birth_place.city is not None
        assert model.birth_place.country is not None
        assert deserialized_model.birth_place.city == model.birth_place.city
        assert deserialized_model.birth_place.country == model.birth_place.country


def test_birthplace_model():
    """Test the BirthPlace model"""
    birthplace = BirthPlace(city="Seattle", country="USA")
    assert birthplace.city == "Seattle"
    assert birthplace.country == "USA"

    # Test with empty values
    empty_birthplace = BirthPlace()
    assert empty_birthplace.city is None
    assert empty_birthplace.country is None


def test_stat_period_model():
    """Test the StatPeriod model"""
    stat_period = StatPeriod(
        points=250.5,
        projected_points=300.0,
        breakdown={"AB": 550, "H": 175, "HR": 25},
        projected_breakdown={"AB": 600, "H": 190, "HR": 30},
    )

    assert stat_period.points == 250.5
    assert stat_period.projected_points == 300.0
    assert stat_period.breakdown["AB"] == 550
    assert stat_period.projected_breakdown["HR"] == 30

    # Test with default values
    default_stat_period = StatPeriod()
    assert default_stat_period.points == 0.0
    assert default_stat_period.projected_points == 0.0
    assert default_stat_period.breakdown == {}
    assert default_stat_period.projected_breakdown == {}
