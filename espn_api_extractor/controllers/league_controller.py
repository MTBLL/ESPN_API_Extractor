from typing import Any, Dict, Optional

from espn_api_extractor.handlers.league_handler import LeagueHandler
from espn_api_extractor.utils.logger import Logger


class LeagueController:
    def __init__(self, args):
        self.league_id = args.league_id
        self.year = args.year
        self.views = getattr(args, "views", None)
        self.espn_s2 = getattr(args, "espn_s2", None)
        self.swid = getattr(args, "swid", None)
        self.logger = Logger("LeagueController").logging
        self.league_handler = LeagueHandler(
            league_id=self.league_id,
            year=self.year,
            espn_s2=self.espn_s2,
            swid=self.swid,
            views=self.views,
        )

    async def execute(self) -> Dict[str, Any]:
        self.logger.info(
            f"Fetching league data for league {self.league_id} year {self.year}"
        )

        try:
            league_data: Optional[dict] = self.league_handler.fetch()
            return {"league": league_data, "failures": []}
        except Exception as e:
            error_msg = f"League extraction failed: {str(e)}"
            self.logger.error(error_msg)
            return {"league": None, "failures": [error_msg]}
