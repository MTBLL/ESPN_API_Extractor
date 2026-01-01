from types import SimpleNamespace

import pytest

from espn_api_extractor.baseball.league import League
from espn_api_extractor.requests.constants import FantasySports


class DummySettings:
    def __init__(self, data):
        self.data = data


class DummyTeam:
    def __init__(self, data, roster, schedule, year, owners=None, pro_schedule=None):
        self.team_id = data["id"]
        self.roster = roster
        self.schedule = schedule
        self.year = year
        self.owners = owners or []
        self.pro_schedule = pro_schedule
        self.division_id = data.get("divisionId", 0)
        self.final_standing = data.get("final", 0)
        self.standing = data.get("standing", 0)


def _make_league(**kwargs):
    base_class = League.__bases__[0]

    class DummyLeague(base_class):
        pass

    return DummyLeague(**kwargs)


def test_init_sets_requestor_cookies(monkeypatch):
    captured = {}

    def fake_requestor(sport, year, league_id, cookies):
        captured["sport"] = sport
        captured["year"] = year
        captured["league_id"] = league_id
        captured["cookies"] = cookies
        return SimpleNamespace()

    monkeypatch.setattr(
        "espn_api_extractor.base.base_league.EspnFantasyRequests", fake_requestor
    )

    league = _make_league(
        league_id=123,
        year=2025,
        sport=FantasySports.MLB,
        espn_s2="s2",
        swid="swid",
    )

    assert captured["sport"] == FantasySports.MLB
    assert captured["year"] == 2025
    assert captured["league_id"] == 123
    assert captured["cookies"] == {"espn_s2": "s2", "SWID": "swid"}
    assert league.settings is not None


def test_fetch_league_sets_current_week_for_pre_2018():
    league = _make_league(league_id=1, year=2017, sport=FantasySports.MLB)
    league.espn_request = SimpleNamespace(
        get_league=lambda: {
            "status": {
                "currentMatchupPeriod": 2,
                "firstScoringPeriod": 1,
                "finalScoringPeriod": 10,
                "previousSeasons": [2015, 2019],
            },
            "scoringPeriodId": 7,
            "settings": {"name": "Test"},
            "members": [],
        }
    )

    data = league._fetch_league(SettingsClass=DummySettings)

    assert data["scoringPeriodId"] == 7
    assert league.current_week == 7
    assert league.previousSeasons == [2015]
    assert isinstance(league.settings, DummySettings)


def test_fetch_league_caps_current_week():
    league = _make_league(league_id=1, year=2025, sport=FantasySports.MLB)
    league.espn_request = SimpleNamespace(
        get_league=lambda: {
            "status": {
                "currentMatchupPeriod": 2,
                "firstScoringPeriod": 1,
                "finalScoringPeriod": 10,
                "previousSeasons": [2024, 2026],
            },
            "scoringPeriodId": 12,
            "settings": {"name": "Test"},
            "members": [],
        }
    )

    league._fetch_league(SettingsClass=DummySettings)

    assert league.current_week == 10
    assert league.previousSeasons == [2024]


def test_fetch_draft_skips_when_not_drafted():
    league = _make_league(league_id=1, year=2025, sport=FantasySports.MLB)
    league.espn_request = SimpleNamespace(
        get_league_draft=lambda: {"draftDetail": {"drafted": False}}
    )

    league._fetch_draft()

    assert league.draft == []


def test_fetch_draft_builds_picks():
    league = _make_league(league_id=1, year=2025, sport=FantasySports.MLB)
    league.player_map = {10: "Player Ten"}
    league.teams = [SimpleNamespace(team_id=1), SimpleNamespace(team_id=2)]
    league.espn_request = SimpleNamespace(
        get_league_draft=lambda: {
            "draftDetail": {
                "drafted": True,
                "picks": [
                    {
                        "teamId": 1,
                        "playerId": 10,
                        "roundId": 2,
                        "roundPickNumber": 3,
                        "bidAmount": 15,
                        "keeper": False,
                        "nominatingTeamId": 2,
                    }
                ],
            }
        }
    )

    league._fetch_draft()

    assert len(league.draft) == 1
    pick = league.draft[0]
    assert pick.playerId == 10
    assert pick.playerName == "Player Ten"
    assert pick.round_num == 2
    assert pick.round_pick == 3
    assert pick.bid_amount == 15
    assert pick.nominatingTeam.team_id == 2


