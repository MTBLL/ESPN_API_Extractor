from pydantic import Json

from espn_api_extractor.requests import EspnFantasyRequests
from espn_api_extractor.runners import CoreRunner


class ProPlayersHandler:
    def __init__(self, runner: CoreRunner, league_id: int = None):
        self.runner = runner
        self.league_id = league_id
        # Get ESPN player universe
        self.fantasy_requestor = EspnFantasyRequests(
            sport="mlb",
            year=runner.year,
            league_id=league_id,
            cookies={},
            logger=runner.logger,
        )

    def fetch(self) -> Json:
        return self.fantasy_requestor.get_pro_players()
