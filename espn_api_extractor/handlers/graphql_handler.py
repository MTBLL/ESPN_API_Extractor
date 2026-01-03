import json
from typing import List, Optional

from espn_api_extractor.models.player_model import PlayerModel
from espn_api_extractor.requests.graphql_requests import GraphQLClient
from espn_api_extractor.utils.logger import Logger


class GraphQLHandler:
    """Fetch and deserialize GraphQL player data for extraction optimization."""

    def __init__(
        self,
        config_path: str = "hasura_config.json",
        force_full_extraction: bool = False,
        client: Optional[GraphQLClient] = None,
    ):
        """Initialize handler with GraphQL client configuration."""
        self.client = client or GraphQLClient(config_path=config_path)
        self.force_full_extraction = force_full_extraction
        self.logger = Logger("GraphQLHandler").logging

    def get_existing_players(self) -> List[PlayerModel]:
        """Return existing players from GraphQL as PlayerModel instances."""
        self.client.initialize_with_hitl(self.force_full_extraction)

        if not self.client.is_available:
            self.logger.info("GraphQL not available, returning empty player list")
            return []

        query = """
        query GetExistingPlayers {
          players {
            active
            bats
            birthPlace
            dateOfBirth
            debutYear
            displayHeight
            displayName
            displayWeight
            eligibleSlots
            fangraphsApiRoute
            firstName
            headshot
            height
            idEspn
            idFangraphs
            idXmlbam
            injured
            injuryStatus
            jersey
            lastName
            name
            nameAscii
            nameNonascii
            nickname
            primaryPosition
            proTeam
            shortName
            slugEspn
            slugFangraphs
            status
            throws
            weight
          }
        }
        """

        data = self.client.fetch(query)
        if not data or "players" not in data:
            self.logger.error("Unexpected GraphQL response for players query")
            return []

        players_data = data["players"]
        players = []
        for player_data in players_data:
            try:
                if "idEspn" in player_data:
                    player_data["id"] = player_data.pop("idEspn")
                if "slugEspn" in player_data:
                    player_data["slug"] = player_data.pop("slugEspn")

                if isinstance(player_data.get("jersey"), int):
                    player_data["jersey"] = str(player_data["jersey"])

                if isinstance(player_data.get("eligibleSlots"), str):
                    try:
                        player_data["eligibleSlots"] = json.loads(
                            player_data["eligibleSlots"]
                        )
                    except json.JSONDecodeError:
                        player_data["eligibleSlots"] = []

                player_model = PlayerModel(**player_data)
                players.append(player_model)
            except Exception as e:
                self.logger.warning(
                    "Failed to deserialize player %s: %s",
                    player_data.get("id", "unknown"),
                    str(e),
                )
                continue

        self.logger.info(
            "Retrieved and deserialized %s existing players from GraphQL",
            len(players),
        )
        return players
