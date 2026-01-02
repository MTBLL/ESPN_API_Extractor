from unittest.mock import MagicMock

import pytest

from espn_api_extractor.handlers.player_extract_handler import PlayerExtractHandler


def test_fetch_player_cards_raises_when_unconfigured():
    handler = PlayerExtractHandler()

    with pytest.raises(
        RuntimeError, match="PlayerExtractHandler is not configured for fetching"
    ):
        handler.fetch_player_cards()


def test_fetch_player_cards_parses_response_dict():
    fantasy_requests = MagicMock()
    fantasy_requests.get_player_cards.return_value = {"players": [{"id": 1}]}

    handler = PlayerExtractHandler(fantasy_requests=fantasy_requests)

    assert handler.fetch_player_cards() == [{"id": 1}]
    fantasy_requests.get_player_cards.assert_called_once_with(player_ids=[])


def test_fetch_player_cards_parses_response_list():
    fantasy_requests = MagicMock()
    fantasy_requests.get_player_cards.return_value = [{"id": 2}]

    handler = PlayerExtractHandler(fantasy_requests=fantasy_requests)

    assert handler.fetch_player_cards() == [{"id": 2}]
    fantasy_requests.get_player_cards.assert_called_once_with(player_ids=[])


def test_apply_pitcher_transforms_overrides_two_way_positions():
    handler = PlayerExtractHandler()
    player = MagicMock()
    player.eligible_slots = ["P", "UTIL"]

    data = {"primary_position": "DH", "pos": "DH", "position_name": "Designated Hitter"}
    handler.apply_pitcher_transforms(player, data)

    assert data["primary_position"] == "SP"
    assert data["pos"] == "SP"
    assert data["position_name"] == "Starting Pitcher"
