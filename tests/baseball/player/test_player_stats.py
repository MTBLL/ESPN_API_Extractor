"""
Unit tests for player statistics functionality.
"""

from unittest.mock import MagicMock, patch

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.requests.core_requests import EspnCoreRequests
from tests.baseball.test_stats_fixtures import (
    SAMPLE_PLAYER_BASIC_INFO,
    SAMPLE_PLAYER_STATS_RESPONSE,
)


class TestPlayerStatistics:
    """Test player statistics functionality."""

    def test_player_hydrate_statistics(self):
        """Test that a player can be hydrated with statistics data."""
        # Create a player
        player = Player(SAMPLE_PLAYER_BASIC_INFO)

        # Verify player was created with basic info
        assert player.id == 42404
        assert player.name == "Test Player"

        # Call the hydrate_statistics method
        player.hydrate_statistics(SAMPLE_PLAYER_STATS_RESPONSE)

        # Verify the player now has statistics
        assert hasattr(player, "season_stats")
        assert player.season_stats["split_id"] == "0"
        assert player.season_stats["split_name"] == "All Splits"

        # Check the categories were added
        assert "categories" in player.season_stats
        assert "batting" in player.season_stats["categories"]
        assert "fielding" in player.season_stats["categories"]

        # Check specific batting stats
        batting = player.season_stats["categories"]["batting"]
        assert batting["display_name"] == "Batting"
        assert (
            batting["summary"]
            == "55-197, 14 HR, 5 3B, 9 2B, 32 RBI, 38 R, 18 BB, 9 SB, 53 K"
        )

        # Check specific stats values
        assert batting["stats"]["homeRuns"]["value"] == 14.0
        assert batting["stats"]["avg"]["display_value"] == ".279"

        # Check fielding stats
        fielding = player.season_stats["categories"]["fielding"]
        assert fielding["display_name"] == "Fielding"
        assert fielding["stats"]["fieldingPct"]["value"] == 0.99115044

    def test_player_model_with_stats(self):
        """Test that player statistics are properly included in the PlayerModel."""
        # Create a player and hydrate with statistics
        player = Player(SAMPLE_PLAYER_BASIC_INFO)
        player.hydrate_statistics(SAMPLE_PLAYER_STATS_RESPONSE)

        # Convert to model
        model = player.to_model()

        # Verify model has statistics
        assert model.season_stats is not None
        assert model.season_stats.split_id == "0"
        assert model.season_stats.split_name == "All Splits"

        # Check categories in model
        assert len(model.season_stats.categories) == 2
        assert "batting" in model.season_stats.categories
        assert "fielding" in model.season_stats.categories

        # Check specific stat values in model
        # Access the categories, which is a dictionary of StatCategory objects
        # The StatCategory objects have display_name and stats attributes
        assert "batting" in model.season_stats.categories
        batting = model.season_stats.categories["batting"]
        assert batting.display_name == "Batting"

        # The stats attribute of a StatCategory is a dictionary of StatDetail objects
        assert "homeRuns" in batting.stats
        assert batting.stats["homeRuns"].value == 14.0
        assert "avg" in batting.stats
        assert batting.stats["avg"].display_value == ".279"

        # Convert back to player
        player2 = Player.from_model(model)

        # Verify statistics were preserved
        assert hasattr(player2, "season_stats")
        assert player2.season_stats["split_id"] == "0"
        assert (
            player2.season_stats["categories"]["batting"]["stats"]["homeRuns"]["value"]
            == 14.0
        )

    @patch(
        "espn_api_extractor.requests.core_requests.EspnCoreRequests._fetch_player_stats"
    )
    def test_hydrate_player_with_statistics(self, mock_fetch_player_stats):
        """Test hydrating a player with statistics using the EspnCoreRequests class."""
        # Setup mock
        mock_fetch_player_stats.return_value = SAMPLE_PLAYER_STATS_RESPONSE

        # Create a player
        player = Player(SAMPLE_PLAYER_BASIC_INFO)

        # Create a mock logger
        mock_logger = MagicMock()

        # Create the core requests object with the mock logger
        core_requests = EspnCoreRequests(sport="mlb", year=2025, logger=mock_logger)

        # Call the method to hydrate a player with statistics
        hydrated_player, success = core_requests._hydrate_player_with_stats(player)

        # Verify the result
        assert success is True
        assert hasattr(hydrated_player, "season_stats")
        assert hydrated_player.season_stats["split_name"] == "All Splits"
        assert (
            hydrated_player.season_stats["categories"]["batting"]["stats"]["homeRuns"][
                "value"
            ]
            == 14.0
        )

        # Verify mock was called
        mock_fetch_player_stats.assert_called_once_with(42404)
