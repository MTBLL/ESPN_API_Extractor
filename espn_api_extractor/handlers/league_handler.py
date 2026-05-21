from typing import Any, Optional, Sequence

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
        filtered = self._filter_team_rosters(filtered)
        return filtered

    def _drop_excluded_keys(self, data: dict) -> dict:
        return {
            key: value for key, value in data.items() if key not in EXCLUDED_LEAGUE_KEYS
        }

    def _filter_settings(self, data: dict) -> dict:
        settings = data.get("settings")
        if not isinstance(settings, dict):
            return data

        settings = self._drop_settings_keys(settings)
        settings = self._filter_acquisition_settings(settings)
        settings = self._filter_scoring_settings(settings)

        updated = dict(data)
        updated["settings"] = settings
        return updated

    def _drop_settings_keys(self, settings: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in settings.items()
            if key not in EXCLUDED_SETTINGS_KEYS
        }

    def _filter_acquisition_settings(self, settings: dict) -> dict:
        acquisition_settings = settings.get("acquisitionSettings")
        if not isinstance(acquisition_settings, dict):
            return settings

        updated = dict(settings)
        updated["acquisitionSettings"] = {
            key: value
            for key, value in acquisition_settings.items()
            if key in ACQUISITION_SETTINGS_KEEP
        }
        return updated

    def _filter_scoring_settings(self, settings: dict) -> dict:
        scoring_settings = settings.get("scoringSettings")
        if not isinstance(scoring_settings, dict):
            return settings

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
        categories: dict[str, list[dict[str, Any]]] = {"batting": [], "pitching": []}
        for item in scoring_items:
            stat_id = item.get("statId")
            entry = {
                "statId": stat_id,
                "name": STATS_MAP.get(stat_id) if isinstance(stat_id, int) else None,
                "isReverseItem": item.get("isReverseItem"),
            }
            if isinstance(stat_id, int) and stat_id >= 32:
                categories["pitching"].append(entry)
            else:
                categories["batting"].append(entry)
        return categories

    def _filter_status(self, data: dict) -> dict:
        status = data.get("status")
        if not isinstance(status, dict):
            return data

        updated = dict(data)
        updated_status = dict(status)
        updated_status.pop("waiverProcessStatus", None)
        updated["status"] = updated_status
        return updated

    def _filter_team_rosters(self, data: dict) -> dict:
        teams = data.get("teams")
        if not isinstance(teams, list):
            return data

        updated_teams = []
        for team in teams:
            roster = team.get("roster")
            if not isinstance(roster, dict):
                updated_teams.append(team)
                continue

            entries = roster.get("entries")
            if not isinstance(entries, list):
                updated_teams.append(team)
                continue

            updated_entries = [
                self._drop_roster_entry_stats(entry) for entry in entries
            ]
            updated_roster = dict(roster)
            updated_roster["entries"] = updated_entries

            updated_team = dict(team)
            updated_team["roster"] = updated_roster
            updated_teams.append(updated_team)

        updated = dict(data)
        updated["teams"] = updated_teams
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

        simplified = {
            "id": matchup.get("id"),
            "matchupPeriodId": matchup.get("matchupPeriodId"),
            "playoffTierType": matchup.get("playoffTierType"),
            "winner": winner,
            "teams": teams,
        }

        # Preserve per-category breakdown for H2H category leagues. Only
        # present when ESPN returns scoreByStat (category leagues); points and
        # roster-limit leagues have no scoreByStat and the key is omitted.
        category_results = {}
        if home_team_id is not None:
            home_categories = self._format_category_results(
                home.get("cumulativeScore")
            )
            if home_categories:
                category_results[home_team_id] = home_categories
        if away_team_id is not None:
            away_categories = self._format_category_results(
                away.get("cumulativeScore")
            )
            if away_categories:
                category_results[away_team_id] = away_categories
        if category_results:
            simplified["categoryResults"] = category_results

        return simplified

    def _format_record(self, cumulative_score: Optional[dict]) -> str:
        if not isinstance(cumulative_score, dict):
            return "0-0-0"
        wins = cumulative_score.get("wins", 0)
        losses = cumulative_score.get("losses", 0)
        ties = cumulative_score.get("ties", 0)
        return f"{wins}-{losses}-{ties}"

    def _format_category_results(
        self, cumulative_score: Optional[dict]
    ) -> Optional[dict]:
        """Map ESPN scoreByStat to {category_name: {value, result}}.

        Returns None when no category data is present (non-category leagues),
        so callers can omit the field entirely.
        """
        if not isinstance(cumulative_score, dict):
            return None
        score_by_stat = cumulative_score.get("scoreByStat")
        if not isinstance(score_by_stat, dict) or not score_by_stat:
            return None

        results = {}
        for stat_key, stat_dict in score_by_stat.items():
            if not isinstance(stat_dict, dict):
                continue
            # Only scored categories carry a WIN/LOSS/TIE result. ESPN also
            # returns component stats (AB, H, ER, ...) with result=None; skip
            # those so the breakdown matches the matchup's category line.
            if stat_dict.get("result") is None:
                continue
            try:
                stat_id = int(stat_key)
            except (TypeError, ValueError):
                continue
            category = STATS_MAP.get(stat_id, f"STAT_{stat_id}")
            results[category] = {
                "value": stat_dict.get("score"),
                "result": stat_dict.get("result"),
            }
        return results or None

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

    def _drop_roster_entry_stats(self, entry: dict) -> dict:
        updated_entry = dict(entry)

        player_pool_entry = entry.get("playerPoolEntry")
        if isinstance(player_pool_entry, dict):
            updated_ppe = dict(player_pool_entry)
            updated_ppe.pop("ratings", None)
            player = player_pool_entry.get("player")
            if isinstance(player, dict):
                updated_player = dict(player)
                updated_player.pop("stats", None)
                updated_player.pop("draftRanksByRankType", None)
                updated_ppe["player"] = updated_player
            updated_entry["playerPoolEntry"] = updated_ppe

        player = entry.get("player")
        if isinstance(player, dict):
            updated_player = dict(player)
            updated_player.pop("stats", None)
            updated_player.pop("draftRanksByRankType", None)
            updated_entry["player"] = updated_player

        return updated_entry
