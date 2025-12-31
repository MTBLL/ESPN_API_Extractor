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
