from typing import Dict, List, Optional, Set

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.requests import EspnCoreRequests, EspnFantasyRequests
from espn_api_extractor.requests.constants import FantasySports
from espn_api_extractor.utils.logger import Logger


class FullHydrationHandler:
    """
    Handler for complete hydration of new players.

    Executes full ESPN API workflow:
    - Fantasy API calls (get_pro_players, get_player_cards)
    - Multi-threaded Core API hydration (bio + stats)
    - Player object hydration pipeline
    """

    def __init__(
        self,
        league_id: int,
        year: int,
        threads: Optional[int] = None,
        batch_size: int = 100,
    ):
        self.league_id = league_id
        self.year = year
        self.threads = threads
        self.batch_size = batch_size
        self.logger = Logger("FullHydrationHandler")

        # Initialize API requestors
        self.fantasy_requests = EspnFantasyRequests(
            league_id=self.league_id, sport=FantasySports.MLB, year=self.year
        )
        self.core_requests = EspnCoreRequests(
            sport="mlb", year=self.year, max_workers=self.threads
        )

    async def execute(
        self, player_ids: Set[int], pro_players_data: Optional[List[Dict]] = None
    ) -> List[Player]:
        """
        Execute complete hydration for new players.

        Args:
            player_ids: Set of new player IDs to fully hydrate
            pro_players_data: Optional pre-fetched pro_players data (optimization to avoid re-fetching)

        Returns:
            List[Player]: Fully hydrated player objects
        """
        self.logger.logging.info(f"Fully hydrating {len(player_ids)} new players")

        # Step 1: Create Player objects from player card data
        if pro_players_data is None:
            self.logger.logging.info("Fetching player cards from ESPN")
            pro_players_data = []
            kona_batch_size = 100
            player_ids_list = list(player_ids)
            for i in range(0, len(player_ids_list), kona_batch_size):
                batch = player_ids_list[i : i + kona_batch_size]
                self.logger.logging.info(
                    f"Fetching kona_playercard batch {i // kona_batch_size + 1}/{(len(player_ids_list) + kona_batch_size - 1) // kona_batch_size} "
                    f"({len(batch)} players)"
                )
                try:
                    kona_data = self.fantasy_requests.get_player_cards(batch)
                    if kona_data and "players" in kona_data:
                        pro_players_data.extend(kona_data["players"])
                except Exception as e:
                    self.logger.logging.warning(
                        f"Failed to fetch kona_playercard batch starting at index {i}: {e}"
                    )

        # Filter to only the players we need to hydrate
        players_to_hydrate = []
        pro_players_map = (
            {p["id"]: p for p in pro_players_data} if pro_players_data else {}
        )

        for player_id in player_ids:
            if player_id in pro_players_map:
                player = Player(pro_players_map[player_id], current_season=self.year)
                players_to_hydrate.append(player)
            else:
                self.logger.logging.warning(
                    f"Player ID {player_id} not found in pro_players data"
                )

        self.logger.logging.info(f"Created {len(players_to_hydrate)} Player objects")

        if not players_to_hydrate:
            return []

        # Step 2: Multi-threaded hydration with bio + stats from Core API
        self.logger.logging.info("Hydrating with bio and stats data from Core API")
        hydrated_players, failed_players = self.core_requests.hydrate_players(
            players_to_hydrate, batch_size=self.batch_size, include_stats=True
        )

        if failed_players:
            self.logger.logging.warning(
                f"Failed to fully hydrate {len(failed_players)} players"
            )

        self.logger.logging.info(
            f"Successfully fully hydrated {len(hydrated_players)} new players"
        )
        return hydrated_players
