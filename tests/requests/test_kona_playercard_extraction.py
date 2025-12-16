import json
from unittest.mock import Mock, patch

import pytest

from espn_api_extractor.baseball.constants import STATS_MAP
from espn_api_extractor.requests.constants import FantasySports
from espn_api_extractor.requests.fantasy_requests import EspnFantasyRequests


class TestProjectionsExtraction:
    """Test extraction and processing of projection data from ESPN API"""

    @pytest.fixture
    def mock_logger(self):
        return Mock()

    @pytest.fixture
    def fantasy_requests(self):
        return EspnFantasyRequests(
            sport=FantasySports.MLB,
            year=2025,
            league_id=None,
            cookies={},
        )

    @pytest.fixture
    def projections_fixture_data(self):
        """Load the kona_playercard projections fixture"""
        with open("tests/fixtures/kona_playercard_projections_fixture.json", "r") as f:
            return json.load(f)

    def test_get_player_cards_builds_correct_filters(self, fantasy_requests):
        """Test that get_player_cards builds the correct API filters"""
        player_ids = [42404, 39832]

        with patch.object(fantasy_requests, "_get") as mock_get:
            mock_get.return_value = {"players": []}

            fantasy_requests.get_player_cards(player_ids)

            # Verify the call was made with correct parameters
            mock_get.assert_called_once()
            call_args = mock_get.call_args

            # Check params
            assert call_args[1]["params"] == {
                "view": "kona_playercard",
                "scoringPeriodId": 0,
            }

            # Check headers contain the correct filter
            headers = call_args[1]["headers"]
            assert "x-fantasy-filter" in headers

            filter_data = json.loads(headers["x-fantasy-filter"])
            assert filter_data["players"]["filterIds"]["value"] == player_ids
            assert (
                filter_data["players"]["filterStatsForTopScoringPeriodIds"]["value"]
                == 1
            )

            # Verify additional values include projections and seasonal stats
            additional_values = filter_data["players"][
                "filterStatsForTopScoringPeriodIds"
            ]["additionalValue"]
            assert "002025" in additional_values  # current year stats
            assert "102025" in additional_values  # projections
            assert "002024" in additional_values  # previous year stats
            assert "012025" in additional_values  # last_7_games stats
            assert "022025" in additional_values  # regular season stats

    def test_extract_projections_from_fixture(self, projections_fixture_data):
        """Test extracting projection data from the fixture"""
        players = projections_fixture_data["players"]

        # Test first player (Corbin Carroll)
        carroll = players[1]
        assert carroll["id"] == 42404
        assert carroll["player"]["firstName"] == "Corbin"
        assert carroll["player"]["lastName"] == "Carroll"

        # Test season outlook exists
        assert "seasonOutlook" in carroll["player"]
        season_outlook = carroll["player"]["seasonOutlook"]
        assert isinstance(season_outlook, str)
        assert len(season_outlook) > 100  # Should be a substantial text
        assert "2023 NL Rookie of the Year" in season_outlook

        # Test stats array contains different stat types
        stats = carroll["player"]["stats"]

        # Find projection stats (id="102025")
        projection_stats = None
        last_7_games_stats = None
        current_season_stats = None

        for stat in stats:
            if stat["id"] == "102025":
                projection_stats = stat
            elif stat["id"] == "012025":
                last_7_games_stats = stat
            elif stat["id"] == "022025":
                current_season_stats = stat

        assert projection_stats is not None, "Projection stats (102025) should exist"
        assert last_7_games_stats is not None, "Preseason stats (012025) should exist"
        assert current_season_stats is not None, (
            "Regular season stats (022025) should exist"
        )

        # Test projection stats structure
        assert projection_stats["statSourceId"] == 1  # Projections source
        assert projection_stats["statSplitTypeId"] == 0
        assert "stats" in projection_stats

        # Test some key projection stats are present and reasonable
        proj_stats = projection_stats["stats"]
        assert "0" in proj_stats  # AB (at bats)
        assert "1" in proj_stats  # H (hits)
        assert "5" in proj_stats  # HR (home runs)
        assert "23" in proj_stats  # SB (stolen bases)

        # Verify projections are reasonable numbers
        assert proj_stats["0"] == 377.0  # AB
        assert proj_stats["1"] == 95.0  # H
        assert proj_stats["5"] == 19.0  # HR
        assert proj_stats["23"] == 21.0  # SB

    def test_extract_last_7_games_regular_and_previous_season_stats(
        self, projections_fixture_data
    ):
        """Test extracting last_7_games, regular season, and previous season stats from fixture"""
        players = projections_fixture_data["players"]
        ohtani = players[0]  # Shohei Ohtani

        assert ohtani["id"] == 39832
        stats = ohtani["player"]["stats"]

        # Find last_7_games, regular season, and previous season stats
        last_7_games_stats = None
        current_season_stats = None
        previous_season_stats = None

        for stat in stats:
            if stat["id"] == "012025":
                last_7_games_stats = stat
            elif stat["id"] == "022025":
                current_season_stats = stat
            elif stat["id"] == "002024":
                previous_season_stats = stat

        assert last_7_games_stats is not None
        assert current_season_stats is not None
        assert previous_season_stats is not None

        # Test last_7_games stats
        last_7 = last_7_games_stats["stats"]
        assert "0" in last_7  # AB
        assert last_7["0"] == 21.0  # Preseason AB

        # Test regular season stats
        reg_stats = current_season_stats["stats"]
        assert "0" in reg_stats  # AB
        assert reg_stats["0"] == 54.0  # Regular season AB

        # Test previous season stats (2024)
        prev_stats = previous_season_stats["stats"]
        assert "0" in prev_stats  # AB
        assert prev_stats["0"] == 636.0  # 2024 season AB
        assert "5" in prev_stats  # HR
        assert prev_stats["5"] == 54.0  # 2024 season HR

    def test_stat_key_mapping_with_constants(self, projections_fixture_data):
        """Test that stat keys can be mapped using STATS_MAP constants"""
        players = projections_fixture_data["players"]
        carroll = players[1]

        # Find projection stats
        projection_stats = None
        for stat in carroll["player"]["stats"]:
            if stat["id"] == "102025":
                projection_stats = stat
                break

        assert projection_stats is not None
        proj_stats = projection_stats["stats"]

        # Test mapping some key stats
        assert "0" in proj_stats  # AB
        assert STATS_MAP[0] == "AB"

        assert "1" in proj_stats  # H
        assert STATS_MAP[1] == "H"

        assert "5" in proj_stats  # HR
        assert STATS_MAP[5] == "HR"

        assert "23" in proj_stats  # SB
        assert STATS_MAP[23] == "SB"

        # Test that we can create a mapped dictionary
        mapped_stats = {}
        for key, value in proj_stats.items():
            stat_key = int(key)
            if stat_key in STATS_MAP:
                mapped_stats[STATS_MAP[stat_key]] = value

        # Verify mapped stats
        assert mapped_stats["AB"] == 377.0
        assert mapped_stats["H"] == 95.0
        assert mapped_stats["HR"] == 19.0
        assert mapped_stats["SB"] == 21.0

    def test_multiple_players_data_structure(self, projections_fixture_data):
        """Test that the fixture contains multiple players with consistent structure"""
        players = projections_fixture_data["players"]
        assert len(players) == 2  # Should have Carroll and Ohtani

        for player in players:
            # Test basic structure
            assert "id" in player
            assert "player" in player
            assert "firstName" in player["player"]
            assert "lastName" in player["player"]
            assert "seasonOutlook" in player["player"]
            assert "stats" in player["player"]

            # Test that stats is a list
            assert isinstance(player["player"]["stats"], list)

            # Test that each player has multiple stat periods
            stat_ids = [stat["id"] for stat in player["player"]["stats"]]
            # Should have at least projections, last_7_games, and regular season
            assert len([sid for sid in stat_ids if sid.endswith("2025")]) >= 3
