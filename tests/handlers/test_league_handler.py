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

    expected = {
        "id": source_matchup["id"],
        "matchupPeriodId": source_matchup["matchupPeriodId"],
        "playoffTierType": source_matchup["playoffTierType"],
        "winner": expected_winner,
        "teams": expected_teams,
    }

    # Pitcher games-started is preserved per team when ESPN returns statBySlot.
    def _expected_games_started(team_record):
        for slot_entry in team_record.get("statBySlot", {}).values():
            if slot_entry.get("statId") == 33:
                return {
                    "value": slot_entry.get("value"),
                    "limitExceeded": slot_entry.get("limitExceeded"),
                    "exceededOnScoringPeriod": slot_entry.get(
                        "exceededOnScoringPeriod"
                    ),
                }
        return None

    expected_games_started = {}
    home_gs = _expected_games_started(home_record)
    if home_gs is not None:
        expected_games_started[home["teamId"]] = home_gs
    away_gs = _expected_games_started(away_record)
    if away_gs is not None:
        expected_games_started[away["teamId"]] = away_gs
    if expected_games_started:
        expected["gamesStarted"] = expected_games_started

    assert simplified_matchup == expected


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


def test_fetch_preserves_category_results():
    """H2H category leagues keep per-category scoreByStat breakdown."""
    league = MagicMock()
    league.espn_request.get_league.return_value = {
        "id": 1,
        "settings": None,
        "status": {},
        "teams": None,
        "schedule": [
            {
                "id": 10,
                "matchupPeriodId": 1,
                "playoffTierType": "NONE",
                "winner": "HOME",
                "home": {
                    "teamId": 3,
                    "cumulativeScore": {
                        "wins": 2,
                        "losses": 1,
                        "ties": 0,
                        "scoreByStat": {
                            "20": {"score": 45, "result": "WIN"},
                            "5": {"score": 12, "result": "LOSS"},
                            "47": {"score": 3.10, "result": "TIE"},
                            # Component stat (no win/loss) -> filtered out
                            "1": {"score": 88, "result": None},
                        },
                    },
                },
                "away": {
                    "teamId": 7,
                    "cumulativeScore": {
                        "wins": 1,
                        "losses": 2,
                        "ties": 0,
                        "scoreByStat": {
                            "20": {"score": 40, "result": "LOSS"},
                            "5": {"score": 15, "result": "WIN"},
                            "47": {"score": 3.10, "result": "TIE"},
                        },
                    },
                },
            },
            {
                # Non-category matchup: no scoreByStat -> no categoryResults key
                "id": 11,
                "matchupPeriodId": 1,
                "playoffTierType": "NONE",
                "winner": "AWAY",
                "home": {"teamId": 4, "cumulativeScore": {"wins": 0}},
                "away": {"teamId": 8, "cumulativeScore": {"wins": 0}},
            },
        ],
    }

    handler = LeagueHandler(year=2024, league_id=6789, league=league)
    result = handler.fetch()

    category_matchup = next(m for m in result["schedule"] if m["id"] == 10)
    # Component stat "1" (H, result=None) is filtered; only scored categories remain.
    # Keyed by stat ID (not name) so non-injective STATS_MAP entries can't collide.
    assert category_matchup["categoryResults"] == {
        3: {
            20: {"name": "R", "value": 45, "result": "WIN"},
            5: {"name": "HR", "value": 12, "result": "LOSS"},
            47: {"name": "ERA", "value": 3.10, "result": "TIE"},
        },
        7: {
            20: {"name": "R", "value": 40, "result": "LOSS"},
            5: {"name": "HR", "value": 15, "result": "WIN"},
            47: {"name": "ERA", "value": 3.10, "result": "TIE"},
        },
    }
    # Component stat 1 (H, result=None) is filtered out
    assert 1 not in category_matchup["categoryResults"][3]
    # Category names resolved through the shared STATS_MAP
    assert STATS_MAP[20] == "R"

    plain_matchup = next(m for m in result["schedule"] if m["id"] == 11)
    assert "categoryResults" not in plain_matchup


