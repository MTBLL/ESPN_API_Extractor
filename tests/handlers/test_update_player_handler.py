import asyncio

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.handlers.update_player_handler import UpdatePlayerHandler


def test_update_player_handler_updates_kona_stats(josh_hader_kona_card):
    existing = Player({"id": 32760, "fullName": "Josh Hader"})
    handler = UpdatePlayerHandler(league_id=10998, year=2025)

    updated_players = asyncio.run(
        handler.execute([existing], pro_players_data=[josh_hader_kona_card])
    )

    assert updated_players[0] is existing
    stats = updated_players[0].stats
    assert "projections" in stats

    expected_svhd = (
        next(
            entry
            for entry in josh_hader_kona_card["player"]["stats"]
            if entry.get("seasonId") == 2025
            and entry.get("statSourceId") == 1
            and entry.get("statSplitTypeId") == 0
        )
        .get("stats", {})
        .get("83")
    )
    assert expected_svhd is not None
    assert stats["projections"]["SVHD"] == expected_svhd
    assert updated_players[0].on_team_id == josh_hader_kona_card.get("onTeamId")
