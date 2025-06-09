import json
import pytest

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.models.player_model import PlayerModel


class TestKonaPlayercardNewFields:
    """Test the new kona_playercard fields and comprehensive data extraction"""

    @pytest.fixture
    def kona_playercard_fixture_data(self):
        """Load the kona_playercard fixture data"""
        with open("tests/fixtures/kona_playercard_projections_fixture.json", "r") as f:
            return json.load(f)

    @pytest.fixture
    def carroll_full_data(self, kona_playercard_fixture_data):
        """Get Corbin Carroll's complete data from fixture"""
        carroll_data = kona_playercard_fixture_data["players"][0]
        assert carroll_data["id"] == 42404
        return carroll_data

    @pytest.fixture
    def ohtani_full_data(self, kona_playercard_fixture_data):
        """Get Shohei Ohtani's complete data from fixture"""
        ohtani_data = kona_playercard_fixture_data["players"][1]
        assert ohtani_data["id"] == 39832
        return ohtani_data

    def test_hydrate_kona_playercard_extracts_draft_auction_value(self, carroll_full_data):
        """Test that hydrate_kona_playercard extracts draftAuctionValue from top-level"""
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})
        
        # Hydrate with complete player dict from API response
        player.hydrate_kona_playercard(carroll_full_data)
        
        # Verify draft auction value was extracted
        assert hasattr(player, "draft_auction_value")
        assert player.draft_auction_value == 0  # From fixture

    def test_hydrate_kona_playercard_extracts_on_team_id(self, carroll_full_data):
        """Test that hydrate_kona_playercard extracts onTeamId from top-level"""
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})
        
        # Hydrate with both player and top-level data
        merged_data = {**carroll_full_data["player"], **carroll_full_data}
        player.hydrate_kona_playercard(merged_data)
        
        # Verify on team ID was extracted
        assert hasattr(player, "on_team_id")
        assert player.on_team_id == 0  # From fixture

    def test_hydrate_kona_playercard_extracts_draft_ranks(self, carroll_full_data):
        """Test that hydrate_kona_playercard extracts draftRanksByRankType"""
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})
        
        # Hydrate with complete player dict from API response
        player.hydrate_kona_playercard(carroll_full_data)
        
        # Verify draft ranks were extracted
        assert hasattr(player, "draft_ranks")
        assert isinstance(player.draft_ranks, dict)
        assert "ROTO" in player.draft_ranks
        assert "STANDARD" in player.draft_ranks
        
        # Verify ROTO rank data
        roto_rank = player.draft_ranks["ROTO"]
        assert roto_rank["auctionValue"] == 40
        assert roto_rank["rank"] == 7
        assert roto_rank["rankType"] == "ROTO"
        
        # Verify STANDARD rank data
        standard_rank = player.draft_ranks["STANDARD"]
        assert standard_rank["auctionValue"] == 31
        assert standard_rank["rank"] == 14
        assert standard_rank["rankType"] == "STANDARD"

    def test_hydrate_kona_playercard_extracts_games_by_position(self, carroll_full_data):
        """Test that hydrate_kona_playercard extracts and maps games played by position"""
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})
        
        # Hydrate with kona_playercard data
        merged_data = {**carroll_full_data["player"], **carroll_full_data}
        player.hydrate_kona_playercard(merged_data)
        
        # Verify games played by position was extracted and mapped
        assert hasattr(player, "games_played_by_position")
        assert isinstance(player.games_played_by_position, dict)
        
        # Position ID 9 should be mapped to "CF" (center field)
        assert "CF" in player.games_played_by_position
        assert player.games_played_by_position["CF"] == 62  # From fixture

    def test_hydrate_kona_playercard_extracts_auction_value_average(self, carroll_full_data):
        """Test that hydrate_kona_playercard extracts auction value average from ownership"""
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})
        
        # Hydrate with kona_playercard data
        merged_data = {**carroll_full_data["player"], **carroll_full_data}
        player.hydrate_kona_playercard(merged_data)
        
        # Verify auction value average was extracted
        assert hasattr(player, "auction_value_average")
        assert player.auction_value_average == 28.29850746268657  # From fixture

    def test_hydrate_kona_playercard_updates_injury_status(self, carroll_full_data):
        """Test that hydrate_kona_playercard updates injury status from kona data"""
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})
        
        # Hydrate with kona_playercard data
        merged_data = {**carroll_full_data["player"], **carroll_full_data}
        player.hydrate_kona_playercard(merged_data)
        
        # Verify injury status was updated
        assert hasattr(player, "injured")
        assert player.injured == False  # From fixture
        assert hasattr(player, "injury_status")
        assert player.injury_status == "ACTIVE"  # From fixture

    def test_stat_mapping_uses_readable_names_only(self, carroll_full_data):
        """Test that stat keys are mapped from numeric to readable names and only readable names are stored"""
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})
        
        # Hydrate with kona_playercard data
        merged_data = {**carroll_full_data["player"], **carroll_full_data}
        player.hydrate_kona_playercard(merged_data)
        
        # Verify projections use readable stat names, not numeric keys (under stats namespace)
        assert hasattr(player, "stats")
        assert "projections" in player.stats
        assert len(player.stats["projections"]) > 0
        
        # Check that we have readable keys, not numeric keys
        projection_keys = list(player.stats["projections"].keys())
        assert "AB" in projection_keys  # At bats
        assert "H" in projection_keys   # Hits
        assert "HR" in projection_keys  # Home runs
        assert "SB" in projection_keys  # Stolen bases
        
        # Verify no numeric keys are present - only readable names or non-numeric keys
        for key in projection_keys:
            assert not key.isdigit(), f"Found numeric key '{key}' in projections, should be readable name"
        
        # Check other stat categories too - should only contain known mapped stats
        for stat_dict in [player.stats["preseason"], player.stats["regular_season"], player.stats["previous_season"]]:
            if stat_dict:
                for key in stat_dict.keys():
                    # Unknown numeric keys (like "22") should be filtered out
                    assert not key.isdigit(), f"Found numeric key '{key}' in stats, unknown numeric keys should be filtered out"

    def test_player_model_includes_new_kona_playercard_fields(self, carroll_full_data):
        """Test that PlayerModel includes all new kona_playercard fields"""
        player = Player({"id": 42404, "fullName": "Corbin Carroll"})
        merged_data = {**carroll_full_data["player"], **carroll_full_data}
        player.hydrate_kona_playercard(merged_data)
        
        # Convert to model
        model = player.to_model()
        
        # Verify all new fields are in the model
        assert hasattr(model, "draft_auction_value")
        assert model.draft_auction_value == 0
        
        assert hasattr(model, "on_team_id")
        assert model.on_team_id == 0
        
        assert hasattr(model, "draft_ranks")
        assert isinstance(model.draft_ranks, dict)
        assert "ROTO" in model.draft_ranks
        assert model.draft_ranks["ROTO"]["auctionValue"] == 40
        
        assert hasattr(model, "games_played_by_position")
        assert isinstance(model.games_played_by_position, dict)
        assert "CF" in model.games_played_by_position
        assert model.games_played_by_position["CF"] == 62
        
        assert hasattr(model, "auction_value_average")
        assert model.auction_value_average == 28.29850746268657

    def test_player_model_serialization_with_new_fields(self, ohtani_full_data):
        """Test PlayerModel JSON serialization includes new kona_playercard fields"""
        player = Player({"id": 39832, "fullName": "Shohei Ohtani"})
        player.hydrate_kona_playercard(ohtani_full_data)
        
        # Convert to model and serialize
        model = player.to_model()
        json_data = model.model_dump_json()
        
        # Parse back to verify new fields are in JSON
        parsed_data = json.loads(json_data)
        
        assert "draft_auction_value" in parsed_data
        assert "on_team_id" in parsed_data
        assert "draft_ranks" in parsed_data
        assert "games_played_by_position" in parsed_data
        assert "auction_value_average" in parsed_data

    def test_player_from_model_preserves_new_fields(self, carroll_full_data):
        """Test that Player.from_model() preserves new kona_playercard fields"""
        # Create and hydrate original player
        original_player = Player({"id": 42404, "fullName": "Corbin Carroll"})
        original_player.hydrate_kona_playercard(carroll_full_data)
        
        # Convert to model and back to player
        model = original_player.to_model()
        restored_player = Player.from_model(model)
        
        # Verify new fields are preserved
        assert restored_player.draft_auction_value == original_player.draft_auction_value
        assert restored_player.on_team_id == original_player.on_team_id
        assert restored_player.draft_ranks == original_player.draft_ranks
        assert restored_player.games_played_by_position == original_player.games_played_by_position
        assert restored_player.auction_value_average == original_player.auction_value_average

    def test_comprehensive_kona_playercard_data_extraction(self, ohtani_full_data):
        """Test comprehensive extraction of all kona_playercard data from Ohtani fixture"""
        player = Player({"id": 39832, "fullName": "Shohei Ohtani"})
        player.hydrate_kona_playercard(ohtani_full_data)
        
        # Verify season outlook
        assert hasattr(player, "season_outlook")
        assert player.season_outlook is not None
        assert "MVP honors" in player.season_outlook
        
        # Verify projections and seasonal stats (under stats namespace)
        assert len(player.stats["projections"]) > 0
        assert len(player.stats["previous_season"]) > 0
        
        # Verify fantasy data
        assert player.draft_auction_value is not None
        assert player.on_team_id is not None
        assert len(player.draft_ranks) > 0
        
        # Verify ownership data
        assert player.auction_value_average is not None
        
        # Verify all stats use readable names only (under stats namespace)
        all_stat_dicts = [
            player.stats["projections"],
            player.stats["preseason"],
            player.stats["regular_season"],
            player.stats["previous_season"]
        ]
        
        for stat_dict in all_stat_dicts:
            if stat_dict:
                for key in stat_dict.keys():
                    assert isinstance(key, str), f"Stat key should be string, got {type(key)}"
                    # Unknown numeric keys should be filtered out, only mapped readable names should remain
                    assert not key.isdigit(), f"Found numeric key '{key}', unknown numeric keys should be filtered out"
                    assert len(key) <= 10, f"Stat key '{key}' seems too long, might not be properly mapped"