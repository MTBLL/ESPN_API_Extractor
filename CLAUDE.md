# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands
- Install dependencies: `poetry install`
- Run all tests: `poetry run pytest tests/`
- Run a single test: `poetry run pytest tests/test_file.py::TestClass::test_function`
- Test with coverage: `poetry run pytest --cov=espn_api_extractor --cov-report=xml tests/`
- Run the player extractor: `poetry run python -m espn_api_extractor.runners.players`
- Debug with players dump: `poetry run python debug_dump_players.py`

## Code Style Guidelines
- **Python Version**: 3.13+
- **Type Annotations**: Use proper type hints for all function parameters and return values
- **Imports**: Group standard library, third-party, and local imports in separate blocks
- **Exceptions**: Use specific exception types and add proper error handling
- **Formatting**: Follow PEP 8 guidelines
- **Classes**: Use proper object-oriented principles with clear inheritance
- **Logging**: Use the Logger class from utils.logger for consistent logging
- **Threading**: Use thread-safe logging with locks when implementing multi-threading
- **Testing**: Create comprehensive tests with pytest fixtures and mocks
- **Documentation**: Add docstrings to all classes and methods