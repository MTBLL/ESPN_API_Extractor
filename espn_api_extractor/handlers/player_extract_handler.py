from typing import Any, Dict, List, Optional

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.requests.constants import FantasySports
from espn_api_extractor.requests.fantasy_requests import EspnFantasyRequests


class PlayerExtractHandler:
    def __init__(
        self,
        args: Optional[object] = None,
        *,
        league_id: Optional[int] = None,
        year: Optional[int] = None,
        fantasy_requests: Optional[EspnFantasyRequests] = None,
    ):
        if args is not None:
            league_id = getattr(args, "league_id", league_id)
            year = getattr(args, "year", year)

        self.fantasy_requests = fantasy_requests

        if self.fantasy_requests is None and league_id is not None and year is not None:
            self.fantasy_requests = EspnFantasyRequests(
                league_id=league_id, sport=FantasySports.MLB, year=year
            )

    def fetch_player_cards(
        self, player_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        if self.fantasy_requests is None:
            raise RuntimeError("PlayerExtractHandler is not configured for fetching")

        response = self.fantasy_requests.get_player_cards(player_ids=player_ids or [])
        if isinstance(response, dict):
            players = response.get("players", [])
        elif isinstance(response, list):
            players = response
        else:
            players = []

        return [player for player in players if isinstance(player, dict)]

    def get_slot_flags(self, player: Player) -> tuple[bool, bool]:
        slots = self._normalize_eligible_slots(player)
        if not slots:
            return False, False
        has_pitcher_slot = any("P" in slot for slot in slots)
        has_non_pitcher_slot = any("P" not in slot for slot in slots)
        return has_pitcher_slot, has_non_pitcher_slot

    def is_two_way_player(self, player: Player) -> bool:
        has_pitcher_slot, has_non_pitcher_slot = self.get_slot_flags(player)
        return has_pitcher_slot and has_non_pitcher_slot

    def apply_pitcher_transforms(self, player: Player, data: Dict[str, Any]) -> None:
        if self.is_two_way_player(player):
            self._override_pitcher_positions(data)

    def _normalize_eligible_slots(self, player: Player) -> List[str]:
        slots = getattr(player, "eligible_slots", None)
        if not slots:
            return []
        return [str(slot) for slot in slots if slot is not None]

    def _override_pitcher_positions(self, data: Dict[str, Any]) -> None:
        data["primary_position"] = "SP"
        data["pos"] = "SP"
        data["position_name"] = "Starting Pitcher"
