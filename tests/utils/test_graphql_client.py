import json
import os
import tempfile
import unittest.mock as mock
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError, ConnectTimeout

from espn_api_extractor.utils.graphql_client import GraphQLClient
from espn_api_extractor.utils.logger import Logger


class TestGraphQLClient:
    """Integration test suite for GraphQLClient class"""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing"""
        logger = Logger("test")
        logger.logging = mock.MagicMock()
        return logger

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing"""
        config_data = {
            "endpoint": "https://test-graphql.example.com/graphql",
            "headers": {"x-hasura-ddn-token": "test_token_123"},
            "timeout": 30,
            "retry_attempts": 3,
            "retry_delay": 1,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        yield temp_file

        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)

    @pytest.fixture
    def invalid_config_file(self):
        """Create a temporary invalid config file for testing"""
        invalid_config = {
            "headers": {"token": "test"},
            # Missing endpoint
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(invalid_config, f)
            temp_file = f.name

        yield temp_file

        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)

    def test_init_default(self, mock_logger):
        """Test GraphQLClient initialization with defaults"""
        client = GraphQLClient(logger=mock_logger)
        assert client.logger == mock_logger
        assert client.config_path == "hasura_config.json"
        assert client.endpoint is None
        assert client.headers == {}
        assert client.timeout == 30
        assert client.retry_attempts == 3
        assert client.retry_delay == 1
        assert client.is_available is False

    def test_init_custom_config_path(self, mock_logger):
        """Test GraphQLClient initialization with custom config path"""
        custom_path = "custom_config.json"
        client = GraphQLClient(config_path=custom_path, logger=mock_logger)
        assert client.config_path == custom_path

    def test_load_config_success(self, mock_logger, temp_config_file):
        """Test successful config loading"""
        client = GraphQLClient(config_path=temp_config_file, logger=mock_logger)
        result = client._load_config()

        assert result is True
        assert client.endpoint == "https://test-graphql.example.com/graphql"
        assert client.headers["x-hasura-ddn-token"] == "test_token_123"
        assert client.timeout == 30
        assert client.retry_attempts == 3
        assert client.retry_delay == 1

    def test_load_config_file_not_found(self, mock_logger):
        """Test config loading when file doesn't exist"""
        client = GraphQLClient(config_path="nonexistent.json", logger=mock_logger)
        result = client._load_config()

        assert result is False
        mock_logger.logging.warning.assert_called_with(
            "GraphQL config file not found: nonexistent.json"
        )

    def test_load_config_invalid_json(self, mock_logger):
        """Test config loading with invalid JSON"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name

        try:
            client = GraphQLClient(config_path=temp_file, logger=mock_logger)
            result = client._load_config()

            assert result is False
            mock_logger.logging.error.assert_called()
        finally:
            os.unlink(temp_file)

    def test_load_config_missing_endpoint(self, mock_logger, invalid_config_file):
        """Test config loading with missing endpoint"""
        client = GraphQLClient(config_path=invalid_config_file, logger=mock_logger)
        result = client._load_config()

        assert result is False
        mock_logger.logging.error.assert_called_with(
            "GraphQL endpoint not specified in config"
        )

    @patch("requests.Session.post")
    def test_connection_success(self, mock_post, mock_logger, temp_config_file):
        """Test successful GraphQL connection"""
        # Setup successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"__schema": {"types": [{"name": "Query"}]}}
        }
        mock_post.return_value = mock_response

        client = GraphQLClient(config_path=temp_config_file, logger=mock_logger)
        client._load_config()

        success, error = client._test_connection()

        assert success is True
        assert error is None
        mock_logger.logging.info.assert_called_with(
            "GraphQL connection test successful"
        )

    @patch("requests.Session.post")
    def test_connection_http_error(self, mock_post, mock_logger, temp_config_file):
        """Test GraphQL connection with HTTP error"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        client = GraphQLClient(config_path=temp_config_file, logger=mock_logger)
        client._load_config()

        success, error = client._test_connection()

        assert success is False
        assert error == "HTTP 500: Internal Server Error"

    @patch("requests.Session.post")
    def test_connection_graphql_error(self, mock_post, mock_logger, temp_config_file):
        """Test GraphQL connection with GraphQL error response"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errors": [{"message": "Schema not available"}]
        }
        mock_post.return_value = mock_response

        client = GraphQLClient(config_path=temp_config_file, logger=mock_logger)
        client._load_config()

        success, error = client._test_connection()

        assert success is False
        assert error == "GraphQL error: Schema not available"

    @patch("requests.Session.post")
    def test_connection_timeout(self, mock_post, mock_logger, temp_config_file):
        """Test GraphQL connection with timeout"""
        mock_post.side_effect = ConnectTimeout("Connection timeout")

        client = GraphQLClient(config_path=temp_config_file, logger=mock_logger)
        client._load_config()

        success, error = client._test_connection()

        assert success is False
        assert error == "Connection timeout to https://test-graphql.example.com/graphql"

    @patch("requests.Session.post")
    def test_connection_connection_error(
        self, mock_post, mock_logger, temp_config_file
    ):
        """Test GraphQL connection with connection error"""
        mock_post.side_effect = ConnectionError("Connection failed")

        client = GraphQLClient(config_path=temp_config_file, logger=mock_logger)
        client._load_config()

        success, error = client._test_connection()

        assert success is False
        assert error == "Connection failed to https://test-graphql.example.com/graphql"

    def test_connection_no_endpoint(self, mock_logger):
        """Test connection test with no endpoint configured"""
        client = GraphQLClient(logger=mock_logger)

        success, error = client._test_connection()

        assert success is False
        assert error == "No GraphQL endpoint configured"

    @patch("builtins.input")
    def test_prompt_user_abort(self, mock_input, mock_logger):
        """Test user prompt returning abort (default)"""
        mock_input.return_value = ""  # Default input (empty)

        client = GraphQLClient(logger=mock_logger)
        client.endpoint = "https://test.com/graphql"

        result = client._prompt_user_for_fallback("Connection failed")

        assert result is False

    @patch("builtins.input")
    def test_prompt_user_continue(self, mock_input, mock_logger):
        """Test user prompt returning continue"""
        mock_input.return_value = "y"

        client = GraphQLClient(logger=mock_logger)
        client.endpoint = "https://test.com/graphql"

        result = client._prompt_user_for_fallback("Connection failed")

        assert result is True

    @patch("builtins.input")
    def test_prompt_user_invalid_then_valid(self, mock_input, mock_logger):
        """Test user prompt with invalid input then valid"""
        mock_input.side_effect = ["invalid", "n"]

        client = GraphQLClient(logger=mock_logger)
        client.endpoint = "https://test.com/graphql"

        result = client._prompt_user_for_fallback("Connection failed")

        assert result is False
        assert mock_input.call_count == 2

    def test_initialize_force_full_extraction(self, mock_logger):
        """Test initialization with force_full_extraction=True"""
        client = GraphQLClient(logger=mock_logger)

        result = client.initialize_with_hitl(force_full_extraction=True)

        assert result is client
        assert client.is_available is False
        mock_logger.logging.info.assert_called_with(
            "Forcing full ESPN extraction (GraphQL bypassed)"
        )

    def test_initialize_no_config(self, mock_logger):
        """Test initialization when no config is available"""
        client = GraphQLClient(config_path="nonexistent.json", logger=mock_logger)

        result = client.initialize_with_hitl()

        assert result is client
        assert client.is_available is False

    @patch.object(GraphQLClient, "_test_connection")
    @patch.object(GraphQLClient, "_load_config")
    def test_initialize_connection_success(
        self, mock_load_config, mock_test_connection, mock_logger
    ):
        """Test initialization with successful connection"""
        mock_load_config.return_value = True
        mock_test_connection.return_value = (True, None)

        client = GraphQLClient(logger=mock_logger)

        result = client.initialize_with_hitl()

        assert result is client
        assert client.is_available is True

    @patch.object(GraphQLClient, "_prompt_user_for_fallback")
    @patch.object(GraphQLClient, "_test_connection")
    @patch.object(GraphQLClient, "_load_config")
    def test_initialize_connection_fail_user_continue(
        self, mock_load_config, mock_test_connection, mock_prompt, mock_logger
    ):
        """Test initialization with connection failure and user continues"""
        mock_load_config.return_value = True
        mock_test_connection.return_value = (False, "Connection timeout")
        mock_prompt.return_value = True

        client = GraphQLClient(logger=mock_logger)

        result = client.initialize_with_hitl()

        assert result is client
        assert client.is_available is False
        mock_prompt.assert_called_once_with("Connection timeout")

    @patch.object(GraphQLClient, "_prompt_user_for_fallback")
    @patch.object(GraphQLClient, "_test_connection")
    @patch.object(GraphQLClient, "_load_config")
    def test_initialize_connection_fail_user_abort(
        self, mock_load_config, mock_test_connection, mock_prompt, mock_logger
    ):
        """Test initialization with connection failure and user aborts"""
        mock_load_config.return_value = True
        mock_test_connection.return_value = (False, "Connection timeout")
        mock_prompt.return_value = False

        client = GraphQLClient(logger=mock_logger)

        with pytest.raises(SystemExit):
            client.initialize_with_hitl()

    @patch("requests.Session.post")
    def test_get_existing_player_ids_success(
        self, mock_post, mock_logger, temp_config_file
    ):
        """Test successful retrieval of existing player IDs"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "players": [{"espn_id": 12345}, {"espn_id": 67890}, {"espn_id": 11111}]
            }
        }
        mock_post.return_value = mock_response

        client = GraphQLClient(config_path=temp_config_file, logger=mock_logger)
        client._load_config()
        client.is_available = True

        player_ids = client.get_existing_player_ids()

        assert player_ids == {12345, 67890, 11111}
        mock_logger.logging.info.assert_called_with(
            "Retrieved 3 existing player IDs from GraphQL"
        )

    @patch("requests.Session.post")
    def test_get_existing_player_ids_http_error(
        self, mock_post, mock_logger, temp_config_file
    ):
        """Test player ID retrieval with HTTP error"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        client = GraphQLClient(config_path=temp_config_file, logger=mock_logger)
        client._load_config()
        client.is_available = True

        player_ids = client.get_existing_player_ids()

        assert player_ids == set()
        mock_logger.logging.error.assert_called_with("GraphQL query failed: HTTP 500")

    @patch("requests.Session.post")
    def test_get_existing_player_ids_graphql_error(
        self, mock_post, mock_logger, temp_config_file
    ):
        """Test player ID retrieval with GraphQL error"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errors": [{"message": "Query failed"}]}
        mock_post.return_value = mock_response

        client = GraphQLClient(config_path=temp_config_file, logger=mock_logger)
        client._load_config()
        client.is_available = True

        player_ids = client.get_existing_player_ids()

        assert player_ids == set()

    def test_get_existing_player_ids_not_available(self, mock_logger):
        """Test player ID retrieval when GraphQL not available"""
        client = GraphQLClient(logger=mock_logger)
        client.is_available = False

        player_ids = client.get_existing_player_ids()

        assert player_ids == set()

    @patch("requests.Session.post")
    def test_get_existing_player_ids_exception(
        self, mock_post, mock_logger, temp_config_file
    ):
        """Test player ID retrieval with exception"""
        mock_post.side_effect = Exception("Network error")

        client = GraphQLClient(config_path=temp_config_file, logger=mock_logger)
        client._load_config()
        client.is_available = True

        player_ids = client.get_existing_player_ids()

        assert player_ids == set()
        mock_logger.logging.error.assert_called_with(
            "Failed to query existing players: Network error"
        )


