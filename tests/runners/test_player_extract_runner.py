import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from espn_api_extractor.runners.player_extract_runner import PlayerExtractRunner


def test_player_extract_runner_uses_graphql_when_available(monkeypatch, tmp_path):
    args = SimpleNamespace(
        year=2025,
        output_dir=str(tmp_path),
        graphql_config="hasura_config.json",
        force_full_extraction=False,
        as_models=False,
    )

    controller = MagicMock()
    controller_player = MagicMock()
    controller.execute = AsyncMock(
        return_value={"players": [controller_player], "failures": []}
    )

    graphql_client = MagicMock()
    graphql_client.is_available = True
    graphql_client.get_existing_players.return_value = [MagicMock(), MagicMock()]
    graphql_client.initialize_with_hitl.return_value = graphql_client

    graphql_class = MagicMock(return_value=graphql_client)

    monkeypatch.setattr(
        "espn_api_extractor.runners.player_extract_runner.GraphQLClient",
        graphql_class,
    )
    monkeypatch.setattr(
        "espn_api_extractor.runners.player_extract_runner.PlayerController",
        MagicMock(return_value=controller),
    )

    from espn_api_extractor.runners import player_extract_runner

    existing_a = MagicMock()
    existing_b = MagicMock()
    monkeypatch.setattr(
        player_extract_runner.Player,
        "from_model",
        MagicMock(side_effect=[existing_a, existing_b]),
    )

    runner = PlayerExtractRunner(args)
    monkeypatch.setattr(runner, "_save_extraction_results", MagicMock())

    result = asyncio.run(runner.run())

    graphql_class.assert_called_once_with(config_path="hasura_config.json")
    graphql_client.initialize_with_hitl.assert_called_once_with(
        force_full_extraction=False
    )
    graphql_client.get_existing_players.assert_called_once_with()
    controller.execute.assert_awaited_once_with([existing_a, existing_b])
    runner._save_extraction_results.assert_called_once_with([controller_player], [])
    assert result == [controller_player]


def test_player_extract_runner_skips_graphql_when_unavailable(monkeypatch, tmp_path):
    args = SimpleNamespace(
        year=2025,
        output_dir=str(tmp_path),
        graphql_config="hasura_config.json",
        force_full_extraction=False,
        as_models=False,
    )

    controller = MagicMock()
    controller_player = MagicMock()
    controller.execute = AsyncMock(
        return_value={"players": [controller_player], "failures": []}
    )

    graphql_client = MagicMock()
    graphql_client.is_available = False
    graphql_client.initialize_with_hitl.return_value = graphql_client

    graphql_class = MagicMock(return_value=graphql_client)

    monkeypatch.setattr(
        "espn_api_extractor.runners.player_extract_runner.GraphQLClient",
        graphql_class,
    )
    monkeypatch.setattr(
        "espn_api_extractor.runners.player_extract_runner.PlayerController",
        MagicMock(return_value=controller),
    )

    runner = PlayerExtractRunner(args)
    monkeypatch.setattr(runner, "_save_extraction_results", MagicMock())

    result = asyncio.run(runner.run())

    graphql_client.get_existing_players.assert_not_called()
    controller.execute.assert_awaited_once_with([])
    runner._save_extraction_results.assert_called_once_with([controller_player], [])
    assert result == [controller_player]


def test_player_extract_runner_returns_models_when_requested(monkeypatch, tmp_path):
    args = SimpleNamespace(
        year=2025,
        output_dir=str(tmp_path),
        graphql_config="hasura_config.json",
        force_full_extraction=False,
        as_models=True,
    )

    controller = MagicMock()
    player = MagicMock()
    player.to_model.return_value = {"id": 1}
    controller.execute = AsyncMock(return_value={"players": [player], "failures": []})

    graphql_client = MagicMock()
    graphql_client.is_available = False
    graphql_client.initialize_with_hitl.return_value = graphql_client

    graphql_class = MagicMock(return_value=graphql_client)

    monkeypatch.setattr(
        "espn_api_extractor.runners.player_extract_runner.GraphQLClient",
        graphql_class,
    )
    monkeypatch.setattr(
        "espn_api_extractor.runners.player_extract_runner.PlayerController",
        MagicMock(return_value=controller),
    )

    runner = PlayerExtractRunner(args)
    monkeypatch.setattr(runner, "_save_extraction_results", MagicMock())

    result = asyncio.run(runner.run())

    controller.execute.assert_awaited_once_with([])
    runner._save_extraction_results.assert_called_once_with([player], [])
    assert result == [{"id": 1}]
