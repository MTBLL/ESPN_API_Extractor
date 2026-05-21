from espn_api_extractor.base.base_settings import BaseSettings


def test_games_started_limits_parsed():
    """Min, per-period cap, and per-matchup cap are derived from settings."""
    settings = BaseSettings(
        {
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
    )

    assert settings.games_started_min == 4
    assert settings.games_started_max_per_period == 1.4285714285714286
    assert settings.games_started_max_per_matchup == 10


def test_games_started_limits_absent():
    """Leagues without a games-started limit leave the fields as None."""
    settings = BaseSettings({})

    assert settings.games_started_min is None
    assert settings.games_started_max_per_period is None
    assert settings.games_started_max_per_matchup is None


def test_games_started_limits_ignore_other_stat_ids():
    """Limits keyed on a non-GS stat id are not picked up."""
    settings = BaseSettings(
        {
            "scoringSettings": {
                "statQualificationMinimum": {"limitValue": 30, "statId": 81},
            },
            "rosterSettings": {
                "lineupSlotStatLimits": {
                    "7": {"limitValue": 9, "statId": 81},
                },
            },
            "scheduleSettings": {"matchupPeriodLength": 7},
        }
    )

    assert settings.games_started_min is None
    assert settings.games_started_max_per_period is None
    assert settings.games_started_max_per_matchup is None