class TestGraphQLClientIntegration:
    """Integration tests that test GraphQLClient with real Hasura configuration"""

    @pytest.fixture
    def hasura_config_path(self):
        """Use the actual hasura_config.json file in the project root"""
        config_path = "/Users/Shared/BaseballHQ/tools/_extract/ESPN_API_Extractor/hasura_config.json"
        if not os.path.exists(config_path):
            pytest.skip(f"Real Hasura config not found at {config_path}")
        return config_path

    @pytest.mark.integration
    def test_real_hasura_connection(self, hasura_config_path):
        """Integration test with real Hasura DDN endpoint"""
        logger = Logger("integration-test")
        client = GraphQLClient(config_path=hasura_config_path, logger=logger)

        # Load the actual config
        config_loaded = client._load_config()
        assert config_loaded is True

        # Verify we loaded the expected endpoint
        assert "communal-stork-9800.ddn.hasura.app" in client.endpoint
        assert "x-hasura-ddn-token" in client.headers

        # Test connection to real endpoint
        success, error = client._test_connection()

        # Log results for manual verification
        if success:
            print("✅ Real Hasura connection successful")
            print(f"   Endpoint: {client.endpoint}")
        else:
            print(f"❌ Real Hasura connection failed: {error}")
            print(f"   Endpoint: {client.endpoint}")

        # Note: Don't assert success since external services can be down
        # This test is for manual verification and integration validation

    @pytest.mark.integration
    def test_real_player_query(self, hasura_config_path):
        """Integration test that attempts to query real player data"""
        logger = Logger("integration-test")
        client = GraphQLClient(config_path=hasura_config_path, logger=logger)

        # Initialize client
        client._load_config()

        # Only proceed if connection works
        success, error = client._test_connection()
        if not success:
            pytest.skip(f"Hasura connection failed: {error}")

        # Mark as available and try to query players
        client.is_available = True
        player_ids = client.get_existing_player_ids()

        print(f"Found {len(player_ids)} existing players in Hasura")
        if player_ids:
            print(f"Sample player IDs: {list(player_ids)[:5]}")

        # Test should pass regardless of whether players exist
        assert isinstance(player_ids, set)

    @pytest.mark.integration
    def test_full_initialization_flow(self, hasura_config_path):
        """Test the complete initialization flow with real config"""
        logger = Logger("integration-test")
        client = GraphQLClient(config_path=hasura_config_path, logger=logger)

        # Mock user input to avoid interactive prompts in tests
        with patch.object(client, "_prompt_user_for_fallback", return_value=True):
            try:
                result = client.initialize_with_hitl()
                print(f"Initialization result: {result}")
                print(f"Client available: {client.is_available}")
            except SystemExit as e:
                print(f"Initialization aborted: {e}")
                # This is acceptable behavior when user chooses to abort

        # Test doesn't assert specific outcome since it depends on external service

    @pytest.mark.integration
    def test_schema_introspection(self, hasura_config_path):
        """Test that we can introspect the Hasura schema"""
        logger = Logger("integration-test")
        client = GraphQLClient(config_path=hasura_config_path, logger=logger)

        if not client._load_config():
            pytest.skip("Could not load Hasura config")

        # Custom query to get schema info
        introspection_query = """
        query IntrospectionQuery {
            __schema {
                types {
                    name
                    kind
                }
            }
        }
        """

        try:
            import requests

            response = requests.post(
                client.endpoint,
                json={"query": introspection_query},
                headers=client.headers,
                timeout=client.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                if "data" in data and "__schema" in data["data"]:
                    types = data["data"]["__schema"]["types"]
                    type_names = [
                        t["name"] for t in types if not t["name"].startswith("__")
                    ]
                    print(f"Found {len(type_names)} schema types")
                    print(f"Sample types: {type_names[:10]}")

                    # Look for player-related types
                    player_types = [t for t in type_names if "player" in t.lower()]
                    print(f"Player-related types: {player_types}")
                else:
                    print(f"Schema introspection failed: {data}")
            else:
                print(f"HTTP {response.status_code}: {response.text}")

        except Exception as e:
            print(f"Schema introspection error: {e}")
            # Don't fail test since this is exploratory
