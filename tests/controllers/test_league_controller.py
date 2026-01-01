import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

from espn_api_extractor.controllers.league_controller import LeagueController


def test_league_controller_execute_success(monkeypatch):
    args = SimpleNamespace(league_id=10998, year=2025, espn_s2="s2", swid="swid")

    handler = MagicMock()
    handler.fetch.return_value = {"id": 10998}

    handler_class = MagicMock(return_value=handler)
    logger = MagicMock()
    logger_class = MagicMock(return_value=MagicMock(logging=logger))

    monkeypatch.setattr(
        "espn_api_extractor.controllers.league_controller.LeagueHandler",
        handler_class,
    )
    monkeypatch.setattr(
        "espn_api_extractor.controllers.league_controller.Logger",
        logger_class,
    )

    controller = LeagueController(args)
    result = asyncio.run(controller.execute())

    handler_class.assert_called_once_with(
        league_id=10998,
        year=2025,
        espn_s2="s2",
        swid="swid",
    )
    logger.info.assert_called_once_with(
        "Fetching league data for league 10998 year 2025"
    )
    logger.error.assert_not_called()
    assert result == {"league": {"id": 10998}, "failures": []}


def test_league_controller_execute_failure(monkeypatch):
    args = SimpleNamespace(league_id=10998, year=2025)

    handler = MagicMock()
    handler.fetch.side_effect = RuntimeError("boom")

    handler_class = MagicMock(return_value=handler)
    logger = MagicMock()
    logger_class = MagicMock(return_value=MagicMock(logging=logger))

    monkeypatch.setattr(
        "espn_api_extractor.controllers.league_controller.LeagueHandler",
        handler_class,
    )
    monkeypatch.setattr(
        "espn_api_extractor.controllers.league_controller.Logger",
        logger_class,
    )

    controller = LeagueController(args)
    result = asyncio.run(controller.execute())

    handler_class.assert_called_once_with(
        league_id=10998,
        year=2025,
        espn_s2=None,
        swid=None,
    )
    logger.info.assert_called_once_with(
        "Fetching league data for league 10998 year 2025"
    )
    logger.error.assert_called_once_with("League extraction failed: boom")
    assert result == {"league": None, "failures": ["League extraction failed: boom"]}
