from pydantic import Json

from espn_api_extractor.requests import EspnFantasyRequests
from espn_api_extractor.requests.constants import FantasySports


class ProPlayersHandler:
    def __init__(self, year: int, league_id: int = None):
        self.league_id = league_id
        # Get ESPN player universe
        self.fantasy_requestor = EspnFantasyRequests(
            sport=FantasySports.MLB,
            year=year,
            league_id=league_id,
            cookies={},
        )

    def fetch(self) -> Json:
        return self.fantasy_requestor.get_pro_players()
