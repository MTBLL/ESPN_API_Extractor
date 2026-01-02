import pytest

from espn_api_extractor.baseball.constants import STATS_MAP
from espn_api_extractor.baseball.player import Player


class TestPlayerEnhanced:
    """Enhanced tests for the Player class to improve coverage"""

    @pytest.fixture
    def player_missing_data(self):
        """Fixture providing player data with minimal fields"""
        return {"id": 12345, "fullName": "Minimal Player"}

    @pytest.fixture
    def player_with_acquisition_data(self):
        """Fixture providing player data with acquisition type"""
        return {
            "id": 12345,
            "fullName": "Drafted Player",
            "acquisitionType": "DRAFT",
            "lineupSlotId": 10,  # RF
        }

    def test_player_with_stats_processing(
        self, corbin_carroll_kona_card, corbin_carroll_season
    ):
        """Test player initialization with stats processing"""
        player = Player(corbin_carroll_kona_card, corbin_carroll_season)
        stats_entries = corbin_carroll_kona_card["player"]["stats"]
        current_stats_entry = next(
            entry
            for entry in stats_entries
            if entry.get("seasonId") == corbin_carroll_season
            and entry.get("statSourceId") == 0
            and entry.get("statSplitTypeId") == 0
        )
        projections_entry = next(
            entry
            for entry in stats_entries
            if entry.get("seasonId") == corbin_carroll_season
            and entry.get("statSourceId") == 1
            and entry.get("statSplitTypeId") == 0
        )
        mapped_current = {
            STATS_MAP.get(int(k), str(k)): v
            for k, v in current_stats_entry["stats"].items()
        }
        mapped_projections = {
            STATS_MAP.get(int(k), str(k)): v
            for k, v in projections_entry["stats"].items()
        }

        # Verify stats are processed correctly with readable keys
        # Use dynamic key for previous_season (e.g., "previous_season_24")
        current_year = corbin_carroll_season
        previous_year = current_year - 1
        previous_season_key = f"previous_season_{str(previous_year)[-2:]}"

        assert "current_season" in player.stats
        assert "last_7_games" in player.stats
        assert previous_season_key in player.stats
        assert "projections" in player.stats

        # Verify current season stats
        current_season = player.stats["current_season"]
        assert "AB" in current_season
        assert current_season["AB"] == mapped_current["AB"]
        assert current_season["H"] == mapped_current["H"]
        assert current_season["AVG"] == mapped_current["AVG"]
        assert current_season["R"] == mapped_current["R"]

        # Verify projections
        projections = player.stats["projections"]
        assert "AB" in projections
        assert projections["AB"] == mapped_projections["AB"]
        assert projections["H"] == mapped_projections["H"]

        # Verify player info from playerPoolEntry
        assert player.injury_status == "ACTIVE"
        assert player.injured is False
        expected_percent_owned = round(
            corbin_carroll_kona_card["player"]["ownership"]["percentOwned"], 2
        )
        assert player.percent_owned == expected_percent_owned

    def test_empty_eligible_slots(self):
        """Test player with empty eligibleSlots field"""
        data = {"id": 123, "fullName": "Test Player", "eligibleSlots": []}
        player = Player(data)

        # Should have empty eligible_slots list
        assert player.eligible_slots == []

    def test_missing_eligible_slots(self):
        """Test player with missing eligibleSlots field"""
        data = {
            "id": 123,
            "fullName": "Test Player",
            # No eligibleSlots field
        }
        player = Player(data)

        # Should have empty eligible_slots list
        assert player.eligible_slots == []

    def test_player_ownership_formats(self):
        """Test different formats of ownership data"""
        # Test with percentOwned in top level
        data1 = {
            "id": 123,
            "fullName": "Test Player",
            "ownership": {"percentOwned": 88.5},
        }
        player1 = Player(data1)
        assert player1.percent_owned == 88.5

        # Test with ownership in player field
        data2 = {
            "id": 123,
            "fullName": "Test Player",
            "player": {"ownership": {"percentOwned": 77.3}},
        }
        player2 = Player(data2)
        assert player2.percent_owned == 77.3

        # Test with missing ownership
        data3 = {"id": 123, "fullName": "Test Player"}
        player3 = Player(data3)
        assert player3.percent_owned == -1

    def test_player_hydration_with_edge_cases(self):
        """Test player hydration with edge cases and missing fields"""
        player = Player({"id": 123, "fullName": "Test Player"})

        # Hydrate with minimal data
        player.hydrate_bio(
            {
                "displayName": "Test Player"
                # Missing many fields
            }
        )

        # Verify basic fields were set
        assert player.display_name == "Test Player"

        # Fields that depend on nested data should be initialized but None
        assert player.bats is None
        assert player.throws is None
        assert not hasattr(player, "status_name")  # This field is not in our init list
        assert not hasattr(
            player, "experience_years"
        )  # This field is not in our init list
        assert player.headshot is None

        # Default values for certain fields
        # active is set to False by hydrate_bio when not in data
        assert player.active is False

        # Hydrate with partial nested data
        player.hydrate_bio(
            {
                "position": {
                    "name": "Pitcher"
                    # Missing displayName and abbreviation
                },
                "status": {
                    "name": "Active"
                    # Missing type
                },
                "experience": {
                    # Missing years
                },
                "headshot": {
                    # Missing href
                },
            }
        )

        # Verify partial nested data handled properly
        assert player.position_name == "Pitcher"
        # The Player.hydrate method sets all position attributes from position dictionary
        # even if some fields are missing in the data
        assert player.pos is None  # None because it's missing in data
        assert player.status is None  # None because it's missing in data

        # experience_years is not set because the empty experience dictionary is not handled in the code
        assert not hasattr(player, "experience_years")

        # headshot remains None because the empty headshot dictionary doesn't have href
        assert player.headshot is None
