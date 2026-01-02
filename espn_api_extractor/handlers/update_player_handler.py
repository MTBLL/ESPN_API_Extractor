from typing import Dict, List, Optional

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.utils.logger import Logger


class UpdatePlayerHandler:
    """
    Handler for selective updates of existing players.

    Updates dynamic data: stats, team, fantasy team, injury status,
    position eligibility, ownership percentages.
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
        self.logger = Logger("UpdatePlayerHandler")

    async def execute(
        self,
        existing_players: List[Player],
        pro_players_data: Optional[List[Dict]] = None,
        include_stats_update: bool = True,
    ) -> List[Player]:
        """
        Execute selective updates for existing players.

        Args:
            existing_players: Existing player objects to update
            pro_players_data: Optional pre-fetched kona_playercard data (optimization)
            include_stats_update: Whether to fetch updated stats from Core API (default: False)

        Returns:
            List[Player]: Updated player objects with refreshed data
        """
        assert existing_players is not None, "existing_players cannot be None"
        self.logger.logging.info(
            f"Updating {len(existing_players)} existing players"
        )

        if pro_players_data is None:
            raise ValueError("pro_players_data is required for updates")

        # Create map for quick lookup
        pro_players_map = (
            {p["id"]: p for p in pro_players_data} if pro_players_data else {}
        )

        # Step 2: Update existing Player objects with latest kona data
        updated_players = []
        for player in existing_players:
            player_id = player.id
            if player_id in pro_players_map:
                player_data = pro_players_map[player_id]
                updated_players.append(
                    self._apply_kona_updates(
                        player, player_data, include_stats_update
                    )
                )
            else:
                self.logger.logging.warning(
                    f"Player ID {player_id} not found in current ESPN player cards"
                )

        if not updated_players:
            self.logger.logging.warning("No players found to update")
            return []

        self.logger.logging.info(
            f"Updated {len(updated_players)} Player objects from kona data"
        )

        if include_stats_update:
            self.logger.logging.info(
                f"Successfully updated {len(updated_players)} players from kona data"
            )
        else:
            self.logger.logging.info(
                f"Successfully updated {len(updated_players)} players (stats update skipped)"
            )
        return updated_players

    def _apply_kona_updates(
        self, player: Player, player_data: Dict, include_stats_update: bool
    ) -> Player:
        updated = Player(player_data, current_season=self.year)
        update_fields = [
            "primary_position",
            "eligible_slots",
            "pro_team",
            "injury_status",
            "status",
            "injured",
            "percent_owned",
            "season_outlook",
            "draft_ranks",
            "games_played_by_position",
            "draft_auction_value",
            "on_team_id",
            "auction_value_average",
            "transactions",
        ]
        if include_stats_update:
            update_fields.append("stats")

        for field in update_fields:
            value = getattr(updated, field, None)
            if value is not None:
                setattr(player, field, value)

        return player
