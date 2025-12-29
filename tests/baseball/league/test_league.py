from types import SimpleNamespace
from unittest.mock import MagicMock

from espn_api_extractor.baseball.league import League
from espn_api_extractor.baseball.team import Team


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


def test_fetch_teams_maps_opponents_to_team_instances(league_response_fixture):
    league = League(league_id=1, year=2025, fetch_league=False)
    data = league_response_fixture
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
