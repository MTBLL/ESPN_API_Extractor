from typing import Dict, List, Set

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.requests import EspnCoreRequests, EspnFantasyRequests
from espn_api_extractor.requests.constants import FantasySports
from espn_api_extractor.utils.logger import Logger


class UpdatePlayerHandler:
    """
    Handler for selective updates of existing players.

    Updates dynamic data: stats, team, fantasy team, injury status,
    position eligibility, ownership percentages.
    """

    def __init__(
        self, league_id: int, year: int, threads: int = None, batch_size: int = 100
    ):
        self.league_id = league_id
        self.year = year
        self.threads = threads
        self.batch_size = batch_size
        self.logger = Logger("UpdatePlayerHandler")

        # Initialize API requestors
        self.fantasy_requests = EspnFantasyRequests(
            league_id=self.league_id, sport=FantasySports.MLB, year=self.year
        )
        self.core_requests = EspnCoreRequests(
            sport="mlb", year=self.year, max_workers=self.threads
        )

    async def execute(
        self,
        player_ids: Set[int],
        pro_players_data: List[Dict] = None,
        include_stats_update: bool = True,
    ) -> List[Player]:
        """
        Execute selective updates for existing players.

        Args:
            player_ids: Set of existing player IDs to update
            pro_players_data: Optional pre-fetched pro_players data (optimization)
            include_stats_update: Whether to fetch updated stats from Core API (default: True)

        Returns:
            List[Player]: Updated player objects with refreshed data
        """
        self.logger.logging.info(f"Updating {len(player_ids)} existing players")

        # Step 1: Get current pro_players data if not provided
        if pro_players_data is None:
            self.logger.logging.info("Fetching pro_players data from ESPN")
            pro_players_data = self.fantasy_requests.get_pro_players()

        # Create map for quick lookup
        pro_players_map = {p["id"]: p for p in pro_players_data}

        # Step 2: Create/update Player objects with latest data
        updated_players = []
        for player_id in player_ids:
            if player_id in pro_players_map:
                player_data = pro_players_map[player_id]
                player = Player(player_data)
                updated_players.append(player)
            else:
                self.logger.logging.warning(
                    f"Player ID {player_id} not found in current ESPN pro_players"
                )

        if not updated_players:
            self.logger.logging.warning("No players found to update")
            return []

        self.logger.logging.info(
            f"Created {len(updated_players)} Player objects from pro_players data"
        )

        # Step 3: Optionally update with latest stats from Core API
        if include_stats_update:
            self.logger.logging.info("Updating with latest stats from Core API")
            # Only fetch stats (not bio, since that's mostly static)
            hydrated_players, failed_players = self.core_requests.hydrate_players(
                updated_players,
                batch_size=self.batch_size,
                include_stats=True,  # Get latest stats
            )

            if failed_players:
                self.logger.logging.warning(
                    f"Failed to update stats for {len(failed_players)} players"
                )

            self.logger.logging.info(
                f"Successfully updated {len(hydrated_players)} players with stats"
            )
            return hydrated_players
        else:
            self.logger.logging.info(
                f"Successfully updated {len(updated_players)} players (stats update skipped)"
            )
            return updated_players
