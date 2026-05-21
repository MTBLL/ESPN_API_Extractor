from espn_api_extractor.baseball.matchup import Matchup


def _side(team_id, games_started=None, limit_exceeded=False):
    side = {"teamId": team_id, "totalPoints": 0}
    if games_started is not None:
        side["cumulativeScore"] = {
            "wins": 0,
            "ties": 0,
            "statBySlot": {
                "22": {
                    "statId": 33,
                    "value": games_started,
                    "limitExceeded": limit_exceeded,
                }
            },
        }
    return side


def test_matchup_parses_games_started():
    """Pitcher games started + cap flag are read from cumulativeScore."""
    matchup = Matchup(
        {
            "home": _side(1, games_started=5),
            "away": _side(2, games_started=2, limit_exceeded=True),
            "winner": "UNDECIDED",
        }
    )

    assert matchup.home_games_started == 5
    assert matchup.away_games_started == 2
    assert matchup.home_games_started_limit_exceeded is False
    assert matchup.away_games_started_limit_exceeded is True


def test_matchup_games_started_absent():
    """Matchups without statBySlot leave games-started fields as None."""
    matchup = Matchup(
        {
            "home": _side(1),
            "away": _side(2),
            "winner": "UNDECIDED",
        }
    )

    assert matchup.home_games_started is None
    assert matchup.away_games_started is None
    assert matchup.home_games_started_limit_exceeded is None
    assert matchup.away_games_started_limit_exceeded is None
    assert repr(matchup) == "Matchup(1, 2)"


def test_fetch_games_started_handles_malformed_input():
    """Malformed side shapes return (None, None) instead of raising."""
    # Non-dict side data
    assert Matchup._fetch_games_started(None) == (None, None)
    # Non-dict cumulativeScore
    assert Matchup._fetch_games_started({"cumulativeScore": "bad"}) == (None, None)
    # Non-dict statBySlot
    assert Matchup._fetch_games_started(
        {"cumulativeScore": {"statBySlot": "bad"}}
    ) == (None, None)
    # statBySlot present but no games-started (statId 33) entry
    assert Matchup._fetch_games_started(
        {"cumulativeScore": {"statBySlot": {"7": {"statId": 81, "value": 9}}}}
    ) == (None, None)


def test_matchup_handles_cumulative_score_without_score_by_stat():
    """cumulativeScore lacking scoreByStat (bye/early season) is not fatal."""
    matchup = Matchup(
        {
            "home": _side(1, games_started=3),
            "away": _side(2, games_started=1),
            "winner": "UNDECIDED",
        }
    )

    assert matchup.home_team_live_score == 0
    assert matchup.home_games_started == 3


def test_matchup_live_score_from_cumulative_score():
    """Live score is wins + ties/2 when scoreByStat is present."""
    matchup = Matchup(
        {
            "home": {
                "teamId": 1,
                "totalPoints": 0,
                "cumulativeScore": {
                    "wins": 3,
                    "ties": 2,
                    "scoreByStat": {"20": {"score": 5, "result": "WIN"}},
                },
            },
            "away": {
                "teamId": 2,
                "totalPoints": 0,
                "cumulativeScore": {
                    "wins": 1,
                    "ties": 2,
                    "scoreByStat": {"20": {"score": 3, "result": "LOSS"}},
                },
            },
            "winner": "HOME",
        }
    )

    assert matchup.home_team_live_score == 3 + 2 / 2
    assert matchup.away_team_live_score == 1 + 2 / 2
    assert repr(matchup) == "Matchup(1 4.0 - 2.0 2)"
