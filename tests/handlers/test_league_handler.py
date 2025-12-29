from unittest.mock import MagicMock

from espn_api_extractor.handlers.league_handler import (
    DEFAULT_LEAGUE_VIEWS,
    LeagueHandler,
)


def test_uses_existing_league(monkeypatch):
    # Ensure the handler does not instantiate its own league when one is provided
    monkeypatch.setattr(
        "espn_api_extractor.handlers.league_handler.League",
        MagicMock(side_effect=AssertionError("constructor should not be called")),
    )

    existing_league = MagicMock()

    handler = LeagueHandler(
        year=2024,
        league_id=12345,
        league=existing_league,
        views=("mTeam", "mRoster"),
    )

    assert handler.league is existing_league
    assert handler.views == ["mTeam", "mRoster"]


def test_fetch_calls_get_league_data():
    league = MagicMock()
    league.espn_request.get_league_data.return_value = {"league": "data"}

    handler = LeagueHandler(
        year=2024,
        league_id=6789,
        league=league,
        views=["mTeam", "mSettings"],
    )

    result = handler.fetch()

    assert result == {"league": "data"}
    league.espn_request.get_league_data.assert_called_once_with(
        ["mTeam", "mSettings"]
    )


def test_initializes_league_with_cookies(monkeypatch):
    league = MagicMock()
    constructor = MagicMock(return_value=league)
    monkeypatch.setattr(
        "espn_api_extractor.handlers.league_handler.League",
        constructor,
    )

    handler = LeagueHandler(
        year=2023,
        league_id=2468,
        espn_s2="token1",
        swid="token2",
    )

    constructor.assert_called_once_with(
        year=2023,
        league_id=2468,
        espn_s2="token1",
        swid="token2",
        fetch_league=False,
    )
    assert handler.league is league
    assert handler.views == list(DEFAULT_LEAGUE_VIEWS)


def test_initializes_with_default_views(monkeypatch):
    league = MagicMock()
    monkeypatch.setattr(
        "espn_api_extractor.handlers.league_handler.League",
        MagicMock(return_value=league),
    )

    handler = LeagueHandler(year=2024, league_id=13579)

    assert handler.views == list(DEFAULT_LEAGUE_VIEWS)
    league.espn_request.get_league_data.assert_not_called()