def test_fetch_preserves_games_started():
    """Matchups carry per-team pitcher games-started count + cap flag."""
    league = MagicMock()
    league.espn_request.get_league.return_value = {
        "id": 1,
        "settings": None,
        "status": {},
        "teams": None,
        "schedule": [
            {
                "id": 48,
                "matchupPeriodId": 7,
                "playoffTierType": "NONE",
                "winner": "AWAY",
                "home": {
                    "teamId": 1,
                    "cumulativeScore": {
                        "wins": 0,
                        "statBySlot": {
                            "22": {
                                "statId": 33,
                                "value": 5,
                                "limitExceeded": False,
                                "exceededOnScoringPeriod": 0,
                            }
                        },
                    },
                },
                "away": {
                    "teamId": 8,
                    "cumulativeScore": {
                        "wins": 0,
                        "statBySlot": {
                            "22": {
                                "statId": 33,
                                "value": 2,
                                "limitExceeded": False,
                                "exceededOnScoringPeriod": 0,
                            }
                        },
                    },
                },
            },
            {
                # No statBySlot -> no gamesStarted key
                "id": 49,
                "matchupPeriodId": 7,
                "playoffTierType": "NONE",
                "winner": "HOME",
                "home": {"teamId": 2, "cumulativeScore": {"wins": 0}},
                "away": {"teamId": 9, "cumulativeScore": {"wins": 0}},
            },
        ],
    }

    handler = LeagueHandler(year=2024, league_id=6789, league=league)
    result = handler.fetch()

    matchup = next(m for m in result["schedule"] if m["id"] == 48)
    assert matchup["gamesStarted"] == {
        1: {"value": 5, "limitExceeded": False, "exceededOnScoringPeriod": 0},
        8: {"value": 2, "limitExceeded": False, "exceededOnScoringPeriod": 0},
    }

    plain = next(m for m in result["schedule"] if m["id"] == 49)
    assert "gamesStarted" not in plain


def test_build_games_started_limits():
    """Min + max games-started limits are derived into one settings block."""
    handler = LeagueHandler(year=2024, league_id=6789, league=MagicMock())

    settings = {
        "scoringSettings": {
            "statQualificationMinimum": {"limitValue": 4, "statId": 33},
        },
        "rosterSettings": {
            "lineupSlotStatLimits": {
                "22": {"limitValue": 1.4285714285714286, "statId": 33},
            },
        },
        "scheduleSettings": {"matchupPeriodLength": 7},
    }

    assert handler._build_games_started_limits(settings) == {
        "statId": 33,
        "min": 4,
        "maxPerScoringPeriod": 1.4285714285714286,
        "maxPerMatchup": 10,
    }

    # Wrong statId on either source is ignored; nothing usable -> None.
    assert (
        handler._build_games_started_limits(
            {
                "scoringSettings": {
                    "statQualificationMinimum": {"limitValue": 4, "statId": 81}
                },
                "rosterSettings": {
                    "lineupSlotStatLimits": {"7": {"limitValue": 9, "statId": 81}}
                },
            }
        )
        is None
    )

    # Min present but no cap / no period length -> maxPerMatchup is None.
    assert handler._build_games_started_limits(
        {"scoringSettings": {"statQualificationMinimum": {"limitValue": 4, "statId": 33}}}
    ) == {
        "statId": 33,
        "min": 4,
        "maxPerScoringPeriod": None,
        "maxPerMatchup": None,
    }


def test_fetch_adds_games_started_limits(league_response_fixture):
    """The derived gamesStartedLimits block is attached to settings."""
    league = MagicMock()
    league.espn_request.get_league.return_value = league_response_fixture

    handler = LeagueHandler(year=2024, league_id=6789, league=league)
    result = handler.fetch()

    limits = result["settings"]["gamesStartedLimits"]
    assert limits["statId"] == 33
    assert limits["min"] == 4
    assert limits["maxPerScoringPeriod"] == 1.4285714285714286


def test_format_games_started_handles_malformed_input():
    """Malformed statBySlot shapes are skipped, not raised on."""
    handler = LeagueHandler(year=2024, league_id=6789, league=MagicMock())

    # Non-dict cumulative_score -> None
    assert handler._format_games_started(None) is None
    assert handler._format_games_started("not a dict") is None

    # Missing / non-dict statBySlot -> None
    assert handler._format_games_started({"wins": 0}) is None
    assert handler._format_games_started({"statBySlot": "nope"}) is None

    # Non-dict slot entry skipped; no GS-statId entry -> None
    assert (
        handler._format_games_started(
            {"statBySlot": {"22": "bad", "23": {"statId": 81, "value": 30}}}
        )
        is None
    )

    # Well-formed GS entry comes through
    assert handler._format_games_started(
        {"statBySlot": {"22": {"statId": 33, "value": 7, "limitExceeded": True}}}
    ) == {"value": 7, "limitExceeded": True, "exceededOnScoringPeriod": None}


def test_format_category_results_handles_malformed_input():
    """Malformed scoreByStat shapes are skipped, not raised on."""
    handler = LeagueHandler(year=2024, league_id=6789, league=MagicMock())

    # Non-dict cumulative_score -> None
    assert handler._format_category_results(None) is None
    assert handler._format_category_results("not a dict") is None

    # Non-dict stat entry and non-integer stat key are both skipped; the one
    # well-formed scored category still comes through.
    score = {
        "cumulativeScore": {
            "scoreByStat": {
                "20": {"score": 45, "result": "WIN"},
                "5": "not a dict",
                "bogus": {"score": 1, "result": "WIN"},
            }
        }
    }
    assert handler._format_category_results(score["cumulativeScore"]) == {
        20: {"name": "R", "value": 45, "result": "WIN"},
    }


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
