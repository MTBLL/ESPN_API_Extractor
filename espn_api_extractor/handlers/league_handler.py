from typing import List, Optional, Sequence

from pydantic import Json

from espn_api_extractor.baseball.league import League

DEFAULT_LEAGUE_VIEWS = ("mSettings", "mRoster", "mTeam", "modular", "mNav")
EXCLUDED_LEAGUE_KEYS = {"draftDetail", "gameId", "members", "segmentId"}
EXCLUDED_SETTINGS_KEYS = {
    "financeSettings",
    "isAutoReactivated",
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
        self.views: List[str] = list(views) if views else list(DEFAULT_LEAGUE_VIEWS)

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
        data = self.league.espn_request.get_league_data(self.views)
        assert isinstance(data, dict)

        filtered = {
            key: value for key, value in data.items() if key not in EXCLUDED_LEAGUE_KEYS
        }
        settings = filtered.get("settings")
        if isinstance(settings, dict):
            settings = {
                key: value
                for key, value in settings.items()
                if key not in EXCLUDED_SETTINGS_KEYS
            }
            acquisition_settings = settings.get("acquisitionSettings")
            if isinstance(acquisition_settings, dict):
                settings["acquisitionSettings"] = {
                    key: value
                    for key, value in acquisition_settings.items()
                    if key in ACQUISITION_SETTINGS_KEEP
                }
            filtered["settings"] = settings

        return filtered
