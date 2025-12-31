import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from espn_api_extractor.baseball.league import League
from espn_api_extractor.baseball.team import Team
from espn_api_extractor.baseball.box_score import BoxScore
from espn_api_extractor.base.base_settings import BaseSettings


def test_fetch_league_sets_scoring_type_and_box_score_class(
    monkeypatch, league_response_fixture
):
    league = League(league_id=1, year=2025, fetch_league=False)
    base_class = league.__class__.__bases__[0]
    data = league_response_fixture

    fetch_mock = MagicMock(return_value=data)
    teams_mock = MagicMock()
    draft_calls = []

    def fake_fetch_draft(self):
        draft_calls.append(self)

    monkeypatch.setattr(league, "_fetch_league", fetch_mock)
    monkeypatch.setattr(league, "_fetch_teams", teams_mock)
    monkeypatch.setattr(base_class, "_fetch_draft", fake_fetch_draft)

    league.fetch_league()

    assert league.scoring_type == "H2H_CATEGORY"
    assert league._box_score_class is League.ScoreTypes["H2H_CATEGORY"]
    fetch_mock.assert_called_once_with()
    teams_mock.assert_called_once_with(data)
    assert draft_calls == [league]


def test_league_init_calls_fetch_league_when_enabled(monkeypatch):
    fetch_mock = MagicMock()
    monkeypatch.setattr(League, "fetch_league", fetch_mock)

    league = League(league_id=1, year=2025, fetch_league=True)

    fetch_mock.assert_called_once_with()
    assert league._box_score_class is BoxScore


def test_fetch_league_calls_base_fetch_and_players(monkeypatch, league_response_fixture):
    league = League(league_id=1, year=2025, fetch_league=False)
    base_class = league.__class__.__bases__[0]
    data = league_response_fixture
    base_fetch_calls = []

    def fake_base_fetch(self, SettingsClass=BaseSettings):
        base_fetch_calls.append(SettingsClass)
        return data

    fetch_players = MagicMock()

    monkeypatch.setattr(base_class, "_fetch_league", fake_base_fetch)
    monkeypatch.setattr(league, "_fetch_players", fetch_players)

    result = league._fetch_league()

    assert result == data
    assert base_fetch_calls == [BaseSettings]
    fetch_players.assert_called_once_with()


def test_fetch_teams_maps_opponents_to_team_instances(league_response_fixture):
    league = League(league_id=1, year=2025, fetch_league=False)
    data = league_response_fixture
    for team in data["teams"]:
        roster = team.get("roster") or {}
        roster.setdefault("entries", [])
        team["roster"] = roster
    team_ids = [team["id"] for team in data["teams"][:2]]
    data["schedule"] = [
        {
            "home": {"teamId": team_ids[0], "totalPoints": 0},
            "away": {"teamId": team_ids[1], "totalPoints": 0},
            "winner": "UNDECIDED",
        },
        {
            "home": {"teamId": team_ids[1], "totalPoints": 0},
            "away": {"teamId": team_ids[0], "totalPoints": 0},
            "winner": "UNDECIDED",
        },
    ]
    division_map = {
        team["divisionId"]: f"Division {team['divisionId']}" for team in data["teams"]
    }
    league.settings = SimpleNamespace(division_map=division_map)  # type: ignore[reportAttributeAccess]

    league._fetch_teams(data)

    assert len(league.teams) == len(data["teams"])
    assert all(
        team_id in {team.team_id for team in league.teams} for team_id in team_ids
    )

    team_by_id = {team.team_id: team for team in league.teams}
    for team in league.teams:
        assert team.division_name == league.settings.division_map[team.division_id]
        if team.team_id in team_ids:
            for matchup in team.schedule:
                assert isinstance(matchup.home_team, Team)
                assert isinstance(matchup.away_team, Team)
                assert matchup.home_team is team_by_id[matchup.home_team.team_id]
                assert matchup.away_team is team_by_id[matchup.away_team.team_id]


def test_standings_orders_by_final_or_current():
    league = League(league_id=1, year=2025, fetch_league=False)
    team_a = SimpleNamespace(final_standing=0, standing=2)
    team_b = SimpleNamespace(final_standing=1, standing=3)
    league.teams = [team_a, team_b]

    assert league.standings() == [team_b, team_a]


def test_scoreboard_filters_matchup_period_and_maps_teams():
    league = League(league_id=1, year=2025, fetch_league=False)
    league.currentMatchupPeriod = 2
    team_a = SimpleNamespace(team_id=1)
    team_b = SimpleNamespace(team_id=2)
    league.teams = [team_a, team_b]

    schedule = [
        {
            "matchupPeriodId": 2,
            "home": {"teamId": 1, "totalPoints": 0},
            "away": {"teamId": 2, "totalPoints": 0},
            "winner": "UNDECIDED",
        },
        {
            "matchupPeriodId": 1,
            "home": {"teamId": 2, "totalPoints": 0},
            "away": {"teamId": 1, "totalPoints": 0},
            "winner": "UNDECIDED",
        },
    ]

    league.espn_request = MagicMock()
    league.espn_request.league_get.return_value = {"schedule": schedule}

    matchups = league.scoreboard()

    league.espn_request.league_get.assert_called_once_with(params={"view": "mMatchup"})
    assert len(matchups) == 1
    assert matchups[0].home_team is team_a
    assert matchups[0].away_team is team_b


