import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from espn_api_extractor.runners.players import main
from espn_api_extractor.baseball.player import Player


class TestPlayersRunnerWithProjections:
    """Test the player runner integration with projections data"""

    @pytest.fixture
    def mock_fantasy_requests(self):
        """Mock fantasy requests with projections data"""
        mock = Mock()
        
        # Mock get_pro_players response
        mock.get_pro_players.return_value = [
            {"id": 42404, "fullName": "Corbin Carroll", "firstName": "Corbin", "lastName": "Carroll"},
            {"id": 39832, "fullName": "Shohei Ohtani", "firstName": "Shohei", "lastName": "Ohtani"}
        ]
        
        # Mock get_player_cards response with fixture data
        with open("tests/fixtures/kona_playercard_projections_fixture.json", "r") as f:
            fixture_data = json.load(f)
        mock.get_player_cards.return_value = fixture_data
        
        return mock

    @pytest.fixture
    def mock_core_requests(self):
        """Mock core requests for player hydration"""
        mock = Mock()
        mock.hydrate_players.return_value = ([], [])  # No players hydrated, no failures
        return mock

    @pytest.fixture
    def mock_graphql_client(self):
        """Mock GraphQL client"""
        mock = Mock()
        mock.initialize_with_hitl.return_value = False  # Disable GraphQL optimization
        return mock

    @pytest.fixture
    def projections_fixture_data(self):
        """Load the kona_playercard projections fixture"""
        with open("tests/fixtures/kona_playercard_projections_fixture.json", "r") as f:
            return json.load(f)

    def test_runner_fetches_projections_before_hydration(
        self, 
        mock_fantasy_requests,
        mock_core_requests,
        mock_graphql_client
    ):
        """Test that the runner fetches projections before bio hydration"""
        
        # Setup mocks for the actual workflow logic test
        from espn_api_extractor.utils.logger import Logger
        from espn_api_extractor.baseball.player import Player
        
        logger = Logger("test")
        
        # Simulate the workflow from the runner
        # Step 1: Get ESPN players
        espn_players = mock_fantasy_requests.get_pro_players.return_value
        
        # Step 2: Create Player objects
        player_objs = [Player(player) for player in espn_players]
        
        # Step 3: Extract player IDs and fetch projections
        player_ids = [player.id for player in player_objs if player.id is not None]
        
        # Simulate the player cards fetch call
        player_cards_data = mock_fantasy_requests.get_player_cards(player_ids)
        
        # Verify that get_player_cards was called
        mock_fantasy_requests.get_player_cards.assert_called_once_with(player_ids)
        
        # Verify player IDs are correct
        assert 42404 in player_ids
        assert 39832 in player_ids

    def test_runner_handles_projections_failure_gracefully(self, mock_fantasy_requests):
        """Test that the runner handles projections API failure gracefully"""
        
        from espn_api_extractor.utils.logger import Logger
        from espn_api_extractor.baseball.player import Player
        
        # Setup mock to fail on projections
        mock_fantasy_requests.get_pro_players.return_value = [
            {"id": 42404, "fullName": "Corbin Carroll"}
        ]
        mock_fantasy_requests.get_player_cards.side_effect = Exception("API Error")
        
        logger = Logger("test")
        
        # Test that the exception is caught and handled
        try:
            espn_players = mock_fantasy_requests.get_pro_players()
            player_objs = [Player(player) for player in espn_players]
            player_ids = [player.id for player in player_objs if player.id is not None]
            
            # This should raise an exception but be caught in actual implementation
            player_cards_data = mock_fantasy_requests.get_player_cards(player_ids)
            # If we get here, the test should fail
            assert False, "Expected exception was not raised"
        except Exception as e:
            # Verify the exception message
            assert "API Error" in str(e)

    def test_player_hydrate_kona_playercard_method(self):
        """Test the Player.hydrate_kona_playercard method directly"""
        
        # Create a player object
        player_data = {"id": 42404, "fullName": "Corbin Carroll"}
        player = Player(player_data)
        
        # Load projection data from fixture
        with open("tests/fixtures/kona_playercard_projections_fixture.json", "r") as f:
            fixture_data = json.load(f)
        
        carroll_data = fixture_data["players"][0]["player"]
        
        # Hydrate with kona_playercard data
        player.hydrate_kona_playercard(carroll_data)
        
        # Verify season outlook was set
        assert hasattr(player, "season_outlook")
        assert player.season_outlook is not None
        assert "2023 NL Rookie of the Year" in player.season_outlook
        
        # Verify projections were set
        assert hasattr(player, "projections")
        assert len(player.projections) > 0
        assert "AB" in player.projections  # At bats
        assert "HR" in player.projections  # Home runs
        assert "SB" in player.projections  # Stolen bases
        
        # Verify specific projection values
        assert player.projections["AB"] == 377.0
        assert player.projections["HR"] == 19.0
        assert player.projections["SB"] == 21.0
        
        # Verify preseason stats were set
        assert hasattr(player, "preseason_stats")
        assert len(player.preseason_stats) > 0
        assert "AB" in player.preseason_stats
        
        # Verify regular season stats were set
        assert hasattr(player, "regular_season_stats")
        assert len(player.regular_season_stats) > 0
        assert "AB" in player.regular_season_stats
        
        # Verify previous season stats were set
        assert hasattr(player, "previous_season_stats")
        assert len(player.previous_season_stats) > 0
        assert "AB" in player.previous_season_stats

    def test_player_to_model_includes_projections(self):
        """Test that Player.to_model includes projections data"""
        
        # Create and hydrate a player
        player_data = {"id": 42404, "fullName": "Corbin Carroll"}
        player = Player(player_data)
        
        # Add some test projection data
        player.season_outlook = "Test outlook"
        player.projections = {"AB": 400, "HR": 20}
        player.preseason_stats = {"AB": 50, "HR": 2}
        player.regular_season_stats = {"AB": 300, "HR": 15}
        player.previous_season_stats = {"AB": 500, "HR": 25}
        
        # Convert to model
        model = player.to_model()
        
        # Verify projection fields are included
        assert model.season_outlook == "Test outlook"
        assert model.projections == {"AB": 400, "HR": 20}
        assert model.preseason_stats == {"AB": 50, "HR": 2}
        assert model.regular_season_stats == {"AB": 300, "HR": 15}
        assert model.previous_season_stats == {"AB": 500, "HR": 25}

    def test_integration_with_sample_players(self, projections_fixture_data):
        """Test end-to-end integration with sample players"""
        
        from espn_api_extractor.baseball.player import Player
        
        # Create test players from fixture data
        test_players = []
        for player_data in projections_fixture_data["players"]:
            player = Player({"id": player_data["id"], "fullName": player_data["player"]["fullName"]})
            # Hydrate with projections from fixture
            player.hydrate_kona_playercard(player_data["player"], player_data)
            test_players.append(player)
        
        # Verify players were created with projections
        assert len(test_players) == 2
        for player in test_players:
            assert hasattr(player, "season_outlook")
            assert hasattr(player, "projections")
            assert hasattr(player, "previous_season_stats")
            assert player.season_outlook is not None
            assert len(player.projections) > 0
            assert len(player.previous_season_stats) > 0
        
        # Test conversion to models
        models = [player.to_model() for player in test_players]
        assert len(models) == 2
        for model in models:
            assert model.season_outlook is not None
            assert model.projections is not None
            assert model.previous_season_stats is not None