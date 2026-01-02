from typing import Any, Dict, List

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.handlers.full_hydration_handler import FullHydrationHandler
from espn_api_extractor.handlers.player_extract_handler import PlayerExtractHandler
from espn_api_extractor.handlers.update_player_handler import UpdatePlayerHandler
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
        self.sample_size = args.sample_size
        self.logger = Logger("PlayerController").logging

        self.extract_handler = PlayerExtractHandler(
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
            espn_player_cards = self.extract_handler.fetch_player_cards()
            espn_player_id_list = [
                player.get("id") or player.get("player", {}).get("id")
                for player in espn_player_cards
                if isinstance(player, dict)
            ]
            espn_player_id_list = [
                player_id for player_id in espn_player_id_list if player_id is not None
            ]
            espn_player_ids = set(espn_player_id_list)
            pro_players_data = [
                player for player in espn_player_cards if isinstance(player, dict)
            ]

            self.logger.info(f"Found {len(espn_player_ids)} current ESPN players")

            # 2. Strategic routing based on comparison
            existing_to_update = existing_player_ids.intersection(espn_player_ids)
            new_player_id_list = [
                player_id
                for player_id in espn_player_id_list
                if player_id not in existing_player_ids
            ]
            new_player_ids = set(new_player_id_list)
            missing_from_espn = existing_player_ids - espn_player_ids

            # Apply sample_size limit if specified
            if self.sample_size is not None:
                self.logger.info(
                    f"Limiting to sample_size of {self.sample_size} players"
                )
                # Limit new players to sample size
                new_player_id_list = new_player_id_list[: self.sample_size]
                new_player_ids = set(new_player_id_list)
                # Don't update existing players if we're sampling
                existing_to_update = set()

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
                existing_players_map = {
                    player.id: player
                    for player in existing_players
                    if player.id is not None
                }
                players_to_update = [
                    existing_players_map[player_id]
                    for player_id in existing_to_update
                    if player_id in existing_players_map
                ]
                try:
                    updated_players = await self.update_handler.execute(
                        players_to_update, pro_players_data=pro_players_data
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
                        new_player_ids, pro_players_data=pro_players_data
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

            pitchers, batters = self._split_players_by_role(all_players)

            return {
                "players": all_players,
                "pitchers": pitchers,
                "batters": batters,
                "failures": failures,
            }

        except Exception as e:
            error_msg = f"Critical failure in player extraction: {str(e)}"
            self.logger.error(error_msg)
            return {"players": [], "pitchers": [], "batters": [], "failures": [error_msg]}

    def _split_players_by_role(
        self, players: List[Player]
    ) -> tuple[List[Player], List[Player]]:
        pitchers: List[Player] = []
        batters: List[Player] = []

        for player in players:
            has_pitcher_slot, has_non_pitcher_slot = (
                self.extract_handler.get_slot_flags(player)
            )

            if has_pitcher_slot:
                pitchers.append(player)
            if has_non_pitcher_slot or not has_pitcher_slot:
                batters.append(player)

        return pitchers, batters
