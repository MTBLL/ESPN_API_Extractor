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
        carroll_data = kona_playercard_fixture_data["players"][1]
        assert carroll_data["id"] == 42404
        return carroll_data

    @pytest.fixture
    def ohtani_player_data(self, kona_playercard_fixture_data):
        """Get Shohei Ohtani's player data from fixture"""
        ohtani_data = kona_playercard_fixture_data["players"][0]
        assert ohtani_data["id"] == 39832
        return ohtani_data

    def test_player_hydrate_kona_playercard_sets_season_outlook(
        self, carroll_player_data
    ):
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

    def test_player_hydrate_kona_playercard_sets_seasonal_stats(
        self, carroll_player_data
    ):
        """Test that kona_playercard hydration sets all seasonal stat dictionaries (last_7_games, regular, previous)"""
        # Create player object
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})

        # Hydrate with projections
        player.hydrate_kona_playercard(carroll_player_data)

        # Verify all seasonal stats were set under stats namespace
        assert hasattr(player, "stats")
        assert "last_7_games" in player.stats
        assert "current_season" in player.stats
        assert "previous_season" in player.stats

        # Verify they are dictionaries with data
        assert isinstance(player.stats["last_7_games"], dict)
        assert isinstance(player.stats["current_season"], dict)
        assert isinstance(player.stats["previous_season"], dict)

        assert len(player.stats["last_7_games"]) > 0
        assert len(player.stats["current_season"]) > 0
        assert len(player.stats["previous_season"]) > 0

    def test_player_hydrate_projections_maps_stat_keys_correctly(
        self, ohtani_player_data
    ):
        """Test that stat keys are correctly mapped from numeric to readable names"""
        # Create player object
        player = Player({"id": 39832, "fullName": "Shohei Ohtani"})

        # Hydrate with complete player dict from API response
        player.hydrate_kona_playercard(ohtani_player_data)

        # Test last_7_games stats mapping under stats namespace
        assert "AB" in player.stats["last_7_games"]
        assert player.stats["last_7_games"]["AB"] == 21.0  # From 012025 in fixture

        # Test current season stats mapping under stats namespace
        assert "AB" in player.stats["current_season"]
        assert player.stats["current_season"]["AB"] == 611.0  # From 002025 in fixture

        # Test previous season stats mapping (2024) under stats namespace
        assert "AB" in player.stats["previous_season"]
        assert "HR" in player.stats["previous_season"]
        assert player.stats["previous_season"]["AB"] == 636.0  # From 002024 in fixture
        assert player.stats["previous_season"]["HR"] == 54.0  # From 002024 in fixture

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
        assert player.stats["last_7_games"] == {}
        assert player.stats["current_season"] == {}
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

    def test_player_to_model_includes_all_kona_playercard_data(
        self, carroll_player_data
    ):
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

        assert "last_7_games" in model.stats
        assert len(model.stats["last_7_games"]) > 0

        assert "current_season" in model.stats
        assert len(model.stats["current_season"]) > 0

        assert "previous_season" in model.stats
        assert len(model.stats["previous_season"]) > 0

    def test_player_from_model_preserves_kona_playercard_data(
        self, carroll_player_data
    ):
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
        assert (
            restored_player.stats["projections"] == original_player.stats["projections"]
        )
        assert (
            restored_player.stats["last_7_games"]
            == original_player.stats["last_7_games"]
        )
        assert (
            restored_player.stats["current_season"]
            == original_player.stats["current_season"]
        )
        assert (
            restored_player.stats["previous_season"]
            == original_player.stats["previous_season"]
        )

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
        assert deserialized_model.stats["last_7_games"] == model.stats["last_7_games"]
        assert (
            deserialized_model.stats["current_season"] == model.stats["current_season"]
        )
        assert (
            deserialized_model.stats["previous_season"]
            == model.stats["previous_season"]
        )

    def test_both_players_in_fixture_process_correctly(
        self, kona_playercard_fixture_data
    ):
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

        # Verify Ohtani (first player)
        ohtani = processed_players[0]
        assert ohtani.id == 39832
        assert ohtani.season_outlook is not None
        assert "MVP honors" in ohtani.season_outlook

        # Verify Carroll (second player)
        carroll = processed_players[1]
        assert carroll.id == 42404
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

    def test_hydrate_kona_playercard_extracts_draft_auction_value(
        self, carroll_player_data
    ):
        """Test that hydrate_kona_playercard extracts draftAuctionValue from top-level"""
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})

        # Hydrate with complete player dict from API response
        player.hydrate_kona_playercard(carroll_player_data)

        # Verify draft auction value was extracted
        assert hasattr(player, "draft_auction_value")
        assert player.draft_auction_value == 0  # type: ignore[attr-defined]  # From fixture

    def test_hydrate_kona_playercard_extracts_on_team_id(self, carroll_player_data):
        """Test that hydrate_kona_playercard extracts onTeamId from top-level"""
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})

        # Hydrate with complete player dict from API response
        player.hydrate_kona_playercard(carroll_player_data)

        # Verify on team ID was extracted
        assert hasattr(player, "on_team_id")
        assert player.on_team_id == 0  # type: ignore[attr-defined]  # From fixture

    def test_hydrate_kona_playercard_extracts_draft_ranks(self, carroll_player_data):
        """Test that hydrate_kona_playercard extracts draftRanksByRankType"""
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})

        # Hydrate with complete player dict from API response
        player.hydrate_kona_playercard(carroll_player_data)

        # Verify draft ranks were extracted
        assert hasattr(player, "draft_ranks")
        assert isinstance(player.draft_ranks, dict)  # type: ignore[attr-defined]
        assert "ROTO" in player.draft_ranks  # type: ignore[attr-defined]
        assert "STANDARD" in player.draft_ranks  # type: ignore[attr-defined]

        # Verify ROTO rank data
        roto_rank = player.draft_ranks["ROTO"]  # type: ignore[attr-defined]
        assert roto_rank["auctionValue"] == 40
        assert roto_rank["rank"] == 7
        assert roto_rank["rankType"] == "ROTO"

        # Verify STANDARD rank data
        standard_rank = player.draft_ranks["STANDARD"]  # type: ignore[attr-defined]
        assert standard_rank["auctionValue"] == 31
        assert standard_rank["rank"] == 14
        assert standard_rank["rankType"] == "STANDARD"

    def test_hydrate_kona_playercard_extracts_games_by_position(
        self, carroll_player_data
    ):
        """Test that hydrate_kona_playercard extracts and maps games played by position"""
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})

        # Hydrate with kona_playercard data
        merged_data = {**carroll_player_data["player"], **carroll_player_data}
        player.hydrate_kona_playercard(merged_data)

        # Verify games played by position was extracted and mapped
        assert hasattr(player, "games_played_by_position")
        assert isinstance(player.games_played_by_position, dict)

        # Position ID 9 should be mapped to "CF" (center field)
        assert "CF" in player.games_played_by_position
        assert isinstance(player.games_played_by_position["CF"], int)

    def test_hydrate_kona_playercard_extracts_auction_value_average(
        self, carroll_player_data
    ):
        """Test that hydrate_kona_playercard extracts auction value average from ownership"""
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})

        # Hydrate with kona_playercard data
        merged_data = {**carroll_player_data["player"], **carroll_player_data}
        player.hydrate_kona_playercard(merged_data)

        # Verify auction value average was extracted
        assert hasattr(player, "auction_value_average")
        assert isinstance(player.auction_value_average, float)

    def test_hydrate_kona_playercard_updates_injury_status(self, carroll_player_data):
        """Test that hydrate_kona_playercard updates injury status from kona data"""
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})

        # Hydrate with kona_playercard data
        merged_data = {**carroll_player_data["player"], **carroll_player_data}
        player.hydrate_kona_playercard(merged_data)

        # Verify injury status was updated
        assert hasattr(player, "injured")
        assert player.injured is False  # From fixture
        assert hasattr(player, "injury_status")
        assert player.injury_status == "ACTIVE"  # From fixture

    def test_stat_mapping_uses_readable_names_only(self, carroll_player_data):
        """Test that stat keys are mapped from numeric to readable names and only readable names are stored"""
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})

        # Hydrate with kona_playercard data
        merged_data = {**carroll_player_data["player"], **carroll_player_data}
        player.hydrate_kona_playercard(merged_data)

        # Verify projections use readable stat names, not numeric keys (under stats namespace)
        assert hasattr(player, "stats")
        assert "projections" in player.stats
        assert len(player.stats["projections"]) > 0

        # Check that we have readable keys, not numeric keys
        projection_keys = list(player.stats["projections"].keys())
        assert "AB" in projection_keys  # At bats
        assert "H" in projection_keys  # Hits
        assert "HR" in projection_keys  # Home runs
        assert "SB" in projection_keys  # Stolen bases

        # Verify no numeric keys are present - only readable names or non-numeric keys
        for key in projection_keys:
            assert not key.isdigit(), (
                f"Found numeric key '{key}' in projections, should be readable name"
            )

        # Check other stat categories too - should only contain known mapped stats
        for stat_dict in [
            player.stats["last_7_games"],
            player.stats["current_season"],
            player.stats["previous_season"],
        ]:
            if stat_dict:
                for key in stat_dict.keys():
                    # Unknown numeric keys (like "22") should be filtered out
                    assert not key.isdigit(), (
                        f"Found numeric key '{key}' in stats, unknown numeric keys should be filtered out"
                    )

    def test_player_from_model_preserves_new_fields(self, carroll_player_data):
        """Test that Player.from_model() preserves new kona_playercard fields"""
        # Create and hydrate original player
        original_player = Player({"id": 42404, "fullName": "Corbin Carroll"})
        original_player.hydrate_kona_playercard(carroll_player_data)

        # Convert to model and back to player
        model = original_player.to_model()
        restored_player = Player.from_model(model)

        # Verify new fields are preserved
        assert (
            restored_player.draft_auction_value == original_player.draft_auction_value  # type: ignore[attr-defined]
        )
        assert restored_player.on_team_id == original_player.on_team_id  # type: ignore[attr-defined]
        assert restored_player.draft_ranks == original_player.draft_ranks  # type: ignore[attr-defined]
        assert (
            restored_player.games_played_by_position  # type: ignore[attr-defined]
            == original_player.games_played_by_position  # type: ignore[attr-defined]
        )
        assert (
            restored_player.auction_value_average  # type: ignore[attr-defined]
            == original_player.auction_value_average  # type: ignore[attr-defined]
        )

    def test_comprehensive_kona_playercard_data_extraction(self, ohtani_player_data):
        """Test comprehensive extraction of all kona_playercard data from Ohtani fixture"""
        player = Player({"id": 39832, "fullName": "Shohei Ohtani"})
        player.hydrate_kona_playercard(ohtani_player_data)

        # Verify season outlook
        assert hasattr(player, "season_outlook")
        assert player.season_outlook is not None  # type: ignore[attr-defined]
        assert "MVP honors" in player.season_outlook  # type: ignore[attr-defined]

        # Verify projections and seasonal stats (under stats namespace)
        assert len(player.stats["projections"]) > 0
        assert len(player.stats["previous_season"]) > 0

        # Verify fantasy data
        assert player.draft_auction_value is not None  # type: ignore[attr-defined]
        assert player.on_team_id is not None  # type: ignore[attr-defined]
        assert len(player.draft_ranks) > 0  # type: ignore[attr-defined]

        # Verify ownership data
        assert player.auction_value_average is not None

        # Verify all stats use readable names only (under stats namespace)
        all_stat_dicts = [
            player.stats["projections"],
            player.stats["last_7_games"],
            player.stats["current_season"],
            player.stats["previous_season"],
        ]

        for stat_dict in all_stat_dicts:
            if stat_dict:
                for key in stat_dict.keys():
                    # Skip special nested keys like _fantasy_scoring
                    if key.startswith("_"):
                        continue

                    assert isinstance(key, str), (
                        f"Stat key should be string, got {type(key)}"
                    )
                    # Unknown numeric keys should be filtered out, only mapped readable names should remain
                    assert not key.isdigit(), (
                        f"Found numeric key '{key}', unknown numeric keys should be filtered out"
                    )
                    assert len(key) <= 10, (
                        f"Stat key '{key}' seems too long, might not be properly mapped"
                    )
