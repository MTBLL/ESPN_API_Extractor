from typing import List, Optional, Sequence

from pydantic import Json

from espn_api_extractor.requests import EspnFantasyRequests
from espn_api_extractor.requests.constants import FantasySports

DEFAULT_LEAGUE_VIEWS = ("mSettings", "mRoster", "mTeam", "modular", "mNav")


class LeagueHandler:
    def __init__(
        self,
        year: int,
        league_id: int,
        espn_s2: Optional[str] = None,
        swid: Optional[str] = None,
        views: Optional[Sequence[str]] = None,
        requestor: Optional[EspnFantasyRequests] = None,
    ):
        self.league_id = league_id
        self.views: List[str] = list(views) if views else list(DEFAULT_LEAGUE_VIEWS)

        if requestor is not None:
            self.fantasy_requestor = requestor
            return

        cookies = {}
        if espn_s2 and swid:
            cookies = {"espn_s2": espn_s2, "SWID": swid}

        self.fantasy_requestor = EspnFantasyRequests(
            sport=FantasySports.MLB,
            year=year,
            league_id=league_id,
            cookies=cookies,
        )

    def fetch(self) -> Json:
        return self.fantasy_requestor.get_league_data(self.views)
