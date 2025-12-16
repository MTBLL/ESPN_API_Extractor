import os
import unittest.mock as mock

import pytest
from requests.exceptions import ConnectionError, Timeout

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
        """Create an EspnCoreRequests instance for testing with mocked logger"""
        requests = EspnCoreRequests(sport="mlb", year=2025)
        requests.logger = mock_logger
        return requests

    def test_init_with_valid_sport(self):
        """Test initialization with valid sport"""
        # Test with MLB (only MLB is currently supported according to constant.py)
        mlb_requests = EspnCoreRequests(sport="mlb", year=2025)
        cpu_count = os.cpu_count() or 1
        assert mlb_requests.sport == "mlb"
        assert mlb_requests.year == 2025
        assert mlb_requests.logger is not None
        assert os.cpu_count() is not None
        assert mlb_requests.max_workers == min(32, cpu_count * 4)

        # Test with custom max_workers
        custom_requests = EspnCoreRequests(sport="mlb", year=2025, max_workers=10)
        assert custom_requests.max_workers == 10

    def test_init_with_invalid_sport(self):
        """Test initialization with invalid sport"""
        with pytest.raises(SystemExit):
            EspnCoreRequests(sport="invalid", year=2025)

    def test_check_request_status(self, core_requests):
        """Test _check_request_status method with different status codes"""
        # Test with 200 status code
        result = core_requests._check_request_status(200, extend="test/endpoint")
        assert result is None
        core_requests.logger.logging.warning.assert_not_called()

        # Test with 404 status code
        result = core_requests._check_request_status(404, extend="test/endpoint")
        assert result is None
        # core_requests.logger.logging.warning.assert_called_with(
        #     "Endpoint not found: test/endpoint"
        # )

        # Test with 429 status code
        core_requests.logger.logging.warning.reset_mock()
        result = core_requests._check_request_status(429, extend="test/endpoint")
        assert result is None
        core_requests.logger.logging.warning.assert_called_with("Rate limit exceeded")

        # Test with 500 status code
        core_requests.logger.logging.warning.reset_mock()
        result = core_requests._check_request_status(500, extend="test/endpoint")
        assert result is None
        core_requests.logger.logging.warning.assert_called_with("Internal server error")

        # Test with 503 status code
        core_requests.logger.logging.warning.reset_mock()
        result = core_requests._check_request_status(503, extend="test/endpoint")
        assert result is None
        core_requests.logger.logging.warning.assert_called_with("Service unavailable")

        # Test with other status code
        core_requests.logger.logging.warning.reset_mock()
        result = core_requests._check_request_status(418, extend="test/endpoint")
        assert result is None
        core_requests.logger.logging.warning.assert_called_with("Unknown error: 418")

    @mock.patch("requests.get")
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
            extend="/test/endpoint",
        )

        # Verify request was made correctly
        mock_get.assert_called_with(
            core_requests.sport_endpoint + "/test/endpoint",
            params={"param1": "value1"},
            headers={"header1": "value1"},
            cookies=core_requests.session.cookies,
        )

        # Verify log_request was called correctly
        core_requests.logger.log_request.assert_called_with(
            endpoint=core_requests.sport_endpoint + "/test/endpoint",
            params={"param1": "value1"},
            headers={"header1": "value1"},
            response={"test": "data"},
        )

        # Verify result
        assert result == {"test": "data"}

    @mock.patch("requests.get")
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
            timeout=10,
        )

        # Verify result
        assert result == {"player": "data"}

    @mock.patch("requests.get")
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
        core_requests.logger.logging.warning.assert_any_call(
            "Player ID 12345 not found (404) - skipping retries"
        )

    @mock.patch("requests.get")
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
        with mock.patch("time.sleep") as mock_sleep:
            # Test _get_player_data method
            result = core_requests._get_player_data(player_id=12345)

        # Verify request was made correctly twice
        assert mock_get.call_count == 2

        # Verify sleep was called once with correct backoff
        mock_sleep.assert_called_once_with(1)

        # Verify result contains data from second call
        assert result == {"player": "data_after_retry"}

    @mock.patch("requests.get")
    def test_get_player_data_exception(self, mock_get, core_requests):
        """Test _get_player_data method with exceptions"""
        # Setup mock to raise exceptions
        mock_get.side_effect = [
            Timeout("Connection timed out"),
            ConnectionError("Connection error"),
            ValueError("Invalid response"),
        ]

        # Mock sleep to avoid waiting during test
        with mock.patch("time.sleep"):
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

    def test_hydrate_player_with_bio_without_id(self, core_requests):
        """Test _hydrate_player_with_bio with a player missing ID"""
        player = Player({"fullName": "Test Player"})  # No ID provided

        # Should raise an assertion error
        with pytest.raises(AssertionError):
            core_requests._hydrate_player_with_bio(player)

    def test_hydrate_player_with_bio_hydration_exception(self, core_requests):
        """Test _hydrate_player_with_bio method with exception during hydration"""
        # Create a player with valid ID
        player = Player({"id": 123, "fullName": "Test Player"})

        # Mock _get_player_data to return data
        core_requests._get_player_data = mock.MagicMock(return_value={"id": "123"})

        # Mock player.hydrate to raise an exception
        original_hydrate = Player.hydrate_bio
        Player.hydrate_bio = mock.MagicMock(side_effect=ValueError("Test error"))

        try:
            # Call _hydrate_player_with_bio
            result_player, success = core_requests._hydrate_player_with_bio(player)

            # Verify results
            assert result_player is player
            assert success is False
            core_requests.logger.logging.error.assert_called_with(
                "Error hydrating player 123 with biographical data: Test error"
            )
        finally:
            # Restore original method
            Player.hydrate_bio = original_hydrate

    def test_hydrate_player_worker_bio_only(self, core_requests):
        """Test _hydrate_player_worker with include_stats=False (bio only)"""
        # Create a player with valid ID
        player = Player({"id": 123, "fullName": "Test Player"})

        # Mock _hydrate_player_with_bio to return success
        core_requests._hydrate_player_with_bio = mock.MagicMock(
            return_value=(player, True)
        )
        core_requests._hydrate_player_with_stats = mock.MagicMock()

        # Call _hydrate_player_worker with include_stats=False
        result_player, success = core_requests._hydrate_player_worker(
            player, include_stats=False
        )

        # Verify results
        assert result_player is player
        assert success is True

        # Verify _hydrate_player_with_bio was called
        core_requests._hydrate_player_with_bio.assert_called_once_with(player)

        # Verify _hydrate_player_with_stats was NOT called
        core_requests._hydrate_player_with_stats.assert_not_called()

    def test_hydrate_player_worker_bio_and_stats_success(self, core_requests):
        """Test _hydrate_player_worker with include_stats=True (both bio and stats)"""
        # Create a player with valid ID
        player = Player({"id": 123, "fullName": "Test Player"})
        hydrated_player = Player(
            {"id": 123, "fullName": "Test Player", "display_name": "Test Player"}
        )

        # Mock both methods to return success
        core_requests._hydrate_player_with_bio = mock.MagicMock(
            return_value=(hydrated_player, True)
        )
        core_requests._hydrate_player_with_stats = mock.MagicMock(
            return_value=(hydrated_player, True)
        )

        # Call _hydrate_player_worker with include_stats=True
        result_player, success = core_requests._hydrate_player_worker(
            player, include_stats=True
        )

        # Verify results
        assert result_player is hydrated_player
        assert success is True

        # Verify both methods were called in correct order
        core_requests._hydrate_player_with_bio.assert_called_once_with(player)
        core_requests._hydrate_player_with_stats.assert_called_once_with(
            hydrated_player
        )

    def test_hydrate_player_worker_bio_fails(self, core_requests):
        """Test _hydrate_player_worker when bio hydration fails"""
        # Create a player with valid ID
        player = Player({"id": 123, "fullName": "Test Player"})

        # Mock _hydrate_player_with_bio to return failure
        core_requests._hydrate_player_with_bio = mock.MagicMock(
            return_value=(player, False)
        )
        core_requests._hydrate_player_with_stats = mock.MagicMock()

        # Call _hydrate_player_worker with include_stats=True
        result_player, success = core_requests._hydrate_player_worker(
            player, include_stats=True
        )

        # Verify results
        assert result_player is player
        assert success is False

        # Verify _hydrate_player_with_bio was called
        core_requests._hydrate_player_with_bio.assert_called_once_with(player)

        # Verify _hydrate_player_with_stats was NOT called (since bio failed)
        core_requests._hydrate_player_with_stats.assert_not_called()

    def test_hydrate_player_worker_bio_succeeds_stats_fails(self, core_requests):
        """Test _hydrate_player_worker when bio succeeds but stats fails

        Note: Stats hydration is best-effort. Even if stats fail, the player
        is still considered successfully hydrated (for prospects/injured players
        who have projections but no season stats).
        """
        # Create a player with valid ID
        player = Player({"id": 123, "fullName": "Test Player"})
        hydrated_player = Player(
            {"id": 123, "fullName": "Test Player", "display_name": "Test Player"}
        )

        # Mock bio to succeed, stats to fail
        core_requests._hydrate_player_with_bio = mock.MagicMock(
            return_value=(hydrated_player, True)
        )
        core_requests._hydrate_player_with_stats = mock.MagicMock(
            return_value=(hydrated_player, False)
        )

        # Call _hydrate_player_worker with include_stats=True
        result_player, success = core_requests._hydrate_player_worker(
            player, include_stats=True
        )

        # Verify results - should return the hydrated player with success=True
        # because bio succeeded (stats are best-effort)
        assert result_player is hydrated_player
        assert success is True

        # Verify both methods were called
        core_requests._hydrate_player_with_bio.assert_called_once_with(player)
        core_requests._hydrate_player_with_stats.assert_called_once_with(
            hydrated_player
        )

    def test_hydrate_players_with_include_stats_false(self, core_requests):
        """Test hydrate_players method with include_stats=False"""
        # Create test players
        players = [
            Player({"id": 1, "fullName": "Player 1"}),
            Player({"id": 2, "fullName": "Player 2"}),
        ]

        # Mock _hydrate_player_worker to return success for both players
        def mock_worker(player, include_stats):
            assert include_stats is False  # Verify the parameter is passed correctly
            return player, True

        core_requests._hydrate_player_worker = mock.MagicMock(side_effect=mock_worker)

        # Call hydrate_players with include_stats=False (default)
        hydrated_players, failed_players = core_requests.hydrate_players(
            players, batch_size=5
        )

        # Verify results
        assert len(hydrated_players) == 2
        assert len(failed_players) == 0

        # Verify _hydrate_player_worker was called correctly for each player
        assert core_requests._hydrate_player_worker.call_count == 2

        # Verify each call had include_stats=False
        for call in core_requests._hydrate_player_worker.call_args_list:
            args, kwargs = call
            player_arg, include_stats_arg = args
            assert include_stats_arg is False

    def test_hydrate_players_with_include_stats_true(self, core_requests):
        """Test hydrate_players method with include_stats=True"""
        # Create test players
        players = [
            Player({"id": 1, "fullName": "Player 1"}),
            Player({"id": 2, "fullName": "Player 2"}),
        ]

        # Mock _hydrate_player_worker to return success for both players
        def mock_worker(player, include_stats):
            assert include_stats is True  # Verify the parameter is passed correctly
            return player, True

        core_requests._hydrate_player_worker = mock.MagicMock(side_effect=mock_worker)

        # Call hydrate_players with include_stats=True
        hydrated_players, failed_players = core_requests.hydrate_players(
            players, batch_size=5, include_stats=True
        )

        # Verify results
        assert len(hydrated_players) == 2
        assert len(failed_players) == 0

        # Verify _hydrate_player_worker was called correctly for each player
        assert core_requests._hydrate_player_worker.call_count == 2

        # Verify each call had include_stats=True
        for call in core_requests._hydrate_player_worker.call_args_list:
            args, kwargs = call
            player_arg, include_stats_arg = args
            assert include_stats_arg is True


