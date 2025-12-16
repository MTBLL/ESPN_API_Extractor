import json

import pytest

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.models.player_model import PlayerModel


class TestPlayerModelProjections:
    """Test PlayerModel serialization and validation with projection data"""

    @pytest.fixture
    def projections_fixture_data(self):
        """Load the kona_playercard projections fixture"""
        with open("tests/fixtures/kona_playercard_projections_fixture.json", "r") as f:
            return json.load(f)

    @pytest.fixture
    def sample_projection_data(self):
        """Sample projection data for testing"""
        return {
            "season_outlook": "Test player outlook for 2025 season with detailed analysis.",
            "projections": {
                "AB": 500.0,
                "H": 150.0,
                "HR": 30.0,
                "RBI": 95.0,
                "SB": 15.0,
                "AVG": 0.300,
            },
            "last_7_games": {"AB": 45.0, "H": 12.0, "HR": 2.0, "RBI": 8.0},
            "current_season_stats": {"AB": 400.0, "H": 120.0, "HR": 25.0, "RBI": 75.0},
            "previous_season_stats": {
                "AB": 550.0,
                "H": 165.0,
                "HR": 35.0,
                "RBI": 105.0,
                "SB": 20.0,
            },
        }

    def test_player_model_creates_with_projection_fields(self, sample_projection_data):
        """Test that PlayerModel can be created with projection fields"""
        # Create model with projection data
        model_data = {"id": 12345, "name": "Test Player", **sample_projection_data}

        model = PlayerModel(**model_data)

        # Verify all projection fields are set
        assert model.season_outlook == sample_projection_data["season_outlook"]
        assert model.projections == sample_projection_data["projections"]
        assert model.last_7_games == sample_projection_data["last_7_games"]
        assert (
            model.current_season_stats == sample_projection_data["current_season_stats"]
        )
        assert (
            model.previous_season_stats
            == sample_projection_data["previous_season_stats"]
        )

    def test_player_model_validates_projection_data_types(self):
        """Test that PlayerModel validates projection data types correctly"""
        # Valid data
        valid_data = {
            "id": 12345,
            "name": "Test Player",
            "season_outlook": "Valid string outlook",
            "projections": {"HR": 25.0, "AB": 500.0},
            "last_7_games": {"HR": 2.0},
            "current_season_stats": {"HR": 20.0},
            "previous_season_stats": {"HR": 30.0},
        }

        # Should not raise any validation errors
        model = PlayerModel(**valid_data)
        assert model.projections["HR"] == 25.0

    def test_player_model_defaults_empty_projection_fields(self):
        """Test that PlayerModel defaults to empty dicts for projection fields"""
        # Create model with minimal data
        model = PlayerModel(
            name="Test  Player",
            idEspn=None,
            firstName=None,
            lastName=None,
            displayName=None,
            shortName=None,
            primaryPosition=None,
            positionName=None,
            proTeam=None,
            injuryStatus=None,
            displayWeight=None,
            displayHeight=None,
            dateOfBirth=None,
            birthPlace=None,
            debutYear=None,
            seasonOutlook=None,
            draftAuctionValue=None,
            onTeamId=None,
            auctionValueAverage=None,
        )

        # Verify projection fields default to empty dicts
        assert model.season_outlook is None
        assert model.projections == {}
        assert model.last_7_games == {}
        assert model.current_season_stats == {}
        assert model.previous_season_stats == {}

    def test_player_model_serializes_projection_data_correctly(
        self, sample_projection_data
    ):
        """Test that PlayerModel serializes projection data correctly to JSON"""
        # Create model with projection data
        model_data = {"id": 12345, "name": "Test Player", **sample_projection_data}
        model = PlayerModel(**model_data)

        # Serialize to JSON
        json_str = model.model_dump_json()

        # Parse back to verify structure
        parsed_data = json.loads(json_str)

        # Verify projection fields are in the JSON
        assert "season_outlook" in parsed_data
        assert "projections" in parsed_data
        assert "last_7_games" in parsed_data
        assert "current_season_stats" in parsed_data
        assert "previous_season_stats" in parsed_data

        # Verify actual values
        assert parsed_data["season_outlook"] == sample_projection_data["season_outlook"]
        assert parsed_data["projections"]["HR"] == 30.0
        assert parsed_data["previous_season_stats"]["SB"] == 20.0

    def test_player_model_deserializes_projection_data_correctly(
        self, sample_projection_data
    ):
        """Test that PlayerModel deserializes projection data correctly from JSON"""
        # Create JSON with projection data
        json_data = {"id": 12345, "name": "Test Player", **sample_projection_data}
        json_str = json.dumps(json_data)

        # Deserialize from JSON
        model = PlayerModel.model_validate_json(json_str)

        # Verify all projection data is correctly deserialized
        assert model.season_outlook == sample_projection_data["season_outlook"]
        assert model.projections == sample_projection_data["projections"]
        assert model.last_7_games == sample_projection_data["last_7_games"]
        assert (
            model.current_season_stats == sample_projection_data["current_season_stats"]
        )
        assert (
            model.previous_season_stats
            == sample_projection_data["previous_season_stats"]
        )

    def test_player_model_with_real_fixture_data(self, projections_fixture_data):
        """Test PlayerModel with real data from the projections fixture"""
        # Use Corbin Carroll's data from fixture
        carroll_data = projections_fixture_data["players"][1]

        # Create a Player object and hydrate it
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})
        player.hydrate_kona_playercard(carroll_data)

        # Convert to model
        model = player.to_model()

        # Verify model has real projection data
        assert model.id == 42404
        assert model.season_outlook is not None
        assert "2023 NL Rookie of the Year" in model.season_outlook

        # Verify projections with actual values from fixture
        assert model.projections is not None
        assert model.projections["AB"] == 377.0
        assert model.projections["HR"] == 19.0
        assert model.projections["SB"] == 21.0

        # Verify seasonal stats
        assert model.last_7_games is not None
        assert len(model.last_7_games) > 0

        assert model.current_season_stats is not None
        assert len(model.current_season_stats) > 0

        assert model.previous_season_stats is not None
        assert len(model.previous_season_stats) > 0

    def test_player_model_round_trip_with_projections(self, projections_fixture_data):
        """Test complete round trip: Player -> Model -> JSON -> Model -> Player"""
        # Use Shohei Ohtani's data from fixture
        ohtani_data = projections_fixture_data["players"][0]

        # Step 1: Create Player and hydrate
        original_player = Player({"id": 39832, "fullName": "Shohei Ohtani"})
        original_player.hydrate_kona_playercard(ohtani_data)

        # Step 2: Convert to Model
        model = original_player.to_model()

        # Step 3: Serialize to JSON
        json_str = model.model_dump_json()

        # Step 4: Deserialize from JSON
        deserialized_model = PlayerModel.model_validate_json(json_str)

        # Step 5: Convert back to Player
        restored_player = Player.from_model(deserialized_model)

        # Verify all projection data survived the round trip
        # Player objects store season_outlook in stats dictionary
        assert restored_player.stats.get("season_outlook") == original_player.stats.get(
            "season_outlook"
        )
        # Player objects store projections in stats dictionary
        assert restored_player.stats.get("projections") == original_player.stats.get(
            "projections"
        )
        assert restored_player.stats.get("last_7_games") == original_player.stats.get(
            "last_7_games"
        )
        assert restored_player.stats.get("current_season") == original_player.stats.get(
            "current_season"
        )
        assert restored_player.stats.get(
            "previous_season"
        ) == original_player.stats.get("previous_season")

    def test_player_model_handles_partial_projection_data(self):
        """Test that PlayerModel handles partial projection data gracefully"""
        # Test with only some projection fields
        partial_data = {
            "id": 12345,
            "name": "Test Player",
            "season_outlook": "Only outlook provided",
            "projections": {"HR": 25.0},
            # Missing last_7_games, current_season_stats, previous_season_stats
        }

        model = PlayerModel(**partial_data)

        # Verify partial data is preserved
        assert model.season_outlook == "Only outlook provided"
        assert model.projections == {"HR": 25.0}

        # Verify missing fields default to empty dicts
        assert model.last_7_games == {}
        assert model.current_season_stats == {}
        assert model.previous_season_stats == {}

    def test_player_model_projection_fields_are_optional(self):
        """Test that all projection fields are optional in PlayerModel"""
        # Create model with no projection data
        minimal_model = PlayerModel(
            name="Test Player",
            idEspn=12345,
            firstName=None,
            lastName=None,
            displayName=None,
            shortName=None,
            primaryPosition=None,
            positionName=None,
            proTeam=None,
            injuryStatus=None,
            displayWeight=None,
            displayHeight=None,
            dateOfBirth=None,
            birthPlace=None,
            debutYear=None,
            seasonOutlook=None,
            draftAuctionValue=None,
            onTeamId=None,
            auctionValueAverage=None,
        )

        # Should not raise any validation errors
        assert minimal_model.id == 12345
        assert minimal_model.name == "Test Player"

        # All projection fields should be None or empty
        assert minimal_model.season_outlook is None
        assert minimal_model.projections == {}
        assert minimal_model.last_7_games == {}
        assert minimal_model.current_season_stats == {}
        assert minimal_model.previous_season_stats == {}

    def test_player_model_preserves_existing_fields_with_projections(
        self, sample_projection_data
    ):
        """Test that PlayerModel preserves existing fields when projection data is added"""
        # Create model with both existing and projection data
        complete_data = {
            "id": 12345,
            "name": "Test Player",
            "pro_team": "NYY",
            "primary_position": "OF",
            "date_of_birth": "1995-01-15",
            **sample_projection_data,
        }

        model = PlayerModel(**complete_data)

        # Verify existing fields are preserved
        assert model.id == 12345
        assert model.name == "Test Player"
        assert model.pro_team == "NYY"
        assert model.primary_position == "OF"
        assert model.date_of_birth == "1995-01-15"

        # Verify projection fields are also set
        assert model.season_outlook == sample_projection_data["season_outlook"]
        assert model.projections == sample_projection_data["projections"]

    def test_player_model_validates_projection_dict_values(self):
        """Test that PlayerModel validates projection dictionary values are numeric"""
        # This test ensures that the Dict[str, Any] typing works correctly
        # and allows various numeric types in projection dictionaries
        numeric_data = {
            "id": 12345,
            "name": "Test Player",
            "projections": {
                "AB": 500,  # int
                "AVG": 0.300,  # float
                "HR": 25.0,  # float
                "SB": 15,  # int
            },
            "previous_season_stats": {"AB": 550, "HR": 30},
        }

        model = PlayerModel(**numeric_data)

        # Verify numeric values are preserved correctly
        assert model.projections["AB"] == 500
        assert model.projections["AVG"] == 0.300
        assert model.projections["HR"] == 25.0
        assert model.projections["SB"] == 15