def test_recent_activity_raises_before_2019():
    league = League(league_id=1, year=2018, fetch_league=False)

    with pytest.raises(Exception, match="Cant use recent activity before 2019"):
        league.recent_activity()


def test_recent_activity_builds_filters_and_returns_activity(monkeypatch):
    league = League(league_id=1, year=2025, fetch_league=False)
    league.espn_request = MagicMock()
    league.espn_request.league_get.return_value = {"topics": [{"id": 1}, {"id": 2}]}

    activity_factory = MagicMock(side_effect=["a1", "a2"])
    monkeypatch.setattr("espn_api_extractor.baseball.league.Activity", activity_factory)

    result = league.recent_activity(size=10, msg_type="FA", offset=3)

    call_kwargs = league.espn_request.league_get.call_args.kwargs
    assert call_kwargs["extend"] == "/communication/"
    assert call_kwargs["params"] == {"view": "kona_league_communication"}

    filters = json.loads(call_kwargs["headers"]["x-fantasy-filter"])
    assert filters["topics"]["limit"] == 10
    assert filters["topics"]["offset"] == 3
    assert filters["topics"]["filterIncludeMessageTypeIds"]["value"] == [178]

    assert result == ["a1", "a2"]
    assert activity_factory.call_args_list[0].args[0] == {"id": 1}
    assert activity_factory.call_args_list[1].args[0] == {"id": 2}


def test_free_agents_raises_before_2019():
    league = League(league_id=1, year=2018, fetch_league=False)

    with pytest.raises(Exception, match="Cant use free agents before 2019"):
        league.free_agents()


def test_free_agents_builds_filters_and_returns_players(monkeypatch):
    league = League(league_id=1, year=2025, fetch_league=False)
    league.current_week = 7
    league.espn_request = MagicMock()
    league.espn_request.league_get.return_value = {
        "players": [{"id": 1}, {"id": 2}]
    }

    player_factory = MagicMock(side_effect=["p1", "p2"])
    monkeypatch.setattr("espn_api_extractor.baseball.league.Player", player_factory)

    result = league.free_agents(week=0, size=10, position="1B", position_id=13)

    call_kwargs = league.espn_request.league_get.call_args.kwargs
    assert call_kwargs["params"] == {
        "view": "kona_player_info",
        "scoringPeriodId": 7,
    }

    filters = json.loads(call_kwargs["headers"]["x-fantasy-filter"])
    assert filters["players"]["limit"] == 10
    assert filters["players"]["filterSlotIds"]["value"] == [1, 13]
    assert result == ["p1", "p2"]


def test_box_scores_raises_before_2019():
    league = League(league_id=1, year=2018, fetch_league=False)

    with pytest.raises(Exception, match="Cant use box score before 2019"):
        league.box_scores()


def test_box_scores_maps_teams_and_filters_matchup():
    league = League(league_id=1, year=2025, fetch_league=False)
    league.currentMatchupPeriod = 3
    league.current_week = 8
    team_a = SimpleNamespace(team_id=1)
    team_b = SimpleNamespace(team_id=2)
    league.teams = [team_a, team_b]

    schedule = [
        {
            "home": {"teamId": 1},
            "away": {"teamId": 2},
            "winner": "UNDECIDED",
        }
    ]

    league.espn_request = MagicMock()
    league.espn_request.league_get.return_value = {"schedule": schedule}
    league._get_pro_schedule = MagicMock(return_value={})

    class FakeBoxScore:
        def __init__(self, data, pro_schedule, year, scoring_period):
            self.home_team = data["home"]["teamId"]
            self.away_team = data["away"]["teamId"]

    league._box_score_class = FakeBoxScore

    result = league.box_scores(matchup_period=2)

    call_kwargs = league.espn_request.league_get.call_args.kwargs
    assert call_kwargs["params"] == {
        "view": ["mMatchupScore", "mScoreboard"],
        "scoringPeriodId": 8,
    }
    filters = json.loads(call_kwargs["headers"]["x-fantasy-filter"])
    assert filters["schedule"]["filterMatchupPeriodIds"]["value"] == [2]

    assert result[0].home_team is team_a
    assert result[0].away_team is team_b


def test_box_scores_uses_scoring_period_when_provided():
    league = League(league_id=1, year=2025, fetch_league=False)
    league.currentMatchupPeriod = 3
    league.current_week = 8
    team_a = SimpleNamespace(team_id=1)
    team_b = SimpleNamespace(team_id=2)
    league.teams = [team_a, team_b]

    league.espn_request = MagicMock()
    league.espn_request.league_get.return_value = {
        "schedule": [
            {
                "home": {"teamId": 1},
                "away": {"teamId": 2},
                "winner": "UNDECIDED",
            }
        ]
    }
    league._get_pro_schedule = MagicMock(return_value={})

    class FakeBoxScore:
        def __init__(self, data, pro_schedule, year, scoring_period):
            self.home_team = data["home"]["teamId"]
            self.away_team = data["away"]["teamId"]

    league._box_score_class = FakeBoxScore

    league.box_scores(matchup_period=4, scoring_period=6)

    call_kwargs = league.espn_request.league_get.call_args.kwargs
    assert call_kwargs["params"]["scoringPeriodId"] == 6
    filters = json.loads(call_kwargs["headers"]["x-fantasy-filter"])
    assert filters["schedule"]["filterMatchupPeriodIds"]["value"] == [4]
