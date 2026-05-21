# ESPN stat id for pitcher games started; the games-started limits are
# keyed on it. Defined locally to keep the base layer sport-agnostic.
_GAMES_STARTED_STAT_ID = 33


class BaseSettings(object):
    """Creates Settings object"""

    def __init__(self, data):
        schedule_settings = data.get("scheduleSettings", {})
        trade_settings = data.get("tradeSettings", {})
        draft_settings = data.get("draftSettings", {})
        scoring_settings = data.get("scoringSettings", {})
        acquisition_settings = data.get("acquisitionSettings", {})
        roster_settings = data.get("rosterSettings", {})

        self.reg_season_count = schedule_settings.get("matchupPeriodCount", 0)
        self.matchup_periods = schedule_settings.get("matchupPeriods", {})
        self.veto_votes_required = trade_settings.get("vetoVotesRequired", 0)
        self.team_count = data.get("size", 0)
        self.playoff_team_count = schedule_settings.get("playoffTeamCount", 0)
        self.keeper_count = draft_settings.get("keeperCount", 0)
        self.trade_deadline = 0
        self.division_map = {}
        if "deadlineDate" in trade_settings:
            self.trade_deadline = trade_settings["deadlineDate"]
        self.name = data.get("name", "")
        self.tie_rule = scoring_settings.get("matchupTieRule", 0)
        self.playoff_tie_rule = scoring_settings.get("playoffMatchupTieRule", 0)
        self.playoff_matchup_period_length = schedule_settings.get(
            "playoffMatchupPeriodLength", 0
        )
        self.playoff_seed_tie_rule = schedule_settings.get("playoffSeedingRule", 0)
        self.scoring_type = scoring_settings.get("scoringType")
        self.faab = acquisition_settings.get("isUsingAcquisitionBudget", False)
        self.acquisition_budget = acquisition_settings.get("acquisitionBudget", 0)
        divisions = schedule_settings.get("divisions", [])
        for division in divisions:
            self.division_map[division.get("id", 0)] = division.get("name")

        # Pitcher games-started limits (MLB H2H). ESPN splits these across two
        # settings sections: statQualificationMinimum is the minimum games
        # started needed to qualify for the pitching categories (miss it and
        # they are forfeited); lineupSlotStatLimits is the per-scoring-period
        # cap, scaled by matchupPeriodLength for the per-matchup cap. All None
        # for leagues/sports without a games-started limit.
        self.games_started_min = None
        self.games_started_max_per_period = None
        self.games_started_max_per_matchup = None

        qualification = scoring_settings.get("statQualificationMinimum")
        if (
            isinstance(qualification, dict)
            and qualification.get("statId") == _GAMES_STARTED_STAT_ID
        ):
            self.games_started_min = qualification.get("limitValue")

        slot_limits = roster_settings.get("lineupSlotStatLimits")
        if isinstance(slot_limits, dict):
            for limit in slot_limits.values():
                if (
                    isinstance(limit, dict)
                    and limit.get("statId") == _GAMES_STARTED_STAT_ID
                ):
                    self.games_started_max_per_period = limit.get("limitValue")
                    break

        period_length = schedule_settings.get("matchupPeriodLength")
        if self.games_started_max_per_period is not None and isinstance(
            period_length, (int, float)
        ) and period_length:
            self.games_started_max_per_matchup = round(
                self.games_started_max_per_period * period_length
            )

    def __repr__(self):
        return f"Settings({self.name})"
