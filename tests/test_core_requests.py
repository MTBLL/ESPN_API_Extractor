import os
import pytest
import unittest.mock as mock
import requests
from requests.exceptions import Timeout, ConnectionError

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.requests.core_requests import EspnCoreRequests
from espn_api_extractor.utils.logger import Logger


class TestCoreRequests:
    """Test suite for EspnCoreRequests class"""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing"""
        logger = Logger("test")
        logger.logging = mock.MagicMock()
        logger.log_request = mock.MagicMock()
        return logger

    @pytest.fixture
    def core_requests(self, mock_logger):
        """Create an EspnCoreRequests instance for testing"""
        return EspnCoreRequests(sport="mlb", year=2025, logger=mock_logger)

    def test_init_with_valid_sport(self, mock_logger):
        """Test initialization with valid sport"""
        # Test with MLB (only MLB is currently supported according to constant.py)
        mlb_requests = EspnCoreRequests(sport="mlb", year=2025, logger=mock_logger)
        assert mlb_requests.sport == "mlb"
        assert mlb_requests.year == 2025
        assert mlb_requests.logger == mock_logger
        assert mlb_requests.max_workers == min(32, os.cpu_count() * 4)

        # Test with custom max_workers
        custom_requests = EspnCoreRequests(sport="mlb", year=2025, logger=mock_logger, max_workers=10)
        assert custom_requests.max_workers == 10

    def test_init_with_invalid_sport(self, mock_logger):
        """Test initialization with invalid sport"""
        with pytest.raises(SystemExit):
            EspnCoreRequests(sport="invalid", year=2025, logger=mock_logger)

    def test_check_request_status(self, core_requests):
        """Test _check_request_status method with different status codes"""
        # Test with 200 status code
        result = core_requests._check_request_status(200, extend="test/endpoint")
        assert result is None
        core_requests.logger.logging.warn.assert_not_called()

        # Test with 404 status code
        result = core_requests._check_request_status(404, extend="test/endpoint")
        assert result is None
        core_requests.logger.logging.warn.assert_called_with("Endpoint not found: test/endpoint")

        # Test with 429 status code
        core_requests.logger.logging.warn.reset_mock()
        result = core_requests._check_request_status(429, extend="test/endpoint")
        assert result is None
        core_requests.logger.logging.warn.assert_called_with("Rate limit exceeded")

        # Test with 500 status code
        core_requests.logger.logging.warn.reset_mock()
        result = core_requests._check_request_status(500, extend="test/endpoint")
        assert result is None
        core_requests.logger.logging.warn.assert_called_with("Internal server error")

        # Test with 503 status code
        core_requests.logger.logging.warn.reset_mock()
        result = core_requests._check_request_status(503, extend="test/endpoint")
        assert result is None
        core_requests.logger.logging.warn.assert_called_with("Service unavailable")

        # Test with other status code
        core_requests.logger.logging.warn.reset_mock()
        result = core_requests._check_request_status(418, extend="test/endpoint")
        assert result is None
        core_requests.logger.logging.warn.assert_called_with("Unknown error: 418")

    @mock.patch('requests.get')
    def test_get_method(self, mock_get, core_requests):
        """Test _get method"""
        # Setup mock response
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_get.return_value = mock_response

        # Test _get method
        result = core_requests._get(
            params={"param1": "value1"},
            headers={"header1": "value1"},
            extend="/test/endpoint"
        )

        # Verify request was made correctly
        mock_get.assert_called_with(
            core_requests.sport_endpoint + "/test/endpoint",
            params={"param1": "value1"},
            headers={"header1": "value1"},
            cookies=core_requests.session.cookies
        )

        # Verify log_request was called correctly
        core_requests.logger.log_request.assert_called_with(
            endpoint=core_requests.sport_endpoint + "/test/endpoint",
            params={"param1": "value1"},
            headers={"header1": "value1"},
            response={"test": "data"}
        )

        # Verify result
        assert result == {"test": "data"}

    @mock.patch('requests.get')
    def test_get_player_data_success(self, mock_get, core_requests):
        """Test _get_player_data method with successful response"""
        # Setup mock response
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"player": "data"}
        mock_get.return_value = mock_response

        # Test _get_player_data method
        result = core_requests._get_player_data(player_id=12345)

        # Verify request was made correctly
        mock_get.assert_called_with(
            core_requests.sport_endpoint + "/athletes/12345",
            params={},
            headers=core_requests.session.headers,
            cookies=core_requests.session.cookies,
            timeout=10
        )

        # Verify result
        assert result == {"player": "data"}

    @mock.patch('requests.get')
    def test_get_player_data_404(self, mock_get, core_requests):
        """Test _get_player_data method with 404 response"""
        # Setup mock response
        mock_response = mock.MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Test _get_player_data method
        result = core_requests._get_player_data(player_id=12345)

        # Verify request was made correctly
        mock_get.assert_called_once()

        # Verify result is None (indicating failure)
        assert result is None

        # Verify log messages were called correctly
        core_requests.logger.logging.warning.assert_any_call("Player ID 12345 not found (404) - skipping retries")

    @mock.patch('requests.get')
    def test_get_player_data_retry_non_404(self, mock_get, core_requests):
        """Test _get_player_data method with retryable error"""
        # Setup mock responses: first 429 (retryable), then 200 (success)
        mock_response1 = mock.MagicMock()
        mock_response1.status_code = 429  # Rate limit - should retry
        
        mock_response2 = mock.MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {"player": "data_after_retry"}
        
        mock_get.side_effect = [mock_response1, mock_response2]

        # Mock sleep to avoid waiting during test
        with mock.patch('time.sleep') as mock_sleep:
            # Test _get_player_data method
            result = core_requests._get_player_data(player_id=12345)

        # Verify request was made correctly twice
        assert mock_get.call_count == 2

        # Verify sleep was called once with correct backoff
        mock_sleep.assert_called_once_with(1)

        # Verify result contains data from second call
        assert result == {"player": "data_after_retry"}

    @mock.patch('requests.get')
    def test_get_player_data_exception(self, mock_get, core_requests):
        """Test _get_player_data method with exceptions"""
        # Setup mock to raise exceptions
        mock_get.side_effect = [
            Timeout("Connection timed out"),
            ConnectionError("Connection error"),
            ValueError("Invalid response")
        ]

        # Mock sleep to avoid waiting during test
        with mock.patch('time.sleep'):
            # Test _get_player_data method
            result = core_requests._get_player_data(player_id=12345, max_retries=3)

        # Verify request was attempted 3 times
        assert mock_get.call_count == 3

        # Verify result is None (indicating failure)
        assert result is None

        # Verify log messages
        assert core_requests.logger.logging.warning.call_count >= 3
        core_requests.logger.logging.error.assert_called_once_with(
            "Failed to fetch player 12345 after 3 attempts"
        )

    def test_hydrate_player_without_id(self, core_requests):
        """Test _hydrate_player with a player missing ID"""
        player = Player({"fullName": "Test Player"})  # No ID provided
        
        # Should raise an assertion error
        with pytest.raises(AssertionError):
            core_requests._hydrate_player(player)

    def test_hydrate_player_hydration_exception(self, core_requests):
        """Test _hydrate_player method with exception during hydration"""
        # Create a player with valid ID
        player = Player({"id": 123, "fullName": "Test Player"})
        
        # Mock _get_player_data to return data
        core_requests._get_player_data = mock.MagicMock(return_value={"id": "123"})
        
        # Mock player.hydrate to raise an exception
        original_hydrate = Player.hydrate
        Player.hydrate = mock.MagicMock(side_effect=ValueError("Test error"))
        
        try:
            # Call _hydrate_player
            result_player, success = core_requests._hydrate_player(player)
            
            # Verify results
            assert result_player is player
            assert success is False
            core_requests.logger.logging.error.assert_called_with(
                "Error hydrating player 123: Test error"
            )
        finally:
            # Restore original method
            Player.hydrate = original_hydrate