import time
import pytest
import unittest.mock as mock
import logging
from concurrent.futures import ThreadPoolExecutor

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.requests.core_requests import EspnCoreRequests
from espn_api_extractor.utils.logger import Logger


class TestMultiThreading:
    @pytest.fixture
    def mock_players(self):
        """Create a list of mock players for testing"""
        return [
            Player({"id": 1, "fullName": "Player 1"}),
            Player({"id": 2, "fullName": "Player 2"}),
            Player({"id": 3, "fullName": "Player 3"}),
            Player({"id": 4, "fullName": "Player 4"}),
            Player({"id": 5, "fullName": "Player 5"}),
            Player({"id": 6, "fullName": "Player 6"}),
            Player({"id": 7, "fullName": "Player 7"}),
            Player({"id": 8, "fullName": "Player 8"}),
            Player({"id": 9, "fullName": "Player 9"}),
            Player({"id": 10, "fullName": "Player 10"}),
        ]

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing"""
        logger = Logger("test")
        logger.logging = mock.MagicMock()
        logger.log_request = mock.MagicMock()
        return logger

    @pytest.fixture
    def mock_response(self):
        """Mock player response data"""
        return {
            "id": "123",
            "firstName": "Test",
            "lastName": "Player",
            "fullName": "Test Player",
            "displayName": "Test Player",
            "shortName": "T. Player",
            "weight": 200,
            "height": 75,
            "age": 30,
            "bats": {"displayValue": "Right"},
            "throws": {"displayValue": "Right"},
            "active": True,
        }

    def test_hydrate_player_with_mocks(self, mock_players, mock_logger, mock_response):
        """Test that _hydrate_player works correctly with mocked data"""
        # Create core requests with mocked _get_player_data
        core_requests = EspnCoreRequests(sport="mlb", year=2025, logger=mock_logger)
        
        # Mock the _get_player_data method to return our mock_response
        core_requests._get_player_data = mock.MagicMock(return_value=mock_response)
        
        # Test with a single player
        player = mock_players[0]
        result_player, success = core_requests._hydrate_player(player)
        
        # Verify the result
        assert success is True
        assert result_player.displayName == "Test Player"
        assert result_player.bats == "Right"
        assert result_player.throws == "Right"
        
        # Verify _get_player_data was called correctly
        core_requests._get_player_data.assert_called_once_with(1)

    def test_hydrate_players_threading(self, mock_players, mock_logger, mock_response):
        """Test that hydrate_players uses multi-threading correctly"""
        # Create a core requests object with a mocked _get_player_data
        core_requests = EspnCoreRequests(
            sport="mlb", 
            year=2025, 
            logger=mock_logger,
            max_workers=4  # Use 4 threads for testing
        )
        
        # Mock the _get_player_data method
        core_requests._get_player_data = mock.MagicMock(return_value=mock_response)
        
        # Call hydrate_players with our mock players
        hydrated_players, failed_players = core_requests.hydrate_players(
            mock_players, 
            batch_size=5  # Use small batch size for testing
        )
        
        # Verify all players were hydrated
        assert len(hydrated_players) == 10
        assert len(failed_players) == 0
        
        # Verify each player was properly hydrated
        for player in hydrated_players:
            assert hasattr(player, "displayName")
            assert player.displayName == "Test Player"
            assert player.bats == "Right"
            assert player.throws == "Right"
        
        # Verify _get_player_data was called for each player
        assert core_requests._get_player_data.call_count == 10

    def test_hydrate_players_with_404_player(self, mock_players, mock_logger):
        """Test that 404 errors are handled correctly without retries"""
        # Create a core requests object
        core_requests = EspnCoreRequests(
            sport="mlb", 
            year=2025, 
            logger=mock_logger,
            max_workers=4
        )
        
        # Function to simulate API calls - returns None for player ID 5 (404 error)
        def mock_get_player_data(player_id):
            if player_id == 5:
                return None
            return {
                "id": str(player_id),
                "firstName": "Test",
                "lastName": f"Player {player_id}",
                "fullName": f"Test Player {player_id}",
                "displayName": f"Test Player {player_id}",
                "bats": {"displayValue": "Right"},
                "throws": {"displayValue": "Right"},
            }
        
        # Mock the _get_player_data method with our simulation function
        core_requests._get_player_data = mock.MagicMock(side_effect=mock_get_player_data)
        
        # Run the hydration
        hydrated_players, failed_players = core_requests.hydrate_players(
            mock_players,
            batch_size=5
        )
        
        # Verify 9 players were hydrated successfully and 1 failed
        assert len(hydrated_players) == 9
        assert len(failed_players) == 1
        assert failed_players[0].id == 5
        
        # Verify each successful player was properly hydrated
        for player in hydrated_players:
            assert hasattr(player, "displayName")
            assert player.bats == "Right"
            assert player.throws == "Right"
        
        # Verify _get_player_data was called once for each player (including the 404)
        assert core_requests._get_player_data.call_count == 10

    def test_hydrate_players_performance(self, mock_logger):
        """Test that multi-threading improves performance"""
        # Create a larger list of players for performance testing
        players = [Player({"id": i, "fullName": f"Player {i}"}) for i in range(1, 101)]
        
        # Function that simulates a slow API call (0.05 seconds per call)
        def slow_get_player_data(player_id):
            time.sleep(0.05)  # Simulate network delay
            return {
                "id": str(player_id),
                "firstName": "Test",
                "lastName": f"Player {player_id}",
                "fullName": f"Test Player {player_id}",
                "displayName": f"Test Player {player_id}",
                "bats": {"displayValue": "Right"},
                "throws": {"displayValue": "Right"},
            }
        
        # Test with single-threaded approach (max_workers=1)
        core_requests_single = EspnCoreRequests(
            sport="mlb", 
            year=2025, 
            logger=mock_logger,
            max_workers=1  # Single thread
        )
        core_requests_single._get_player_data = mock.MagicMock(side_effect=slow_get_player_data)
        
        start_time_single = time.time()
        hydrated_single, failed_single = core_requests_single.hydrate_players(
            players[:20],  # Use only first 20 players to keep test reasonable
            batch_size=100
        )
        single_thread_time = time.time() - start_time_single
        
        # Test with multi-threaded approach (max_workers=4)
        core_requests_multi = EspnCoreRequests(
            sport="mlb", 
            year=2025, 
            logger=mock_logger,
            max_workers=4  # Four threads
        )
        core_requests_multi._get_player_data = mock.MagicMock(side_effect=slow_get_player_data)
        
        start_time_multi = time.time()
        hydrated_multi, failed_multi = core_requests_multi.hydrate_players(
            players[:20],  # Use only first 20 players to keep test reasonable
            batch_size=100
        )
        multi_thread_time = time.time() - start_time_multi
        
        # Verify both approaches hydrated the same number of players successfully
        assert len(hydrated_single) == len(hydrated_multi) == 20
        assert len(failed_single) == len(failed_multi) == 0
        
        # Verify multi-threading is faster (should be ~4x faster with 4 threads)
        # Allow some flexibility due to test environment variations
        assert multi_thread_time < single_thread_time, \
            f"Multi-threading ({multi_thread_time:.2f}s) should be faster than single-threading ({single_thread_time:.2f}s)"
        
        # Log the times for debugging
        print(f"Single-threaded time: {single_thread_time:.2f}s")
        print(f"Multi-threaded time: {multi_thread_time:.2f}s")
        print(f"Speed improvement: {single_thread_time / multi_thread_time:.2f}x")
        
        # With 4 threads, should be at least 2x faster (not quite 4x due to overhead)
        assert single_thread_time / multi_thread_time > 2.0, \
            f"Expected at least 2x improvement, got {single_thread_time / multi_thread_time:.2f}x"

    def test_max_workers_configuration(self, mock_players, mock_logger, mock_response):
        """Test that max_workers is properly configured and used"""
        # Create a core requests object with a mocked ThreadPoolExecutor
        with mock.patch('espn_api_extractor.requests.core_requests.ThreadPoolExecutor') as mock_executor:
            # Setup mock executor to pass through to real executor
            mock_instance = mock.MagicMock()
            mock_executor.return_value.__enter__.return_value = ThreadPoolExecutor(max_workers=2)
            
            # Create core requests with different max_workers values
            core_requests_default = EspnCoreRequests(
                sport="mlb", 
                year=2025, 
                logger=mock_logger
            )
            
            core_requests_custom = EspnCoreRequests(
                sport="mlb", 
                year=2025, 
                logger=mock_logger,
                max_workers=10
            )
            
            # Mock the _get_player_data method
            core_requests_default._get_player_data = mock.MagicMock(return_value=mock_response)
            core_requests_custom._get_player_data = mock.MagicMock(return_value=mock_response)
            
            # Verify max_workers is correctly set
            assert core_requests_custom.max_workers == 10
            assert core_requests_default.max_workers is not None  # Should use default CPU-based value
            
            # Run hydration with custom max_workers
            core_requests_custom.hydrate_players(mock_players[:5], batch_size=5)
            
            # Check that ThreadPoolExecutor was called correctly
            mock_executor.assert_called_with(max_workers=10)