from typing import Any, Dict, List

from espn_api_extractor.baseball.player import Player


class PlayerExtractHandler:
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
