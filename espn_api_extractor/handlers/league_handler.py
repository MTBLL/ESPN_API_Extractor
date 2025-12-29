from typing import List, Optional, Sequence

from pydantic import Json

from espn_api_extractor.baseball.league import League

DEFAULT_LEAGUE_VIEWS = ("mSettings", "mRoster", "mTeam", "modular", "mNav")


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
        return self.league.espn_request.get_league_data(self.views)
