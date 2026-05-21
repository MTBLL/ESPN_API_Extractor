from .constants import GAMES_STARTED_STAT_ID


class Matchup(object):
    """Creates Matchup instance"""

    def __init__(self, data):
        self.home_team_live_score = 0
        self.away_team_live_score = 0
        self.home_games_started = None
        self.away_games_started = None
        self.home_games_started_limit_exceeded = None
        self.away_games_started_limit_exceeded = None
        self._fetch_matchup_info(data)

    def __repr__(self):
        # TODO: use final score when that's available?
        # writing this too early to see if data['home']['totalPoints'] is final score
        # it might also be used for points leagues instead of category leagues
        if not self.away_team_live_score:
            return "Matchup(%s, %s)" % (
                self.home_team,
                self.away_team,
            )
        else:
            return "Matchup(%s %s - %s %s)" % (
                self.home_team,
                str(round(self.home_team_live_score, 1)),
                str(round(self.away_team_live_score, 1)),
                self.away_team,
            )

    def _fetch_matchup_info(self, data):
        """Fetch info for matchup"""
        self.home_team = data["home"]["teamId"]
        self.home_final_score = data["home"]["totalPoints"]
        self.away_team = data["away"]["teamId"]
        self.away_final_score = data["away"]["totalPoints"]
        self.winner = data["winner"]

        # if stats are available
        if (
            "cumulativeScore" in data["home"].keys()
            and data["home"]["cumulativeScore"].get("scoreByStat")
        ):
            self.home_team_live_score = (
                data["home"]["cumulativeScore"]["wins"]
                + data["home"]["cumulativeScore"]["ties"] / 2
            )
            self.away_team_live_score = (
                data["away"]["cumulativeScore"]["wins"]
                + data["away"]["cumulativeScore"]["ties"] / 2
            )

        # Pitcher games started for each side, when ESPN reports it.
        (
            self.home_games_started,
            self.home_games_started_limit_exceeded,
        ) = self._fetch_games_started(data.get("home"))
        (
            self.away_games_started,
            self.away_games_started_limit_exceeded,
        ) = self._fetch_games_started(data.get("away"))

    @staticmethod
    def _fetch_games_started(side_data):
        """Pitcher games started for one side of the matchup.

        ESPN tracks the games-started count under cumulativeScore.statBySlot,
        keyed by a virtual lineup slot; the entry whose statId is GS carries
        the running count (the "Cur" in ESPN's box-score game-limits line)
        and a flag for whether the cap was exceeded. Returns (None, None)
        when no games-started entry is present.
        """
        if not isinstance(side_data, dict):
            return (None, None)
        cumulative_score = side_data.get("cumulativeScore")
        if not isinstance(cumulative_score, dict):
            return (None, None)
        stat_by_slot = cumulative_score.get("statBySlot")
        if not isinstance(stat_by_slot, dict):
            return (None, None)
        for slot_entry in stat_by_slot.values():
            if (
                isinstance(slot_entry, dict)
                and slot_entry.get("statId") == GAMES_STARTED_STAT_ID
            ):
                return (
                    slot_entry.get("value"),
                    slot_entry.get("limitExceeded"),
                )
        return (None, None)
