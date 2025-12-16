from datetime import datetime

import pytest

from espn_api_extractor.baseball.player import Player


class TestPlayerEnhanced:
    """Enhanced tests for the Player class to improve coverage"""

    @pytest.fixture
    def basic_player_data(self):
        """Fixture providing basic player data"""
        return {
            "defaultPositionId": 8,
            "eligibleSlots": [9, 10, 5, 12, 16, 17],
            "fullName": "Corbin Carroll",
            "id": 42404,
            "proTeamId": 29,
        }

    @pytest.fixture
    def player_stats_data(self):
        """Fixture providing player data with stats"""
        current_year = datetime.now().year
        return {
            "defaultPositionId": 8,
            "eligibleSlots": [9, 10, 5, 12, 16, 17],
            "fullName": "Corbin Carroll",
            "id": 42404,
            "proTeamId": 29,
            "playerPoolEntry": {
                "player": {
                    "injuryStatus": "ACTIVE",
                    "injured": False,
                    "ownership": {"percentOwned": 99.8},
                    "stats": [
                        {
                            # Current year, regular season stats
                            "seasonId": current_year,
                            "statSplitTypeId": 0,
                            "stats": {
                                "0": 145,  # At bats
                                "1": 42,  # Hits
                                "2": 8,  # Home runs
                                "20": 12,  # Stolen bases
                            },
                            "appliedTotal": 120.5,
                            "scoringPeriodId": 0,
                            "statSourceId": 0,
                        },
                        {
                            # Current year, projected stats
                            "seasonId": current_year,
                            "statSplitTypeId": 0,
                            "appliedStats": {
                                "0": 600,  # At bats
                                "1": 165,  # Hits
                                "2": 28,  # Home runs
                                "20": 45,  # Stolen bases
                            },
                            "appliedTotal": 450.2,
                            "scoringPeriodId": 0,
                            "statSourceId": 1,
                        },
                        {
                            # Previous year stats (should be skipped)
                            "seasonId": current_year - 1,
                            "statSplitTypeId": 0,
                            "stats": {"0": 500, "1": 150},
                            "appliedTotal": 350.0,
                            "scoringPeriodId": 0,
                            "statSourceId": 0,
                        },
                        {
                            # Current year, weekly stats
                            "seasonId": current_year,
                            "statSplitTypeId": 1,  # Last 7 days
                            "stats": {"0": 24, "1": 8},
                            "appliedTotal": 20.5,
                            "scoringPeriodId": 10,  # Week 10
                            "statSourceId": 0,
                        },
                    ],
                }
            },
        }

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

    def test_player_with_stats_processing(self, player_stats_data):
        """Test player initialization with stats processing"""
        player = Player(player_stats_data)

        # Verify stats are processed correctly with readable keys
        assert "current_season" in player.stats
        assert "last_7_games" in player.stats
        assert "previous_season" in player.stats
        assert "projections" in player.stats

        # Verify current season stats
        current_season = player.stats["current_season"]
        assert "AB" in current_season
        assert current_season["AB"] == 145
        assert current_season["H"] == 42
        assert current_season["AVG"] == 8
        assert current_season["R"] == 12

        # Verify fantasy scoring in current_season
        assert "_fantasy_scoring" in current_season
        assert current_season["_fantasy_scoring"]["applied_total"] == 120.5

        # Verify projections
        projections = player.stats["projections"]
        assert "AB" in projections
        assert projections["AB"] == 600
        assert "_fantasy_scoring" in projections
        assert projections["_fantasy_scoring"]["applied_total"] == 450.2

        # Verify player info from playerPoolEntry
        assert player.injury_status == "ACTIVE"
        assert player.injured is False
        assert player.percent_owned == 99.8

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
        assert not hasattr(player, "experience_years")  # This field is not in our init list
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