class TestCoreRequestsIntegration:
    """Integration tests that make real calls to ESPN API"""

    @pytest.fixture
    def real_logger(self):
        """Create a real logger for integration testing"""
        return Logger("integration-test")

    @pytest.fixture
    def real_core_requests(self):
        """Create an EspnCoreRequests instance with real configuration"""
        return EspnCoreRequests(sport="mlb", year=2025, max_workers=2)

    @pytest.mark.integration
    def test_real_player_data_fetch(self, real_core_requests):
        """Integration test that fetches real player data from ESPN API"""
        # Use a well-known MLB player ID (Shohei Ohtani)
        # These IDs are stable and unlikely to change
        known_player_ids = [
            32082,  # Sonny Gray (from our debug data)
            32159,  # Brandon Nimmo (from our debug data)
            33089,  # Luis Garcia (from our debug data)
        ]

        successful_fetches = 0
        for player_id in known_player_ids:
            print(f"\n🔍 Testing player ID: {player_id}")

            # Test biographical data fetch
            bio_data = real_core_requests._get_player_data(player_id)

            if bio_data is not None:
                successful_fetches += 1
                print(f"✅ Successfully fetched bio data for player {player_id}")

                # Verify basic structure
                assert isinstance(bio_data, dict)

                # Check for expected fields in ESPN player data
                if "$ref" in bio_data:
                    print(f"   Player reference: {bio_data['$ref']}")
                elif "athlete" in bio_data:
                    athlete = bio_data["athlete"]
                    if "displayName" in athlete:
                        print(f"   Player name: {athlete['displayName']}")
                    if "position" in athlete:
                        print(f"   Position: {athlete['position']['name']}")

                # Test statistics data fetch
                stats_data = real_core_requests._fetch_player_stats(player_id)
                if stats_data is not None:
                    print(f"✅ Successfully fetched stats data for player {player_id}")
                    assert isinstance(stats_data, dict)

                    # Check for expected stats structure
                    if "statistics" in stats_data:
                        print("   Found statistics data")
                    elif "splits" in stats_data:
                        print("   Found splits data")
                else:
                    print(f"⚠️  No stats data available for player {player_id}")
            else:
                print(f"❌ Failed to fetch data for player {player_id}")

        # At least one fetch should succeed for this test to be meaningful
        assert successful_fetches > 0, (
            f"No successful fetches out of {len(known_player_ids)} attempts"
        )
        print(
            f"\n📊 Summary: {successful_fetches}/{len(known_player_ids)} players fetched successfully"
        )

    @pytest.mark.integration
    def test_real_player_hydration(self, real_core_requests):
        """Integration test that hydrates real players with ESPN data"""
        # Create Player objects with known IDs
        test_players = [
            Player({"id": 32082, "fullName": "Sonny Gray"}),
            Player({"id": 32159, "fullName": "Brandon Nimmo"}),
        ]

        print(f"\n🔧 Testing hydration of {len(test_players)} players")

        # Test bio-only hydration
        hydrated_bio, failed_bio = real_core_requests.hydrate_players(
            test_players.copy(), batch_size=2, include_stats=False
        )

        print(
            f"✅ Bio hydration: {len(hydrated_bio)} successful, {len(failed_bio)} failed"
        )

        # Verify bio hydration results
        for player in hydrated_bio:
            assert hasattr(player, "id")
            print(
                f"   Bio hydrated: {player.id} - {getattr(player, 'display_name', 'Name not loaded')}"
            )

        # Test full hydration (bio + stats)
        hydrated_full, failed_full = real_core_requests.hydrate_players(
            test_players.copy(), batch_size=2, include_stats=True
        )

        print(
            f"✅ Full hydration: {len(hydrated_full)} successful, {len(failed_full)} failed"
        )

        # Verify full hydration results
        for player in hydrated_full:
            assert hasattr(player, "id")
            player_name = getattr(player, "display_name", "Name not loaded")
            has_stats = (
                hasattr(player, "season_stats") and player.season_stats is not None
            )
            print(f"   Full hydrated: {player.id} - {player_name} (stats: {has_stats})")

        # At least some hydrations should succeed
        total_successful = len(hydrated_bio) + len(hydrated_full)
        assert total_successful > 0, "No players were successfully hydrated"

    @pytest.mark.integration
    def test_real_api_endpoints(self, real_core_requests):
        """Integration test that validates ESPN API endpoint accessibility"""
        print("\n🌐 Testing ESPN API endpoints")
        print(f"   Base endpoint: {real_core_requests.sport_endpoint}")

        # Test the base endpoint accessibility
        try:
            # Try a simple request to verify the API is accessible
            import requests

            response = requests.get(
                real_core_requests.sport_endpoint,
                headers=real_core_requests.session.headers,
                timeout=10,
            )
            print(f"   Base endpoint status: {response.status_code}")

            # ESPN API typically returns 200 even for base endpoints
            assert response.status_code in [200, 404], (
                f"Unexpected status code: {response.status_code}"
            )

        except requests.exceptions.RequestException as e:
            print(f"   Connection error: {e}")
            pytest.skip(f"ESPN API not accessible: {e}")

        # Test specific player endpoint format
        test_player_endpoint = f"{real_core_requests.sport_endpoint}/athletes/32082"
        try:
            response = requests.get(
                test_player_endpoint,
                headers=real_core_requests.session.headers,
                timeout=10,
            )
            print(f"   Player endpoint status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict)
                print("   Player endpoint accessible and returning valid JSON")
            else:
                print(f"   Player endpoint returned: {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"   Player endpoint error: {e}")

    @pytest.mark.integration
    def test_error_handling_with_real_api(self, real_core_requests):
        """Integration test that verifies error handling with real API responses"""
        print("\n🔧 Testing error handling with real API")

        # Test with an invalid/non-existent player ID
        invalid_player_id = 999999999
        print(f"   Testing invalid player ID: {invalid_player_id}")

        bio_data = real_core_requests._get_player_data(invalid_player_id)
        assert bio_data is None, "Expected None for invalid player ID"
        print("   ✅ Correctly handled invalid player ID")

        # Test stats for invalid player
        stats_data = real_core_requests._fetch_player_stats(invalid_player_id)
        assert stats_data is None, "Expected None for invalid player stats"
        print("   ✅ Correctly handled invalid player stats")

        # Test hydration with invalid player
        invalid_player = Player({"id": invalid_player_id, "fullName": "Invalid Player"})
        hydrated, failed = real_core_requests.hydrate_players(
            [invalid_player], include_stats=True
        )

        # Should fail gracefully
        assert len(failed) == 1, "Expected 1 failed player"
        assert len(hydrated) == 0, "Expected 0 successful hydrations"
        print("   ✅ Correctly handled invalid player hydration")

    @pytest.mark.integration
    def test_concurrent_requests(self, real_core_requests):
        """Integration test that verifies multi-threading works with real API"""
        print("\n🧵 Testing concurrent requests to real API")

        # Create multiple players to test concurrency
        test_players = [
            Player({"id": 32082, "fullName": "Player 1"}),
            Player({"id": 32159, "fullName": "Player 2"}),
            Player({"id": 33089, "fullName": "Player 3"}),
        ]

        print(
            f"   Testing with {len(test_players)} players and {real_core_requests.max_workers} workers"
        )

        # Measure time for concurrent hydration
        import time

        start_time = time.time()

        hydrated, failed = real_core_requests.hydrate_players(
            test_players, batch_size=5, include_stats=True
        )

        end_time = time.time()
        duration = end_time - start_time

        print(f"   ⏱️  Hydration completed in {duration:.2f} seconds")
        print(f"   📊 Results: {len(hydrated)} successful, {len(failed)} failed")

        # Verify that multi-threading didn't cause data corruption
        for player in hydrated:
            assert hasattr(player, "id")
            assert player.id is not None
            print(f"   ✅ Player {player.id} properly hydrated")

        total_processed = len(hydrated) + len(failed)
        assert total_processed == len(test_players), "Not all players were processed"
