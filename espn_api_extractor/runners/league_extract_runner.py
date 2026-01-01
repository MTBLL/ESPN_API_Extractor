#!/usr/bin/env python3
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from espn_api_extractor.controllers import LeagueController
from espn_api_extractor.utils.logger import Logger


class LeagueExtractRunner:
    def __init__(self, args):
        self.args = args
        self.logger = Logger("LeagueExtractRunner").logging
        self.controller = LeagueController(args)

    async def run(self) -> Optional[Dict[str, Any]]:
        """
        EXTRACTION PHASE ONLY - Extract league data from ESPN and save to local JSON.
        """
        self.logger.info(
            f"Starting league extraction for league {self.args.league_id} year {self.args.year}"
        )
        self.logger.info(f"Output directory: {self.args.output_dir}")

        try:
            results = await self.controller.execute()
            league_data = results["league"]
            failures = results["failures"]

            if league_data is not None:
                self._save_extraction_results(league_data, failures)

            return league_data
        except Exception as e:
            self.logger.error(f"League extraction failed: {e}")
            raise

    def _save_extraction_results(
        self, league_data: Dict[str, Any], failures: list[str]
    ) -> None:
        os.makedirs(self.args.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        league_file = os.path.join(
            self.args.output_dir,
            f"espn_league_{self.args.league_id}_{self.args.year}_{timestamp}.json",
        )

        with open(league_file, "w") as f:
            json.dump(league_data, f, indent=2)

        self.logger.info(f"Saved league data to {league_file}")

        if failures:
            failures_file = os.path.join(
                self.args.output_dir,
                f"league_failures_{self.args.league_id}_{self.args.year}_{timestamp}.json",
            )
            with open(failures_file, "w") as f:
                json.dump({"failures": failures, "count": len(failures)}, f, indent=2)

            self.logger.warning(f"Saved {len(failures)} failures to {failures_file}")
