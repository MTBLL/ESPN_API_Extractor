import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from espn_api_extractor.runners.league_extract_runner import LeagueExtractRunner


def test_league_extract_runner_saves_when_data_present(monkeypatch, tmp_path):
    args = SimpleNamespace(
        league_id=10998,
        year=2025,
        output_dir=str(tmp_path),
    )

    controller = MagicMock()
    league_data = {"settings": {"name": "Test League"}}
    controller.execute = AsyncMock(
        return_value={"league": league_data, "failures": []}
    )

    monkeypatch.setattr(
        "espn_api_extractor.runners.league_extract_runner.LeagueController",
        MagicMock(return_value=controller),
    )

    runner = LeagueExtractRunner(args)
    monkeypatch.setattr(runner, "_save_extraction_results", MagicMock())

    result = asyncio.run(runner.run())

    controller.execute.assert_awaited_once_with()
    runner._save_extraction_results.assert_called_once_with(league_data, [])
    assert result == league_data


def test_league_extract_runner_skips_save_when_no_data(monkeypatch, tmp_path):
    args = SimpleNamespace(
        league_id=10998,
        year=2025,
        output_dir=str(tmp_path),
    )

    controller = MagicMock()
    controller.execute = AsyncMock(return_value={"league": None, "failures": ["no"]})

    monkeypatch.setattr(
        "espn_api_extractor.runners.league_extract_runner.LeagueController",
        MagicMock(return_value=controller),
    )

    runner = LeagueExtractRunner(args)
    monkeypatch.setattr(runner, "_save_extraction_results", MagicMock())

    result = asyncio.run(runner.run())

    controller.execute.assert_awaited_once_with()
    runner._save_extraction_results.assert_not_called()
    assert result is None


def test_league_extract_runner_save_results_writes_files(tmp_path):
    runner = LeagueExtractRunner.__new__(LeagueExtractRunner)
    runner.args = SimpleNamespace(
        league_id=10998,
        year=2025,
        output_dir=str(tmp_path),
    )
    runner.logger = MagicMock()

    league_data = {"settings": {"name": "Test League"}}
    runner._save_extraction_results(league_data, ["oops"])

    league_files = list(tmp_path.glob("espn_league_10998_2025_*.json"))
    assert len(league_files) == 1
    with league_files[0].open() as f:
        stored_data = json.load(f)
    assert stored_data == league_data

    failures_files = list(tmp_path.glob("league_failures_10998_2025_*.json"))
    assert len(failures_files) == 1
    with failures_files[0].open() as f:
        failures_data = json.load(f)
    assert failures_data["failures"] == ["oops"]
    assert failures_data["count"] == 1


def test_league_extract_runner_raises_on_execute_error(monkeypatch, tmp_path):
    args = SimpleNamespace(
        league_id=10998,
        year=2025,
        output_dir=str(tmp_path),
    )

    controller = MagicMock()
    controller.execute = AsyncMock(side_effect=RuntimeError("boom"))

    monkeypatch.setattr(
        "espn_api_extractor.runners.league_extract_runner.LeagueController",
        MagicMock(return_value=controller),
    )

    runner = LeagueExtractRunner(args)
    monkeypatch.setattr(runner, "_save_extraction_results", MagicMock())

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(runner.run())

    runner._save_extraction_results.assert_not_called()
