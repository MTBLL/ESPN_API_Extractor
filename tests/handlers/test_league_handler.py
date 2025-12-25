import pytest
from unittest.mock import MagicMock

from espn_api_extractor.handlers.league_handler import (
    DEFAULT_LEAGUE_VIEWS,
    LeagueHandler,
)
from espn_api_extractor.requests.constants import FantasySports


def test_uses_existing_requestor(monkeypatch):
    # Ensure the handler does not instantiate its own requestor when one is provided
    monkeypatch.setattr(
        "espn_api_extractor.handlers.league_handler.EspnFantasyRequests",
        MagicMock(side_effect=AssertionError("constructor should not be called")),
    )

    existing_requestor = MagicMock()

    handler = LeagueHandler(
        year=2024,
        league_id=12345,
        requestor=existing_requestor,
        views=("mTeam", "mRoster"),
    )

    assert handler.fantasy_requestor is existing_requestor
    assert handler.views == ["mTeam", "mRoster"]


def test_fetch_calls_get_league_data():
    requestor = MagicMock()
    requestor.get_league_data.return_value = {"league": "data"}

    handler = LeagueHandler(
        year=2024,
        league_id=6789,
        requestor=requestor,
        views=["mTeam", "mSettings"],
    )

    result = handler.fetch()

    assert result == {"league": "data"}
    requestor.get_league_data.assert_called_once_with(["mTeam", "mSettings"])


def test_initializes_requestor_with_cookies(monkeypatch):
    requestor = MagicMock()
    constructor = MagicMock(return_value=requestor)
    monkeypatch.setattr(
        "espn_api_extractor.handlers.league_handler.EspnFantasyRequests",
        constructor,
    )

    handler = LeagueHandler(
        year=2023,
        league_id=2468,
        espn_s2="token1",
        swid="token2",
    )

    constructor.assert_called_once_with(
        sport=FantasySports.MLB,
        year=2023,
        league_id=2468,
        cookies={"espn_s2": "token1", "SWID": "token2"},
    )
    assert handler.fantasy_requestor is requestor
    assert handler.views == list(DEFAULT_LEAGUE_VIEWS)


def test_initializes_with_default_views(monkeypatch):
    requestor = MagicMock()
    monkeypatch.setattr(
        "espn_api_extractor.handlers.league_handler.EspnFantasyRequests",
        MagicMock(return_value=requestor),
    )

    handler = LeagueHandler(year=2024, league_id=13579)

    assert handler.views == list(DEFAULT_LEAGUE_VIEWS)
    requestor.get_league_data.assert_not_called()
