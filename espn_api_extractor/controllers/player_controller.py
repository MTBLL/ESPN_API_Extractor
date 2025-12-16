from typing import Any, Dict, List

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.handlers.full_hydration_handler import FullHydrationHandler
from espn_api_extractor.handlers.pro_players_handler import ProPlayersHandler
from espn_api_extractor.handlers.update_player_handler import UpdatePlayerHandler
from espn_api_extractor.requests.constants import FantasySports
from espn_api_extractor.requests.fantasy_requests import EspnFantasyRequests
from espn_api_extractor.utils.logger import Logger


class PlayerController:
    """
    Strategic controller for player data extraction.

    Makes intelligent decisions about whether to do selective updates vs full hydration
    based on comparison of existing Hasura player IDs vs current ESPN players.

    Returns unified interface regardless of update vs new player source.
    """

    def __init__(self, args):
        self.league_id = args.league_id
        self.year = args.year
        self.threads = args.threads
        self.batch_size = args.batch_size
        self.logger = Logger("PlayerController").logging
        self.fantasy_requests = EspnFantasyRequests(
            league_id=self.league_id, sport=FantasySports.MLB, year=self.year
        )
        self.pro_players_handler = ProPlayersHandler(
            league_id=self.league_id, year=self.year
        )
        self.update_handler = UpdatePlayerHandler(
            league_id=self.league_id,
            year=self.year,
            threads=self.threads,
            batch_size=self.batch_size,
        )
        self.full_hydration_handler = FullHydrationHandler(
            league_id=self.league_id,
            year=self.year,
            threads=self.threads,
            batch_size=self.batch_size,
        )

    async def execute(self, existing_players: List[Player]) -> Dict[str, Any]:
        """
        Execute strategic player data extraction.

        Args:
            existing_players: List of Player objects currently in Hasura

        Returns:
            {
                "players": List[Player],  # Unified list of all current players
                "failures": List[str]     # Descriptive failure messages
            }
        """
        existing_player_ids = {player.id for player in existing_players}

        self.logger.info(
            f"Starting player extraction for {len(existing_player_ids)} existing players"
        )

        failures = []
        all_players = []

        try:
            # 1. Get all current ESPN players (single API call)
            self.logger.info("Fetching all current ESPN players")
            espn_players_response = self.fantasy_requests.get_pro_players()
            espn_player_ids = {player["id"] for player in espn_players_response}

            self.logger.info(f"Found {len(espn_player_ids)} current ESPN players")

            # 2. Strategic routing based on comparison
            existing_to_update = existing_player_ids.intersection(espn_player_ids)
            new_player_ids = espn_player_ids - existing_player_ids
            missing_from_espn = existing_player_ids - espn_player_ids

            self.logger.info(f"Players to update: {len(existing_to_update)}")
            self.logger.info(f"New players to fully hydrate: {len(new_player_ids)}")
            self.logger.info(
                f"Players in Hasura but not ESPN: {len(missing_from_espn)}"
            )

            # 3. Track players missing from ESPN
            for player_id in missing_from_espn:
                failures.append(
                    f"Player ID {player_id} in Hasura but not found in ESPN"
                )

            # 4. Process existing player updates first
            if existing_to_update:
                self.logger.info("Processing existing player updates")
                try:
                    updated_players = await self.update_handler.execute(
                        existing_to_update, pro_players_data=espn_players_response
                    )
                    all_players.extend(updated_players)
                    self.logger.info(
                        f"Successfully updated {len(updated_players)} existing players"
                    )
                except Exception as e:
                    error_msg = f"Failed to update existing players: {str(e)}"
                    self.logger.error(error_msg)
                    failures.append(error_msg)

            # 5. Process new players with full hydration
            if new_player_ids:
                self.logger.info("Processing new player hydration")
                try:
                    new_players = await self.full_hydration_handler.execute(
                        new_player_ids, pro_players_data=espn_players_response
                    )
                    all_players.extend(new_players)
                    self.logger.info(
                        f"Successfully hydrated {len(new_players)} new players"
                    )
                except Exception as e:
                    error_msg = f"Failed to hydrate new players: {str(e)}"
                    self.logger.error(error_msg)
                    failures.append(error_msg)

            self.logger.info(
                f"Extraction complete: {len(all_players)} total players, {len(failures)} failures"
            )

            return {"players": all_players, "failures": failures}

        except Exception as e:
            error_msg = f"Critical failure in player extraction: {str(e)}"
            self.logger.error(error_msg)
            return {"players": [], "failures": [error_msg]}
