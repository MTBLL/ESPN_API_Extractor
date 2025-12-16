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

        # Step 1: Create Player objects from pro_players data
        if pro_players_data is None:
            self.logger.logging.info("Fetching pro_players data from ESPN")
            pro_players_data = self.fantasy_requests.get_pro_players()

        # Filter to only the players we need to hydrate
        players_to_hydrate = []
        pro_players_map = (
            {p["id"]: p for p in pro_players_data} if pro_players_data else {}
        )

        for player_id in player_ids:
            if player_id in pro_players_map:
                player = Player(pro_players_map[player_id])
                players_to_hydrate.append(player)
            else:
                self.logger.logging.warning(
                    f"Player ID {player_id} not found in pro_players data"
                )

        self.logger.logging.info(f"Created {len(players_to_hydrate)} Player objects")

        if not players_to_hydrate:
            return []

        # Step 2: Hydrate with kona_playercard data (projections, outlook, etc.)
        self.logger.logging.info("Hydrating with kona_playercard data")
        kona_data = self.fantasy_requests.get_player_cards(list(player_ids))

        if kona_data and "players" in kona_data:
            kona_players_map = {p["id"]: p for p in kona_data["players"]}
            for player in players_to_hydrate:
                if player.id in kona_players_map:
                    try:
                        player.hydrate_kona_playercard(kona_players_map[player.id])
                    except Exception as e:
                        self.logger.logging.warning(
                            f"Failed to hydrate player {player.id} with kona data: {e}"
                        )

        # Step 3: Multi-threaded hydration with bio + stats from Core API
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
