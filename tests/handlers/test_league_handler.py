from unittest.mock import MagicMock

from espn_api_extractor.baseball.constants import STATS_MAP
from espn_api_extractor.handlers.league_handler import (
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
    assert handler.views == ("mTeam", "mRoster")


def test_fetch_calls_get_league(league_response_fixture):
    league = MagicMock()
    league.espn_request.get_league.return_value = league_response_fixture

    handler = LeagueHandler(
        year=2024,
        league_id=6789,
        league=league,
        views=("mTeam", "mSettings"),
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
        entry["statId"] for entry in categories["batting"] + categories["pitching"]
    }
    assert category_ids == expected_ids
    source_by_id = {item["statId"]: item for item in scoring_items}
    for entry in categories["batting"] + categories["pitching"]:
        assert entry["name"] == STATS_MAP.get(entry["statId"], entry["statId"])
        assert entry["isReverseItem"] == source_by_id[entry["statId"]].get(
            "isReverseItem"
        )
    league.espn_request.get_league.assert_called_once_with()


def test_fetch_drops_excluded_keys(league_response_fixture):
    league = MagicMock()
    league.espn_request.get_league.return_value = league_response_fixture

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
    league.espn_request.get_league.return_value = league_response_fixture

    handler = LeagueHandler(
        year=2024,
        league_id=6789,
        league=league,
    )

    result = handler.fetch()

    assert "waiverProcessStatus" not in result["status"]


def test_fetch_simplifies_schedule(league_response_fixture):
    league = MagicMock()
    league.espn_request.get_league.return_value = league_response_fixture

    handler = LeagueHandler(
        year=2024,
        league_id=6789,
        league=league,
    )

    result = handler.fetch()

    source_matchup = None
    for matchup in league_response_fixture.get("schedule", []):
        home = matchup.get("home") or {}
        away = matchup.get("away") or {}
        if home.get("cumulativeScore") and away.get("cumulativeScore"):
            source_matchup = matchup
            break

    assert source_matchup is not None

    simplified_matchup = next(
        item for item in result["schedule"] if item["id"] == source_matchup["id"]
    )

    home = source_matchup.get("home") or {}
    away = source_matchup.get("away") or {}
    home_record = home.get("cumulativeScore", {})
    away_record = away.get("cumulativeScore", {})

    expected_teams = {
        home[
            "teamId"
        ]: f"{home_record.get('wins', 0)}-{home_record.get('losses', 0)}-{home_record.get('ties', 0)}",
        away[
            "teamId"
        ]: f"{away_record.get('wins', 0)}-{away_record.get('losses', 0)}-{away_record.get('ties', 0)}",
    }

    if source_matchup.get("winner") == "HOME":
        expected_winner = home["teamId"]
    elif source_matchup.get("winner") == "AWAY":
        expected_winner = away["teamId"]
    elif source_matchup.get("winner") == "TIE":
        expected_winner = "TIE"
    else:
        expected_winner = None

    assert simplified_matchup == {
        "id": source_matchup["id"],
        "matchupPeriodId": source_matchup["matchupPeriodId"],
        "playoffTierType": source_matchup["playoffTierType"],
        "winner": expected_winner,
        "teams": expected_teams,
    }


def test_fetch_marks_bye_week_when_single_team(league_response_fixture):
    league = MagicMock()
    league.espn_request.get_league.return_value = league_response_fixture

    handler = LeagueHandler(
        year=2024,
        league_id=6789,
        league=league,
    )

    result = handler.fetch()

    source_matchup = None
    for matchup in league_response_fixture.get("schedule", []):
        home = matchup.get("home") or {}
        away = matchup.get("away") or {}
        team_ids = [
            team_id
            for team_id in (home.get("teamId"), away.get("teamId"))
            if team_id is not None
        ]
        if len(team_ids) == 1:
            source_matchup = matchup
            break

    assert source_matchup is not None

    simplified_matchup = next(
        item for item in result["schedule"] if item["id"] == source_matchup["id"]
    )

    assert simplified_matchup["winner"] == "BYE WEEK"


def test_fetch_removes_roster_entry_stats(league_response_fixture):
    league = MagicMock()
    league.espn_request.get_league.return_value = league_response_fixture

    handler = LeagueHandler(
        year=2024,
        league_id=6789,
        league=league,
    )

    result = handler.fetch()

    source_player = (
        league_response_fixture["teams"][0]["roster"]["entries"][0]["playerPoolEntry"][
            "player"
        ]
    )
    assert "stats" in source_player
    assert "draftRanksByRankType" in source_player
    source_pool = league_response_fixture["teams"][0]["roster"]["entries"][0][
        "playerPoolEntry"
    ]
    assert "ratings" in source_pool

    filtered_player = (
        result["teams"][0]["roster"]["entries"][0]["playerPoolEntry"]["player"]
    )
    assert "stats" not in filtered_player
    assert "draftRanksByRankType" not in filtered_player
    filtered_pool = result["teams"][0]["roster"]["entries"][0]["playerPoolEntry"]
    assert "ratings" not in filtered_pool


def test_fetch_handles_missing_sections():
    league = MagicMock()
    league.espn_request.get_league.return_value = {
        "id": 1,
        "settings": None,
        "status": {},
        "schedule": None,
        "teams": None,
    }

    handler = LeagueHandler(
        year=2024,
        league_id=6789,
        league=league,
    )

    result = handler.fetch()

    assert result["settings"] is None
    assert result["schedule"] is None
    assert result["teams"] is None


def test_fetch_handles_roster_entry_shapes():
    league = MagicMock()
    league.espn_request.get_league.return_value = {
        "id": 1,
        "settings": None,
        "status": {},
        "teams": [
            {"id": 1, "roster": None},
            {"id": 2, "roster": {"entries": "not-a-list"}},
            {
                "id": 3,
                "roster": {
                    "entries": [
                        {
                            "player": {
                                "fullName": "Entry Player",
                                "stats": [1],
                                "draftRanksByRankType": {"STANDARD": {"rank": 1}},
                            }
                        },
                        {
                            "playerPoolEntry": {
                                "player": {
                                    "fullName": "Pool Player",
                                    "stats": [2],
                                    "draftRanksByRankType": {"STANDARD": {"rank": 2}},
                                },
                                "ratings": {"0": {"totalRating": 1.0}},
                            },
                            "player": {
                                "fullName": "Entry Player 2",
                                "stats": [3],
                                "draftRanksByRankType": {"STANDARD": {"rank": 3}},
                            },
                        },
                    ]
                },
            },
        ],
    }

    handler = LeagueHandler(
        year=2024,
        league_id=6789,
        league=league,
    )

    result = handler.fetch()

    assert result["teams"][0]["roster"] is None
    assert result["teams"][1]["roster"]["entries"] == "not-a-list"

    cleaned_entries = result["teams"][2]["roster"]["entries"]
    assert "stats" not in cleaned_entries[0]["player"]
    assert "draftRanksByRankType" not in cleaned_entries[0]["player"]

    cleaned_pool = cleaned_entries[1]["playerPoolEntry"]
    cleaned_pool_player = cleaned_pool["player"]
    assert "ratings" not in cleaned_pool
    assert "stats" not in cleaned_pool_player
    assert "draftRanksByRankType" not in cleaned_pool_player

    cleaned_entry_player = cleaned_entries[1]["player"]
    assert "stats" not in cleaned_entry_player
    assert "draftRanksByRankType" not in cleaned_entry_player


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
    assert handler.views is None


def test_initializes_with_default_views(monkeypatch):
    league = MagicMock()
    monkeypatch.setattr(
        "espn_api_extractor.handlers.league_handler.League",
        MagicMock(return_value=league),
    )

    handler = LeagueHandler(year=2024, league_id=13579)

    assert handler.views is None
    league.espn_request.get_league.assert_not_called()