def test_fetch_teams_builds_sorted_team_list():
    league = _make_league(league_id=1, year=2025, sport=FantasySports.MLB)
    data = {
        "teams": [
            {"id": 2, "divisionId": 1, "owners": ["b"], "roster": {"entries": []}},
            {"id": 1, "divisionId": 2, "owners": ["a"], "roster": {"entries": []}},
        ],
        "schedule": [{"home": {"teamId": 1}, "away": {"teamId": 2}}],
        "seasonId": 2025,
        "members": [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}],
    }

    league._fetch_teams(data, TeamClass=DummyTeam)

    assert [team.team_id for team in league.teams] == [1, 2]
    assert league.teams[0].owners == [{"id": "a", "name": "A"}]
    assert league.teams[1].owners == [{"id": "b", "name": "B"}]


def test_fetch_players_maps_ids_and_names():
    league = _make_league(league_id=1, year=2025, sport=FantasySports.MLB)
    league.espn_request = SimpleNamespace(
        get_pro_players=lambda: [
            {"id": 10, "fullName": "Same Name"},
            {"id": 11, "fullName": "Same Name"},
        ]
    )

    league._fetch_players()

    assert league.player_map[10] == "Same Name"
    assert league.player_map["Same Name"] == 10
    assert 11 in league.player_map


def test_get_pro_schedule_builds_matchups():
    league = _make_league(league_id=1, year=2025, sport=FantasySports.MLB)
    league.espn_request = SimpleNamespace(
        get_pro_schedule=lambda: {
            "settings": {
                "proTeams": [
                    {
                        "id": 1,
                        "proGamesByScoringPeriod": {
                            "1": [
                                {
                                    "homeProTeamId": 1,
                                    "awayProTeamId": 2,
                                    "date": 123,
                                }
                            ]
                        },
                    },
                    {
                        "id": 2,
                        "proGamesByScoringPeriod": {
                            "1": [
                                {
                                    "homeProTeamId": 1,
                                    "awayProTeamId": 2,
                                    "date": 123,
                                }
                            ]
                        },
                    },
                ]
            }
        }
    )

    schedule = league._get_pro_schedule(scoringPeriodId=1)

    assert schedule == {1: (2, 123), 2: (1, 123)}


def test_get_all_pro_schedule_returns_all_periods():
    league = _make_league(league_id=1, year=2025, sport=FantasySports.MLB)
    league.espn_request = SimpleNamespace(
        get_pro_schedule=lambda: {
            "settings": {
                "proTeams": [
                    {"id": 1, "proGamesByScoringPeriod": {"1": [{"id": 1}]}},
                    {"id": 2, "proGamesByScoringPeriod": {"1": [{"id": 2}]}},
                ]
            }
        }
    )

    schedule = league._get_all_pro_schedule()

    assert schedule == {1: {"1": [{"id": 1}]}, 2: {"1": [{"id": 2}]}}


def test_standings_uses_final_when_present():
    league = _make_league(league_id=1, year=2025, sport=FantasySports.MLB)
    team_a = SimpleNamespace(final_standing=2, standing=1)
    team_b = SimpleNamespace(final_standing=0, standing=3)
    league.teams = [team_b, team_a]

    assert league.standings() == [team_a, team_b]


def test_get_team_data_returns_match():
    league = _make_league(league_id=1, year=2025, sport=FantasySports.MLB)
    team = SimpleNamespace(team_id=5)
    league.teams = [team]

    assert league.get_team_data(5) is team
    assert league.get_team_data(6) is None


def test_repr_includes_league_and_year():
    league = _make_league(league_id=123, year=2025, sport=FantasySports.MLB)

    assert repr(league) == "League(123, 2025)"
