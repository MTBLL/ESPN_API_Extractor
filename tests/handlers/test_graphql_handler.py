import json
import os
from unittest.mock import MagicMock

from espn_api_extractor.handlers.graphql_handler import GraphQLHandler
from espn_api_extractor.requests.graphql_requests import GraphQLClient


def _load_graphql_fixture() -> dict:
    fixture_path = os.path.join(
        os.path.dirname(__file__), "..", "fixtures", "graphql_players_response.json"
    )
    with open(fixture_path, "r") as fixture_file:
        return json.load(fixture_file)


def test_get_existing_players_returns_empty_when_unavailable():
    client = MagicMock(spec=GraphQLClient)
    client.is_available = False
    client.initialize_with_hitl.return_value = client

    handler = GraphQLHandler(client=client)

    players = handler.get_existing_players()

    assert players == []
    client.fetch.assert_not_called()


def test_get_existing_players_parses_graphql_response():
    fixture = _load_graphql_fixture()

    client = MagicMock(spec=GraphQLClient)
    client.is_available = True
    client.initialize_with_hitl.return_value = client
    client.fetch.return_value = fixture["data"]

    handler = GraphQLHandler(client=client)

    players = handler.get_existing_players()

    assert len(players) == 3
    assert players[0].id == 12345
    assert players[0].slug == "test-player-1"
    assert players[0].jersey == "24"
    assert players[0].eligible_slots == ["1B", "UTIL"]
