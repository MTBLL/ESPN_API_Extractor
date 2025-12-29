import json

from unittest.mock import patch

from espn_api_extractor.requests.constants import FantasySports
from espn_api_extractor.requests.fantasy_requests import EspnFantasyRequests


def test_get_league_calls_league_get_with_views():
    requestor = EspnFantasyRequests(
        sport=FantasySports.MLB,
        year=2025,
        league_id=10998,
        cookies={},
    )

    with patch.object(requestor, "league_get") as mock_league_get:
        mock_league_get.return_value = {"league": "data"}

        result = requestor.get_league()

        assert result == {"league": "data"}
        mock_league_get.assert_called_once_with(
            params={
                "view": ["mTeam", "mRoster", "mMatchup", "mSettings", "mStandings"]
            }
        )


def test_get_league_data_calls_league_get_with_custom_views():
    requestor = EspnFantasyRequests(
        sport=FantasySports.MLB,
        year=2025,
        league_id=10998,
        cookies={},
    )

    with patch.object(requestor, "league_get") as mock_league_get:
        mock_league_get.return_value = {"league": "data"}

        result = requestor.get_league_data(["mSettings", "mRoster"])

        assert result == {"league": "data"}
        mock_league_get.assert_called_once_with(
            params={"view": ["mSettings", "mRoster"]}
        )


def test_get_league_draft_calls_league_get():
    requestor = EspnFantasyRequests(
        sport=FantasySports.MLB,
        year=2025,
        league_id=10998,
        cookies={},
    )

    with patch.object(requestor, "league_get") as mock_league_get:
        mock_league_get.return_value = {"draftDetail": {}}

        result = requestor.get_league_draft()

        assert result == {"draftDetail": {}}
        mock_league_get.assert_called_once_with(params={"view": "mDraftDetail"})


def test_get_league_message_board_without_types_calls_get():
    requestor = EspnFantasyRequests(
        sport=FantasySports.MLB,
        year=2025,
        league_id=10998,
        cookies={},
    )

    with patch.object(requestor, "_get") as mock_get:
        mock_get.return_value = {"topics": []}

        result = requestor.get_league_message_board()

        assert result == {"topics": []}
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["params"] == {"view": "kona_league_messageboard"}
        assert call_kwargs["headers"] == {}
        assert call_kwargs["extend"] == "/segments/0/leagues/10998/communication"


def test_get_league_message_board_with_types_builds_filters():
    requestor = EspnFantasyRequests(
        sport=FantasySports.MLB,
        year=2025,
        league_id=10998,
        cookies={},
    )

    with patch.object(requestor, "_get") as mock_get:
        mock_get.return_value = {"topics": []}

        requestor.get_league_message_board(msg_types=[178, 180])

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["params"] == {"view": "kona_league_messageboard"}
        assert call_kwargs["extend"] == "/segments/0/leagues/10998/communication"

        headers = call_kwargs["headers"]
        assert "x-fantasy-filter" in headers
        filter_data = json.loads(headers["x-fantasy-filter"])
        topics_by_type = filter_data["topicsByType"]
        assert set(topics_by_type.keys()) == {"178", "180"}
        for topic in topics_by_type.values():
            assert topic["sortMessageDate"]["sortPriority"] == 1
            assert topic["sortMessageDate"]["sortAsc"] is False


def test_get_player_card_builds_filters_with_additional_values():
    requestor = EspnFantasyRequests(
        sport=FantasySports.MLB,
        year=2025,
        league_id=10998,
        cookies={},
    )

    with patch.object(requestor, "league_get") as mock_league_get:
        mock_league_get.return_value = {"players": []}

        requestor.get_player_card(
            playerIds=[39832, 42404],
            max_scoring_period=2,
            additional_filters=["012025"],
        )

        mock_league_get.assert_called_once()
        call_kwargs = mock_league_get.call_args.kwargs
        assert call_kwargs["params"] == {"view": "kona_playercard"}

        headers = call_kwargs["headers"]
        assert "x-fantasy-filter" in headers
        filter_data = json.loads(headers["x-fantasy-filter"])
        assert filter_data["players"]["filterIds"]["value"] == [39832, 42404]
        stats_filter = filter_data["players"]["filterStatsForTopScoringPeriodIds"]
        assert stats_filter["value"] == 2
        assert "002025" in stats_filter["additionalValue"]
        assert "102025" in stats_filter["additionalValue"]
        assert "012025" in stats_filter["additionalValue"]
