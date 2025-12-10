import json

import pytest

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.models.player_model import PlayerModel


class TestPlayerKonaPlayercard:
    """Test Player object kona_playercard data hydration and serialization"""

    @pytest.fixture
    def kona_playercard_fixture_data(self):
        """Load the kona_playercard fixture data"""
        with open("tests/fixtures/kona_playercard_projections_fixture.json", "r") as f:
            return json.load(f)

    @pytest.fixture
    def carroll_player_data(self, kona_playercard_fixture_data):
        """Get Corbin Carroll's player data from fixture"""
        carroll_data = kona_playercard_fixture_data["players"][0]
        assert carroll_data["id"] == 42404
        return carroll_data

    @pytest.fixture
    def ohtani_player_data(self, kona_playercard_fixture_data):
        """Get Shohei Ohtani's player data from fixture"""
        ohtani_data = kona_playercard_fixture_data["players"][1]
        assert ohtani_data["id"] == 39832
        return ohtani_data

    def test_player_hydrate_kona_playercard_sets_season_outlook(self, carroll_player_data):
        """Test that kona_playercard hydration correctly sets season outlook"""
        # Create player object
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})

        # Hydrate with complete player dict from API response
        player.hydrate_kona_playercard(carroll_player_data)

        # Verify season outlook was set
        assert hasattr(player, "season_outlook")
        assert player.season_outlook is not None
        assert isinstance(player.season_outlook, str)
        assert len(player.season_outlook) > 100  # Should be substantial text
        assert "2023 NL Rookie of the Year" in player.season_outlook

    def test_player_hydrate_kona_playercard_sets_projections_dict(
        self, carroll_player_data
    ):
        """Test that kona_playercard hydration correctly sets projections dictionary with readable keys"""
        # Create player object
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})

        # Hydrate with complete player dict from API response
        player.hydrate_kona_playercard(carroll_player_data)

        # Verify projections were set under stats namespace
        assert hasattr(player, "stats")
        assert "projections" in player.stats
        assert isinstance(player.stats["projections"], dict)
        assert len(player.stats["projections"]) > 0

        # Verify specific projection values with readable keys
        assert "AB" in player.stats["projections"]  # At bats
        assert "H" in player.stats["projections"]  # Hits
        assert "HR" in player.stats["projections"]  # Home runs
        assert "SB" in player.stats["projections"]  # Stolen bases

        # Verify the actual values match the fixture
        assert player.stats["projections"]["AB"] == 377.0
        assert player.stats["projections"]["H"] == 95.0
        assert player.stats["projections"]["HR"] == 19.0
        assert player.stats["projections"]["SB"] == 21.0

    def test_player_hydrate_kona_playercard_sets_seasonal_stats(self, carroll_player_data):
        """Test that kona_playercard hydration sets all seasonal stat dictionaries (preseason, regular, previous)"""
        # Create player object
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})

        # Hydrate with projections
        player.hydrate_kona_playercard(carroll_player_data)

        # Verify all seasonal stats were set under stats namespace
        assert hasattr(player, "stats")
        assert "preseason" in player.stats
        assert "regular_season" in player.stats
        assert "previous_season" in player.stats

        # Verify they are dictionaries with data
        assert isinstance(player.stats["preseason"], dict)
        assert isinstance(player.stats["regular_season"], dict)
        assert isinstance(player.stats["previous_season"], dict)

        assert len(player.stats["preseason"]) > 0
        assert len(player.stats["regular_season"]) > 0
        assert len(player.stats["previous_season"]) > 0

    def test_player_hydrate_projections_maps_stat_keys_correctly(
        self, ohtani_player_data
    ):
        """Test that stat keys are correctly mapped from numeric to readable names"""
        # Create player object
        player = Player({"id": 39832, "fullName": "Shohei Ohtani"})

        # Hydrate with complete player dict from API response
        player.hydrate_kona_playercard(ohtani_player_data)

        # Test preseason stats mapping under stats namespace
        assert "AB" in player.stats["preseason"]
        assert player.stats["preseason"]["AB"] == 31.0

        # Test regular season stats mapping under stats namespace
        assert "AB" in player.stats["regular_season"]
        assert player.stats["regular_season"]["AB"] == 58.0

        # Test previous season stats mapping (2024) under stats namespace
        assert "AB" in player.stats["previous_season"]
        assert "HR" in player.stats["previous_season"]
        assert player.stats["previous_season"]["AB"] == 636.0
        assert player.stats["previous_season"]["HR"] == 54.0

    def test_player_hydrate_projections_handles_missing_stats_gracefully(self):
        """Test that hydrate_projections handles missing or incomplete stats gracefully"""
        # Create player object
        player = Player({"id": 99999, "fullName": "Test Player"})

        # Test with minimal data following the API structure
        minimal_data = {
            "player": {
                "seasonOutlook": "Test outlook",
                "stats": [],  # Empty stats array
            }
        }

        # Should not raise an error
        player.hydrate_kona_playercard(minimal_data)

        # Should still set season outlook
        assert player.season_outlook == "Test outlook"

        # Should initialize empty dicts for missing stats under stats namespace
        assert player.stats["projections"] == {}
        assert player.stats["preseason"] == {}
        assert player.stats["regular_season"] == {}
        assert player.stats["previous_season"] == {}

    def test_player_hydrate_projections_handles_missing_season_outlook(
        self, carroll_player_data
    ):
        """Test that hydrate_projections handles missing season outlook"""
        # Create player object
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})

        # Remove season outlook from data but maintain API structure
        data_without_outlook = carroll_player_data.copy()
        data_without_outlook["player"] = carroll_player_data["player"].copy()
        del data_without_outlook["player"]["seasonOutlook"]

        # Should not raise an error
        player.hydrate_kona_playercard(data_without_outlook)

        # Should not set season outlook
        assert not hasattr(player, "season_outlook") or player.season_outlook is None

        # Should still process stats under stats namespace
        assert len(player.stats["projections"]) > 0

    def test_player_to_model_includes_all_kona_playercard_data(self, carroll_player_data):
        """Test that Player.to_model() includes all kona_playercard data (projections, seasonal stats, outlook)"""
        # Create and hydrate player
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})
        player.hydrate_kona_playercard(carroll_player_data)

        # Convert to model
        model = player.to_model()

        # Verify model includes all projection data through stats namespace
        assert isinstance(model, PlayerModel)
        assert model.season_outlook is not None
        assert "2023 NL Rookie of the Year" in model.season_outlook

        assert model.stats is not None
        assert "projections" in model.stats
        assert model.stats["projections"]["AB"] == 377.0
        assert model.stats["projections"]["HR"] == 19.0

        assert "preseason" in model.stats
        assert len(model.stats["preseason"]) > 0

        assert "regular_season" in model.stats
        assert len(model.stats["regular_season"]) > 0

        assert "previous_season" in model.stats
        assert len(model.stats["previous_season"]) > 0

    def test_player_from_model_preserves_kona_playercard_data(self, carroll_player_data):
        """Test that Player.from_model() preserves all kona_playercard data"""
        # Create and hydrate original player
        original_player = Player({"id": 42404, "fullName": "Corbin Carroll"})
        merged_data = {**carroll_player_data["player"], **carroll_player_data}
        original_player.hydrate_kona_playercard(merged_data)

        # Convert to model and back to player
        model = original_player.to_model()
        restored_player = Player.from_model(model)

        # Verify projection data is preserved through stats namespace
        assert restored_player.season_outlook == original_player.season_outlook
        assert restored_player.stats["projections"] == original_player.stats["projections"]
        assert restored_player.stats["preseason"] == original_player.stats["preseason"]
        assert restored_player.stats["regular_season"] == original_player.stats["regular_season"]
        assert restored_player.stats["previous_season"] == original_player.stats["previous_season"]

    def test_player_model_serialization_and_deserialization(self, ohtani_player_data):
        """Test PlayerModel JSON serialization and deserialization with kona_playercard data"""
        # Create and hydrate player
        player = Player({"id": 39832, "fullName": "Shohei Ohtani"})
        player.hydrate_kona_playercard(ohtani_player_data)

        # Convert to model
        model = player.to_model()

        # Serialize to JSON
        json_data = model.model_dump_json()
        assert isinstance(json_data, str)

        # Deserialize from JSON
        deserialized_model = PlayerModel.model_validate_json(json_data)

        # Verify all projection data is preserved through stats namespace
        assert deserialized_model.season_outlook == model.season_outlook
        assert deserialized_model.stats["projections"] == model.stats["projections"]
        assert deserialized_model.stats["preseason"] == model.stats["preseason"]
        assert deserialized_model.stats["regular_season"] == model.stats["regular_season"]
        assert deserialized_model.stats["previous_season"] == model.stats["previous_season"]

    def test_both_players_in_fixture_process_correctly(self, kona_playercard_fixture_data):
        """Test that both players in the fixture (Carroll and Ohtani) process correctly"""
        players = kona_playercard_fixture_data["players"]

        processed_players = []
        for player_data in players:
            # Create player object
            player = Player(
                {"id": player_data["id"], "fullName": player_data["player"]["fullName"]}
            )

            # Hydrate with complete player dict from API response
            player.hydrate_kona_playercard(player_data)
            processed_players.append(player)

        # Verify both players were processed
        assert len(processed_players) == 2

        # Verify Carroll (first player)
        carroll = processed_players[0]
        assert carroll.id == 42404
        assert carroll.season_outlook is not None
        assert "2023 NL Rookie of the Year" in carroll.season_outlook
        assert carroll.stats["projections"]["HR"] == 19.0
        assert carroll.stats["projections"]["SB"] == 21.0

        # Verify Ohtani (second player)
        ohtani = processed_players[1]
        assert ohtani.id == 39832
        assert ohtani.season_outlook is not None
        assert ohtani.stats["previous_season"]["HR"] == 54.0  # 2024 stats
        assert ohtani.stats["previous_season"]["AB"] == 636.0

    def test_model_conversion_preserves_all_existing_player_data(
        self, carroll_player_data
    ):
        """Test that model conversion preserves existing player data along with kona_playercard data"""
        # Create player with some existing data
        player_data = {
            "id": 42404,
            "fullName": "Corbin Carroll",
            "firstName": "Corbin",
            "lastName": "Carroll",
        }
        player = Player(player_data)

        # Add some existing attributes
        player.name = "Corbin Carroll"
        player.pro_team = "ARI"
        player.primary_position = "OF"

        # Hydrate with projections
        player.hydrate_kona_playercard(carroll_player_data)

        # Convert to model
        model = player.to_model()

        # Verify both existing and new data are preserved
        assert model.id == 42404
        assert model.name == "Corbin Carroll"
        assert model.pro_team == "ARI"
        assert model.primary_position == "OF"

        # And projection data is included through stats namespace
        assert model.season_outlook is not None
        assert model.stats is not None
        assert "projections" in model.stats
        assert model.stats["projections"]["HR"] == 19.0
