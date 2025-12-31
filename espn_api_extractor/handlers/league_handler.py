from typing import Optional, Sequence

from pydantic import Json

from espn_api_extractor.baseball.constants import STATS_MAP
from espn_api_extractor.baseball.league import League

EXCLUDED_LEAGUE_KEYS = {"draftDetail", "gameId", "members", "segmentId"}
EXCLUDED_SETTINGS_KEYS = {
    "financeSettings",
    "isAutoReactivated",
    "isAutoReactivate",
    "isCustomizable",
    "restrictionType",
}
ACQUISITION_SETTINGS_KEEP = {"acquisitionBudget"}


class LeagueHandler:
    def __init__(
        self,
        year: int,
        league_id: int,
        espn_s2: Optional[str] = None,
        swid: Optional[str] = None,
        views: Optional[Sequence[str]] = None,
        league: Optional[League] = None,
    ):
        self.views = views
        if league is not None:
            self.league = league
            return

        self.league = League(
            year=year,
            league_id=league_id,
            espn_s2=espn_s2,
            swid=swid,
            fetch_league=False,
        )

    def fetch(self) -> Json:
        data = self.league.espn_request.get_league()

        filtered = self._drop_excluded_keys(data)
        filtered = self._filter_settings(filtered)
        filtered = self._filter_status(filtered)
        filtered = self._filter_schedule(filtered)
        return filtered

    def _drop_excluded_keys(self, data: dict) -> dict:
        return {
            key: value for key, value in data.items() if key not in EXCLUDED_LEAGUE_KEYS
        }

    def _filter_settings(self, data: dict) -> dict:
        settings = data.get("settings")

        settings = self._drop_settings_keys(settings)
        settings = self._filter_acquisition_settings(settings)
        settings = self._filter_scoring_settings(settings)

        updated = dict(data)
        updated["settings"] = settings
        return updated

    def _drop_settings_keys(self, settings: dict) -> dict:
        return {
            key: value
            for key, value in settings.items()
            if key not in EXCLUDED_SETTINGS_KEYS
        }

    def _filter_acquisition_settings(self, settings: dict) -> dict:
        acquisition_settings = settings.get("acquisitionSettings")
        assert isinstance(acquisition_settings, dict)

        updated = dict(settings)
        updated["acquisitionSettings"] = {
            key: value
            for key, value in acquisition_settings.items()
            if key in ACQUISITION_SETTINGS_KEEP
        }
        return updated

    def _filter_scoring_settings(self, settings: dict) -> dict:
        scoring_settings = settings.get("scoringSettings")
        assert isinstance(scoring_settings, dict)

        scoring_settings = dict(scoring_settings)
        scoring_items = scoring_settings.pop("scoringItems", None)
        if isinstance(scoring_items, list):
            scoring_settings["categories"] = self._build_scoring_categories(
                scoring_items
            )

        updated = dict(settings)
        updated["scoringSettings"] = scoring_settings
        return updated

    def _build_scoring_categories(self, scoring_items: list[dict]) -> dict:
        categories = {"batting": [], "pitching": []}
        for item in scoring_items:
            stat_id = item.get("statId")
            entry = {
                "statId": stat_id,
                "name": STATS_MAP.get(stat_id),
                "isReverseItem": item.get("isReverseItem"),
            }
            if isinstance(stat_id, int) and stat_id >= 32:
                categories["pitching"].append(entry)
            else:
                categories["batting"].append(entry)
        return categories

    def _filter_status(self, data: dict) -> dict:
        status = data.get("status")
        assert isinstance(status, dict)

        updated = dict(data)
        updated_status = dict(status)
        updated_status.pop("waiverProcessStatus", None)
        updated["status"] = updated_status
        return updated

    def _filter_schedule(self, data: dict) -> dict:
        schedule = data.get("schedule")
        if not isinstance(schedule, list):
            return data

        updated = dict(data)
        updated["schedule"] = [self._simplify_matchup(matchup) for matchup in schedule]
        return updated

    def _simplify_matchup(self, matchup: dict) -> dict:
        home = matchup.get("home") or {}
        away = matchup.get("away") or {}

        home_team_id = home.get("teamId")
        away_team_id = away.get("teamId")

        teams = {}
        if home_team_id is not None:
            teams[home_team_id] = self._format_record(home.get("cumulativeScore"))
        if away_team_id is not None:
            teams[away_team_id] = self._format_record(away.get("cumulativeScore"))

        winner = self._normalize_winner(
            matchup.get("winner"),
            home_team_id,
            away_team_id,
            len(teams),
        )

        return {
            "id": matchup.get("id"),
            "matchupPeriodId": matchup.get("matchupPeriodId"),
            "playoffTierType": matchup.get("playoffTierType"),
            "winner": winner,
            "teams": teams,
        }

    def _format_record(self, cumulative_score: Optional[dict]) -> str:
        if not isinstance(cumulative_score, dict):
            cumulative_score = {}
        wins = cumulative_score.get("wins", 0)
        losses = cumulative_score.get("losses", 0)
        ties = cumulative_score.get("ties", 0)
        return f"{wins}-{losses}-{ties}"

    def _normalize_winner(
        self,
        winner: Optional[str],
        home_team_id: Optional[int],
        away_team_id: Optional[int],
        team_count: int,
    ) -> Optional[int | str]:
        if team_count == 1 and winner in (None, "UNDECIDED"):
            return "BYE WEEK"
        if winner == "HOME":
            return home_team_id
        if winner == "AWAY":
            return away_team_id
        if winner == "TIE":
            return "TIE"
        return None
