import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from espn_api_extractor.controllers.player_controller import PlayerController


def _build_controller(monkeypatch, espn_players):
    espn_request = MagicMock()
    espn_request.get_pro_players.return_value = espn_players

    update_handler = MagicMock()
    update_handler.execute = AsyncMock(return_value=[])

    full_handler = MagicMock()
    full_handler.execute = AsyncMock(return_value=[])

    monkeypatch.setattr(
        "espn_api_extractor.controllers.player_controller.EspnFantasyRequests",
        MagicMock(return_value=espn_request),
    )
    monkeypatch.setattr(
        "espn_api_extractor.controllers.player_controller.ProPlayersHandler",
        MagicMock(),
    )
    monkeypatch.setattr(
        "espn_api_extractor.controllers.player_controller.UpdatePlayerHandler",
        MagicMock(return_value=update_handler),
    )
    monkeypatch.setattr(
        "espn_api_extractor.controllers.player_controller.FullHydrationHandler",
        MagicMock(return_value=full_handler),
    )

    args = SimpleNamespace(
        league_id=10998,
        year=2025,
        threads=None,
        batch_size=100,
        sample_size=None,
    )

    controller = PlayerController(args)
    return controller, espn_request, update_handler, full_handler


def test_player_controller_updates_and_hydrates(monkeypatch):
    espn_players = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
    controller, espn_request, update_handler, full_handler = _build_controller(
        monkeypatch, espn_players
    )

    updated_player = MagicMock()
    new_player = MagicMock()
    update_handler.execute = AsyncMock(return_value=[updated_player])
    full_handler.execute = AsyncMock(return_value=[new_player])

    existing_players = [SimpleNamespace(id=1), SimpleNamespace(id=2), SimpleNamespace(id=99)]

    result = asyncio.run(controller.execute(existing_players))

    espn_request.get_pro_players.assert_called_once_with()
    update_handler.execute.assert_awaited_once_with(
        {1, 2}, pro_players_data=espn_players
    )
    full_handler.execute.assert_awaited_once_with(
        {3, 4}, pro_players_data=espn_players
    )
    assert result["players"] == [updated_player, new_player]
    assert "Player ID 99 in Hasura but not found in ESPN" in result["failures"]


def test_player_controller_sample_size_skips_updates(monkeypatch):
    espn_players = [{"id": 1}, {"id": 2}, {"id": 3}]
    controller, _, update_handler, full_handler = _build_controller(
        monkeypatch, espn_players
    )
    controller.sample_size = 1
    full_handler.execute = AsyncMock(return_value=[])

    existing_players = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    result = asyncio.run(controller.execute(existing_players))

    update_handler.execute.assert_not_called()
    full_handler.execute.assert_awaited_once()
    called_ids = full_handler.execute.call_args.args[0]
    assert isinstance(called_ids, set)
    assert len(called_ids) == 1
    assert result["players"] == []


def test_player_controller_handles_update_failure(monkeypatch):
    espn_players = [{"id": 1}, {"id": 2}]
    controller, _, update_handler, full_handler = _build_controller(
        monkeypatch, espn_players
    )
    update_handler.execute = AsyncMock(side_effect=RuntimeError("update boom"))
    full_handler.execute = AsyncMock(return_value=[])

    existing_players = [SimpleNamespace(id=1)]

    result = asyncio.run(controller.execute(existing_players))

    update_handler.execute.assert_awaited_once()
    full_handler.execute.assert_awaited_once()
    assert result["players"] == []
    assert any("Failed to update existing players: update boom" in msg for msg in result["failures"])


def test_player_controller_handles_full_hydration_failure(monkeypatch):
    espn_players = [{"id": 1}, {"id": 2}]
    controller, _, update_handler, full_handler = _build_controller(
        monkeypatch, espn_players
    )
    update_handler.execute = AsyncMock(return_value=[])
    full_handler.execute = AsyncMock(side_effect=RuntimeError("hydrate boom"))

    existing_players = [SimpleNamespace(id=1)]

    result = asyncio.run(controller.execute(existing_players))

    update_handler.execute.assert_awaited_once()
    full_handler.execute.assert_awaited_once()
    assert result["players"] == []
    assert any("Failed to hydrate new players: hydrate boom" in msg for msg in result["failures"])


def test_player_controller_handles_critical_failure(monkeypatch):
    espn_request = MagicMock()
    espn_request.get_pro_players.side_effect = RuntimeError("boom")

    update_handler = MagicMock()
    update_handler.execute = AsyncMock()

    full_handler = MagicMock()
    full_handler.execute = AsyncMock()

    monkeypatch.setattr(
        "espn_api_extractor.controllers.player_controller.EspnFantasyRequests",
        MagicMock(return_value=espn_request),
    )
    monkeypatch.setattr(
        "espn_api_extractor.controllers.player_controller.ProPlayersHandler",
        MagicMock(),
    )
    monkeypatch.setattr(
        "espn_api_extractor.controllers.player_controller.UpdatePlayerHandler",
        MagicMock(return_value=update_handler),
    )
    monkeypatch.setattr(
        "espn_api_extractor.controllers.player_controller.FullHydrationHandler",
        MagicMock(return_value=full_handler),
    )

    args = SimpleNamespace(
        league_id=10998,
        year=2025,
        threads=None,
        batch_size=100,
        sample_size=None,
    )

    controller = PlayerController(args)

    result = asyncio.run(controller.execute([SimpleNamespace(id=1)]))

    update_handler.execute.assert_not_called()
    full_handler.execute.assert_not_called()
    assert result["players"] == []
    assert result["failures"] == ["Critical failure in player extraction: boom"]
