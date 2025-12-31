from unittest.mock import MagicMock

from espn_api_extractor.baseball.constants import STATS_MAP
from espn_api_extractor.handlers.league_handler import (
    DEFAULT_LEAGUE_VIEWS,
    EXCLUDED_LEAGUE_KEYS,
    EXCLUDED_SETTINGS_KEYS,
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


def test_fetch_calls_get_league_data(league_response_fixture):
    league = MagicMock()
    league.espn_request.get_league_data.return_value = league_response_fixture

    handler = LeagueHandler(
        year=2024,
        league_id=6789,
        league=league,
        views=["mTeam", "mSettings"],
    )

    result = handler.fetch()

    assert result["settings"]["acquisitionSettings"] == {
        "acquisitionBudget": league_response_fixture["settings"]["acquisitionSettings"][
            "acquisitionBudget"
        ]
    }
    categories = result["settings"]["scoringSettings"]["categories"]
    assert set(categories.keys()) == {"batting", "pitching"}

    scoring_items = league_response_fixture["settings"]["scoringSettings"][
        "scoringItems"
    ]
    expected_ids = {item["statId"] for item in scoring_items}
    category_ids = {
        entry["statId"]
        for entry in categories["batting"] + categories["pitching"]
    }
    assert category_ids == expected_ids
    source_by_id = {item["statId"]: item for item in scoring_items}
    for entry in categories["batting"] + categories["pitching"]:
        assert entry["name"] == STATS_MAP.get(entry["statId"], entry["statId"])
        assert entry["isReverseItem"] == source_by_id[entry["statId"]].get(
            "isReverseItem"
        )
    league.espn_request.get_league_data.assert_called_once_with(
        ["mTeam", "mSettings"]
    )


def test_fetch_drops_excluded_keys(league_response_fixture):
    league = MagicMock()
    league.espn_request.get_league_data.return_value = league_response_fixture

    handler = LeagueHandler(
        year=2024,
        league_id=6789,
        league=league,
    )

    result = handler.fetch()

    assert result["settings"]["acquisitionSettings"] == {
        "acquisitionBudget": league_response_fixture["settings"]["acquisitionSettings"][
            "acquisitionBudget"
        ]
    }
    for key in EXCLUDED_LEAGUE_KEYS:
        assert key not in result
    for key in EXCLUDED_SETTINGS_KEYS:
        assert key not in result["settings"]


def test_fetch_removes_waiver_process_status(league_response_fixture):
    league = MagicMock()
    league.espn_request.get_league_data.return_value = league_response_fixture

    handler = LeagueHandler(
        year=2024,
        league_id=6789,
        league=league,
    )

    result = handler.fetch()

    assert "waiverProcessStatus" not in result["status"]


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
