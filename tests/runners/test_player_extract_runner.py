import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.handlers.player_extract_handler import PlayerExtractHandler
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
        return_value={
            "players": [controller_player],
            "pitchers": [],
            "batters": [controller_player],
            "failures": [],
        }
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
    runner._save_extraction_results.assert_called_once_with(  # type: ignore
        [], [controller_player], []
    )
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
        return_value={
            "players": [controller_player],
            "pitchers": [],
            "batters": [controller_player],
            "failures": [],
        }
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
    runner._save_extraction_results.assert_called_once_with([], [controller_player], [])  # type: ignore
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
    controller.execute = AsyncMock(
        return_value={
            "players": [player],
            "pitchers": [],
            "batters": [player],
            "failures": [],
        }
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

    controller.execute.assert_awaited_once_with([])
    runner._save_extraction_results.assert_called_once_with([], [player], [])  # type: ignore[reportAttributeAccessIssue]
    assert result == [{"id": 1}]


def test_player_extract_runner_saves_sorted_players_and_failures(tmp_path):
    runner = PlayerExtractRunner.__new__(PlayerExtractRunner)
    runner.args = SimpleNamespace(output_dir=str(tmp_path), year=2025)
    runner.logger = MagicMock()
    runner.handler = PlayerExtractHandler()

    high = MagicMock()
    high.percent_owned = 50
    high.eligible_slots = ["P"]
    high.to_model.return_value.model_dump.return_value = {
        "id": "high",
        "primary_position": "SP",
        "pos": "SP",
        "position_name": "Starting Pitcher",
    }

    low = MagicMock()
    low.percent_owned = 10
    low.eligible_slots = ["OF"]
    low.to_model.return_value.model_dump.return_value = {
        "id": "low",
        "primary_position": "OF",
        "pos": "OF",
        "position_name": "Outfield",
    }

    zero = MagicMock()
    zero.percent_owned = 0
    zero.eligible_slots = ["P", "UTIL"]
    zero.to_model.return_value.model_dump.return_value = {
        "id": "zero",
        "primary_position": "DH",
        "pos": "DH",
        "position_name": "Designated Hitter",
    }

    runner._save_extraction_results([high, zero], [low, zero], ["oops"])

    pitchers_files = list(tmp_path.glob("espn_pitchers_2025_*.json"))
    assert len(pitchers_files) == 1
    with pitchers_files[0].open() as f:
        pitchers_data = json.load(f)
    assert [player["id"] for player in pitchers_data] == ["high", "zero"]
    assert pitchers_data[1]["primary_position"] == "SP"
    assert pitchers_data[1]["pos"] == "SP"
    assert pitchers_data[1]["position_name"] == "Starting Pitcher"

    batters_files = list(tmp_path.glob("espn_batters_2025_*.json"))
    assert len(batters_files) == 1
    with batters_files[0].open() as f:
        batters_data = json.load(f)
    assert [player["id"] for player in batters_data] == ["low", "zero"]
    assert batters_data[1]["primary_position"] == "DH"
    assert batters_data[1]["pos"] == "DH"
    assert batters_data[1]["position_name"] == "Designated Hitter"


def test_player_extract_runner_adds_pitching_rate_stats(tmp_path):
    runner = PlayerExtractRunner.__new__(PlayerExtractRunner)
    runner.args = SimpleNamespace(output_dir=str(tmp_path), year=2025)
    runner.logger = MagicMock()
    runner.handler = PlayerExtractHandler()

    pitcher_data = {
        "id": 999,
        "fullName": "Test Pitcher",
        "eligibleSlots": [13],
        "defaultPositionId": 1,
        "player": {
            "stats": [
                {
                    "seasonId": 2025,
                    "statSourceId": 0,
                    "statSplitTypeId": 0,
                    "stats": {"34": 30, "48": 10},
                },
                {
                    "seasonId": 2025,
                    "statSourceId": 1,
                    "statSplitTypeId": 0,
                    "stats": {"34": 16, "48": 9},
                },
            ]
        },
    }
    pitcher = Player(pitcher_data, 2025)
    pitcher.percent_owned = 10
    pitcher.eligible_slots = ["P"]

    runner._save_extraction_results([pitcher], [], [])

    pitchers_files = list(tmp_path.glob("espn_pitchers_2025_*.json"))
    assert len(pitchers_files) == 1
    with pitchers_files[0].open() as f:
        pitchers_data = json.load(f)

    current_season = pitchers_data[0]["stats"]["current_season"]
    assert current_season["IP"] == 10.0
    assert current_season["K/9"] == pytest.approx(9.0, rel=1e-3)

    projections = pitchers_data[0]["stats"]["projections"]
    assert projections["IP"] == 5.1
    assert projections["K/9"] == pytest.approx(15.1875, rel=1e-3)

    failures_files = list(tmp_path.glob("failures_2025_*.json"))
    assert len(failures_files) == 0


def test_player_extract_runner_raises_on_execute_error(monkeypatch, tmp_path):
    args = SimpleNamespace(
        year=2025,
        output_dir=str(tmp_path),
        graphql_config="hasura_config.json",
        force_full_extraction=False,
        as_models=False,
    )

    controller = MagicMock()
    controller.execute = AsyncMock(side_effect=RuntimeError("boom"))

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

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(runner.run())

    runner._save_extraction_results.assert_not_called()  # type: ignore[reportAttributeAccessIssue]
