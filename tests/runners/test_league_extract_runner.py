import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

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
