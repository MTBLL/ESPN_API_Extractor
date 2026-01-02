"""
Unit tests for player statistics functionality.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.requests.core_requests import EspnCoreRequests
from tests.baseball.test_stats_fixtures import (
    SAMPLE_PLAYER_BASIC_INFO,
    SAMPLE_PLAYER_STATS_RESPONSE,
)


class TestPlayerStatistics:
    """Test player statistics functionality."""

    def test_player_hydrate_stats(self):
        """Test that a player can be hydrated with statistics data."""
        # Create a player
        player = Player(SAMPLE_PLAYER_BASIC_INFO)

        # Verify player was created with basic info
        assert player.id == 42404
        assert player.name == "Test Player"

        # Call the hydrate_stats method
        player.hydrate_stats(SAMPLE_PLAYER_STATS_RESPONSE)

        # Verify the player now has statistics in the stats dict
        assert "split_id" in player.stats
        assert player.stats["split_id"] == "0"
        assert player.stats["split_name"] == "All Splits"

        # Check the categories were added
        assert "categories" in player.stats
        assert "batting" in player.stats["categories"]
        assert "fielding" in player.stats["categories"]

        # Check specific batting stats
        batting = player.stats["categories"]["batting"]
        assert batting["display_name"] == "Batting"
        assert (
            batting["summary"]
            == "55-197, 14 HR, 5 3B, 9 2B, 32 RBI, 38 R, 18 BB, 9 SB, 53 K"
        )

        # Check specific stats values
        assert batting["stats"]["homeRuns"]["value"] == 14.0
        assert batting["stats"]["avg"]["display_value"] == ".279"

        # Check fielding stats
        fielding = player.stats["categories"]["fielding"]
        assert fielding["display_name"] == "Fielding"
        assert fielding["stats"]["fieldingPct"]["value"] == 0.99115044

    def test_player_model_with_stats(self):
        """Test that player statistics are properly included in the PlayerModel."""
        # Create a player and hydrate with statistics
        player = Player(SAMPLE_PLAYER_BASIC_INFO)
        player.hydrate_stats(SAMPLE_PLAYER_STATS_RESPONSE)

        # Convert to model
        model = player.to_model()

        # Verify model has statistics in the stats dict
        assert model.stats is not None
        assert "split_id" in model.stats
        assert model.stats["split_id"] == "0"
        assert model.stats["split_name"] == "All Splits"

        # Check categories in model
        assert "categories" in model.stats
        assert len(model.stats["categories"]) == 2
        assert "batting" in model.stats["categories"]
        assert "fielding" in model.stats["categories"]

        # Check specific stat values in model
        assert "batting" in model.stats["categories"]
        batting = model.stats["categories"]["batting"]
        assert batting["display_name"] == "Batting"

        # The stats dict contains nested dictionaries
        assert "homeRuns" in batting["stats"]
        assert batting["stats"]["homeRuns"]["value"] == 14.0
        assert "avg" in batting["stats"]
        assert batting["stats"]["avg"]["display_value"] == ".279"

        # Convert back to player
        player2 = Player.from_model(model)

        # Verify statistics were preserved in the stats dict
        assert "split_id" in player2.stats
        assert player2.stats["split_id"] == "0"
        assert (
            player2.stats["categories"]["batting"]["stats"]["homeRuns"]["value"] == 14.0
        )

    def test_relief_pitcher_advanced_stats_plus_computed_properties(
        self, josh_hader_kona_card
    ):
        # checking to see if SVHDs is mapped correctly and if IP and K/9 are computed correctly
        stats_entries = josh_hader_kona_card["player"]["stats"]
        season_ids = [
            entry.get("seasonId")
            for entry in stats_entries
            if isinstance(entry.get("seasonId"), int)
        ]
        current_season = max(season_ids) if season_ids else datetime.now().year

        player = Player(josh_hader_kona_card, current_season)
        projections_entry = next(
            entry
            for entry in stats_entries
            if entry.get("seasonId") == current_season
            and entry.get("statSourceId") == 1
            and entry.get("statSplitTypeId") == 0
        )
        raw_stats = projections_entry.get("stats", {})
        expected_svhd = raw_stats.get("83")
        outs = raw_stats.get("34")
        strikeouts = raw_stats.get("48")

        assert expected_svhd is not None
        assert player.stats["projections"]["SVHD"] == expected_svhd
        assert isinstance(outs, (int, float))
        assert isinstance(strikeouts, (int, float))

        outs_int = int(outs)
        expected_ip = outs_int // 3 + (outs_int % 3) / 10
        expected_k9 = (strikeouts / (outs_int / 3)) * 9 if outs_int else 0

        projections = player.stats["projections"]
        assert projections["IP"] == expected_ip
        assert projections["K/9"] == pytest.approx(expected_k9, rel=1e-3)

    @patch(
        "espn_api_extractor.requests.core_requests.EspnCoreRequests._fetch_player_stats"
    )
    def test_hydrate_player_with_statistics(self, mock_fetch_player_stats):
        """Test hydrating a player with statistics using the EspnCoreRequests class."""
        # Setup mock
        mock_fetch_player_stats.return_value = SAMPLE_PLAYER_STATS_RESPONSE

        # Create a player
        player = Player(SAMPLE_PLAYER_BASIC_INFO)

        # Create the core requests object
        core_requests = EspnCoreRequests(sport="mlb", year=2025)

        # Call the method to hydrate a player with statistics
        hydrated_player, success = core_requests._hydrate_player_with_stats(player)

        # Verify the result
        assert success is True
        assert "split_name" in hydrated_player.stats
        assert hydrated_player.stats["split_name"] == "All Splits"
        assert (
            hydrated_player.stats["categories"]["batting"]["stats"]["homeRuns"]["value"]
            == 14.0
        )

        # Verify mock was called
        mock_fetch_player_stats.assert_called_once_with(42404)
