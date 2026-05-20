import asyncio
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.controllers.player_controller import PlayerController
from espn_api_extractor.handlers import FullHydrationHandler
from espn_api_extractor.models.player_model import PlayerModel


def _make_player_model(player_id: int) -> PlayerModel:
    return PlayerModel(id=player_id, name=f"Player {player_id}")  # type: ignore


def _build_controller(monkeypatch, espn_players):
    extract_handler = MagicMock()
    extract_handler.fetch_player_cards.return_value = espn_players
    extract_handler.get_slot_flags.return_value = (False, True)

    graphql_handler = MagicMock()
    graphql_handler.get_existing_players.return_value = []

    update_handler = MagicMock()
    update_handler.execute = AsyncMock(return_value=[])

    full_handler = MagicMock()
    full_handler.execute = AsyncMock(return_value=[])

    monkeypatch.setattr(
        "espn_api_extractor.controllers.player_controller.PlayerExtractHandler",
        MagicMock(return_value=extract_handler),
    )
    monkeypatch.setattr(
        "espn_api_extractor.controllers.player_controller.GraphQLHandler",
        MagicMock(return_value=graphql_handler),
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
        force_full_extraction=False,
        graphql_config="hasura_config.json",
    )

    controller = PlayerController(args)
    return controller, extract_handler, update_handler, full_handler, graphql_handler


def test_player_controller_no_updates_fully_hydrates(
    monkeypatch, top_kona_cards, corbin_carroll_kona_card, carroll_athlete_fixture_data
):
    """
    Since there are no hasura values returned, the controller implicitly does fully hydrate
    """

    def _mock_get_player_data(self, player_id, **kwargs) -> Dict[str, Any]:
        return carroll_athlete_fixture_data

    monkeypatch.setattr(
        "espn_api_extractor.requests.core_requests.EspnCoreRequests._get_player_data",
        _mock_get_player_data,
    )

    espn_players = [corbin_carroll_kona_card]
    controller, extract_handler, _, full_handler, _ = _build_controller(
        monkeypatch, espn_players
    )
    controller.full_hydration_handler = FullHydrationHandler(
        league_id=controller.league_id,
        year=controller.year,
        threads=controller.threads,
        batch_size=controller.batch_size,
    )

    result = asyncio.run(controller.execute())
    carroll = result["batters"][0]

    extract_handler.fetch_player_cards.assert_called_once_with()
    assert carroll.slug == "corbin-carroll"


def test_player_controller_sample_size_skips_updates(monkeypatch):
    espn_players = [{"id": 1}, {"id": 2}, {"id": 3}]
    controller, _, update_handler, full_handler, graphql_handler = _build_controller(
        monkeypatch, espn_players
    )
    controller.sample_size = 1
    full_handler.execute = AsyncMock(return_value=[])
    graphql_handler.get_existing_players.return_value = [
        _make_player_model(1),
        _make_player_model(2),
    ]

    result = asyncio.run(controller.execute())  # type: ignore

    update_handler.execute.assert_not_called()
    full_handler.execute.assert_awaited_once()
    called_ids = full_handler.execute.call_args.args[0]
    assert isinstance(called_ids, set)
    assert len(called_ids) == 1
    assert result["players"] == []


def test_player_controller_handles_update_failure(monkeypatch):
    espn_players = [{"id": 1}, {"id": 2}]
    controller, _, update_handler, full_handler, graphql_handler = _build_controller(
        monkeypatch, espn_players
    )
    update_handler.execute = AsyncMock(side_effect=RuntimeError("update boom"))
    full_handler.execute = AsyncMock(return_value=[])
    graphql_handler.get_existing_players.return_value = [_make_player_model(1)]

    result = asyncio.run(controller.execute())

    update_handler.execute.assert_awaited_once()
    full_handler.execute.assert_awaited_once()
    assert result["players"] == []
    assert any(
        "Failed to update existing players: update boom" in msg
        for msg in result["failures"]
    )


def test_player_controller_handles_full_hydration_failure(monkeypatch):
    espn_players = [{"id": 1}, {"id": 2}]
    controller, _, update_handler, full_handler, graphql_handler = _build_controller(
        monkeypatch, espn_players
    )
    update_handler.execute = AsyncMock(return_value=[])
    full_handler.execute = AsyncMock(side_effect=RuntimeError("hydrate boom"))
    graphql_handler.get_existing_players.return_value = [_make_player_model(1)]

    result = asyncio.run(controller.execute())

    update_handler.execute.assert_awaited_once()
    full_handler.execute.assert_awaited_once()
    assert result["players"] == []
    assert any(
        "Unable to hydrate new players: hydrate boom" in msg
        for msg in result["failures"]
    )


def test_player_controller_handles_critical_failure(monkeypatch):
    espn_players = [{"id": 1}]
    controller, extract_handler, update_handler, full_handler, graphql_handler = (
        _build_controller(monkeypatch, espn_players)
    )
    extract_handler.fetch_player_cards.side_effect = RuntimeError("boom")
    graphql_handler.get_existing_players.return_value = [_make_player_model(1)]

    result = asyncio.run(controller.execute())

    update_handler.execute.assert_not_called()
    full_handler.execute.assert_not_called()
    assert result["players"] == []
    assert result["failures"] == ["Critical failure in player extraction: boom"]
