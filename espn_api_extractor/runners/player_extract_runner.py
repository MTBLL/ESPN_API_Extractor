#!/usr/bin/env python3
import copy
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Union

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.controllers import PlayerController
from espn_api_extractor.handlers.player_extract_handler import PlayerExtractHandler
from espn_api_extractor.models import PlayerModel
from espn_api_extractor.utils.graphql_client import GraphQLClient
from espn_api_extractor.utils.logger import Logger


class PlayerExtractRunner:
    def __init__(self, args):
        self.args = args
        self.logger = Logger("PlayerExtractRunner").logging

        # Pass args to controller (controller unwraps and passes to handlers)
        self.controller = PlayerController(args)
        self.handler = PlayerExtractHandler()

        # Initialize GraphQL client for reading existing players (optimization)
        self.graphql_client = GraphQLClient(
            config_path=args.graphql_config
        ).initialize_with_hitl(force_full_extraction=args.force_full_extraction)

    async def run(self) -> Union[List[Player], List[PlayerModel]]:
        """
        EXTRACTION PHASE ONLY - Extract player data from ESPN and save to local JSON.

        This is the "E" in ETL:
        - Extract data from ESPN APIs
        - Save raw extracted data to JSON files
        - Transformation and Load happen in separate pipeline stages

        GraphQL optimization:
        - Reads existing players from GraphQL to optimize API calls
        - Does NOT write to GraphQL (that's the Load phase in a separate app)
        """
        self.logger.info(f"Starting player extraction for year {self.args.year}")
        self.logger.info(f"Output directory: {self.args.output_dir}")

        try:
            # Step 1: Get existing players from GraphQL for optimization (read-only)
            existing_players: List[Player] = []
            if self.graphql_client.is_available:
                self.logger.info(
                    "Fetching existing players from GraphQL (optimization)"
                )
                player_models: List[PlayerModel] = (
                    self.graphql_client.get_existing_players()
                )
                existing_players = [
                    Player.from_model(model, current_season=self.args.year)
                    for model in player_models
                ]
                self.logger.info(f"Found {len(existing_players)} existing players")
            else:
                self.logger.info("GraphQL not available - performing full extraction")

            # Step 2: Execute extraction via controller
            results: Dict[str, Any] = await self.controller.execute(existing_players)
            players: List[Player] = results["players"]
            pitchers: List[Player] = results["pitchers"]
            batters: List[Player] = results["batters"]
            failures: List[str] = results["failures"]

            self.logger.info(
                f"Extraction complete: {len(players)} players, {len(failures)} failures"
            )

            # Step 3: Save extracted data to JSON (for next ETL stage)
            self._save_extraction_results(pitchers, batters, failures)

            # Step 4: Return players (convert to models if requested)
            if self.args.as_models:
                return [player.to_model() for player in players]
            else:
                return players

        except Exception as e:
            self.logger.error(f"Player extraction failed: {e}")
            raise

    def _save_extraction_results(
        self, pitchers: List[Player], batters: List[Player], failures: List[str]
    ) -> None:
        """
        Save extracted data to JSON files for next ETL pipeline stage.

        Args:
            players: List of successfully extracted Player objects
            failures: List of failure messages
        """
        os.makedirs(self.args.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        pitchers = self._sort_players(pitchers)
        batters = self._sort_players(batters)

        pitchers_file = os.path.join(
            self.args.output_dir, f"espn_pitchers_{self.args.year}_{timestamp}.json"
        )
        batters_file = os.path.join(
            self.args.output_dir, f"espn_batters_{self.args.year}_{timestamp}.json"
        )

        pitchers_data = []
        for player in pitchers:
            data = copy.deepcopy(player.to_model().model_dump())
            self.handler.apply_pitcher_transforms(player, data)
            pitchers_data.append(data)
        batters_data = [player.to_model().model_dump() for player in batters]

        with open(pitchers_file, "w") as f:
            json.dump(pitchers_data, f, indent=2)
        with open(batters_file, "w") as f:
            json.dump(batters_data, f, indent=2)

        self.logger.info(f"Saved {len(pitchers)} pitchers to {pitchers_file}")
        self.logger.info(f"Saved {len(batters)} batters to {batters_file}")

        # Save failures if any
        if failures:
            failures_file = os.path.join(
                self.args.output_dir, f"failures_{self.args.year}_{timestamp}.json"
            )
            with open(failures_file, "w") as f:
                json.dump({"failures": failures, "count": len(failures)}, f, indent=2)

            self.logger.warning(f"Saved {len(failures)} failures to {failures_file}")

    def _sort_players(self, players: List[Player]) -> List[Player]:
        return sorted(
            players,
            key=lambda p: p.percent_owned if p.percent_owned > 0 else -1,
            reverse=True,
        )
