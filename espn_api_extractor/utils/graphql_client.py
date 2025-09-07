#!/usr/bin/env python3
"""
GraphQL client for ESPN API Extractor ETL pipeline.
READ-ONLY client for extraction optimization - handles connection testing,
player population queries, and HITL validation.

This script is EXTRACT-ONLY - no upsert/update functionality.
Output is saved locally for the next ETL pipeline stage.
"""

import json
import os
from typing import Dict, List, Optional, Set, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from espn_api_extractor.models.player_model import PlayerModel
from espn_api_extractor.utils.logger import Logger


class GraphQLClient:
    """
    READ-ONLY GraphQL client for extraction optimization.

    Provides:
    - Connection testing with HITL validation
    - Existing player population queries
    - Resource optimization for ESPN API calls

    Does NOT provide:
    - Data upserts/updates (out of scope for extraction phase)
    - Mutations (this is extract-only)

    Implements User Story 4: GraphQL Client with Human-in-the-Loop Validation.
    """

    def __init__(
        self, config_path: str = "hasura_config.json", logger: Optional[Logger] = None
    ):
        """
        Initialize GraphQL client with configuration.

        Args:
            config_path: Path to GraphQL configuration file
            logger: Optional logger instance
        """
        self.logger = logger or Logger(GraphQLClient.__name__)
        self.config_path = config_path
        self.endpoint: Optional[str] = None
        self.headers: Dict[str, str] = {}
        self.timeout: int = 30
        self.retry_attempts: int = 3
        self.retry_delay: int = 1
        self.is_available: bool = False

        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.retry_attempts,
            backoff_factor=self.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _log(self, level: str, message: str) -> None:
        """Thread-safe logging helper."""
        if self.logger:
            getattr(self.logger.logging, level)(message)

    def _load_config(self) -> bool:
        """
        Load GraphQL configuration from file.

        Returns:
            True if config loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(self.config_path):
                self._log(
                    "warning", f"GraphQL config file not found: {self.config_path}"
                )
                return False

            with open(self.config_path, "r") as f:
                config = json.load(f)

            self.endpoint = config.get("endpoint")
            self.headers = config.get("headers", {})
            self.timeout = config.get("timeout", 30)
            self.retry_attempts = config.get("retry_attempts", 3)
            self.retry_delay = config.get("retry_delay", 1)

            if not self.endpoint:
                self._log("error", "GraphQL endpoint not specified in config")
                return False

            # Update session headers
            self.session.headers.update(self.headers)
            self._log("info", f"GraphQL config loaded from {self.config_path}")
            return True

        except Exception as e:
            self._log("error", f"Failed to load GraphQL config: {str(e)}")
            return False

    def _test_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Test GraphQL endpoint connection with introspection query.

        Returns:
            Tuple of (success, error_message)
        """
        if not self.endpoint:
            return False, "No GraphQL endpoint configured"

        introspection_query = """
        query IntrospectionQuery {
            __schema {
                types {
                    name
                }
            }
        }
        """

        try:
            response = self.session.post(
                self.endpoint, json={"query": introspection_query}, timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                if "data" in data and "__schema" in data["data"]:
                    self._log("info", "GraphQL connection test successful")
                    return True, None
                else:
                    error_msg = data.get(
                        "errors", [{"message": "Unknown GraphQL error"}]
                    )[0]["message"]
                    return False, f"GraphQL error: {error_msg}"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:200]}"

        except requests.exceptions.ConnectTimeout:
            return False, f"Connection timeout to {self.endpoint}"
        except requests.exceptions.ConnectionError:
            return False, f"Connection failed to {self.endpoint}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def _prompt_user_for_fallback(self, error_message: str) -> bool:
        """
        Human-in-the-loop prompt for GraphQL connection failures.
        Implements HITL mechanism from User Story 4.

        Args:
            error_message: Detailed error message to show user

        Returns:
            True if user confirms to continue without GraphQL, False to abort
        """
        print("\n🔴 GraphQL Connection Failed")
        print(f"Endpoint: {self.endpoint}")
        print(f"Error: {error_message}")
        print("\nThis will result in a full ESPN API extraction (~4,600 API calls)")
        print("vs ~200-800 calls with GraphQL integration.")

        while True:
            response = (
                input("\nContinue with full ESPN extraction? (y/N): ").strip().lower()
            )

            if response in ["", "n", "no"]:
                print("❌ Aborting extraction. Please fix GraphQL endpoint and re-run.")
                return False
            elif response in ["y", "yes"]:
                print("⚠️  Proceeding with full ESPN extraction...")
                return True
            else:
                print("Please enter 'y' for yes or 'n' for no (default: no)")

    def initialize_with_hitl(
        self, force_full_extraction: bool = False
    ) -> "GraphQLClient":
        """
        Initialize GraphQL client with HITL validation.

        Args:
            force_full_extraction: If True, bypass GraphQL even if available

        Returns:
            Self for method chaining. Check is_available property to determine if GraphQL should be used.
        """
        if force_full_extraction:
            self._log("info", "Forcing full ESPN extraction (GraphQL bypassed)")
            self.is_available = False
        elif not self._load_config():
            self._log(
                "info",
                "No GraphQL config available, proceeding with full ESPN extraction",
            )
            self.is_available = False
        else:
            # Test connection
            success, error_message = self._test_connection()

            if success:
                self._log(
                    "info",
                    "GraphQL endpoint available - will use for player population optimization",
                )
                self.is_available = True
            else:
                error_msg = error_message or "Unknown connection error"
                self._log("warning", f"GraphQL connection failed: {error_msg}")

                # HITL prompt for failure handling
                if self._prompt_user_for_fallback(error_msg):
                    self._log(
                        "info",
                        "User confirmed: proceeding with full ESPN extraction",
                    )
                    self.is_available = False
                else:
                    self._log("info", "User aborted: fix GraphQL and re-run")
                    raise SystemExit(
                        "Extraction aborted by user - fix GraphQL endpoint and re-run"
                    )

        return self

    def get_existing_player_ids(self) -> Set[int]:
        """
        Query existing player IDs from GraphQL API.

        Returns:
            Set of ESPN player IDs that exist in the database
        """
        players = self.get_existing_players()
        return {player.id for player in players if player.id is not None}

    def get_existing_players(self) -> List[PlayerModel]:
        """
        Query existing players from GraphQL API with full deserialization.

        Returns fully deserialized Pydantic PlayerModel objects which guarantees
        field validation and type safety.

        Returns:
            List[PlayerModel]: Fully deserialized player objects from Hasura
        """
        # Comprehensive query for all player fields needed by PlayerModel
        # Note: Field names must match the actual Hasura GraphQL schema
        query = """
        query GetExistingPlayers {
            players {
                idEspn
                name
                firstName
                lastName
                displayName
                shortName
                nickname
                slugEspn
                primaryPosition
                eligibleSlots
                proTeam
                injuryStatus
                injured
                active
                weight
                displayWeight
                height
                displayHeight
                bats
                throws
                dateOfBirth
                birthPlace
                debutYear
                jersey
                headshot
            }
        }
        """

        if not self.endpoint:
            raise ValueError("GraphQL endpoint not configured")

        try:
            response = self.session.post(
                self.endpoint, json={"query": query}, timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                if "data" in data and "players" in data["data"]:
                    players_data = data["data"]["players"]

                    # Deserialize each player into PlayerModel with proper validation
                    players = []
                    for player_data in players_data:
                        try:
                            # Map GraphQL field names to PlayerModel field names
                            if "idEspn" in player_data:
                                player_data["id"] = player_data.pop("idEspn")
                            if "slugEspn" in player_data:
                                player_data["slug"] = player_data.pop("slugEspn")
                            
                            # Convert jersey number to string
                            if isinstance(player_data.get("jersey"), int):
                                player_data["jersey"] = str(player_data["jersey"])
                            
                            # Parse eligibleSlots JSON string if present
                            if isinstance(player_data.get("eligibleSlots"), str):
                                import json
                                try:
                                    player_data["eligibleSlots"] = json.loads(player_data["eligibleSlots"])
                                except:
                                    player_data["eligibleSlots"] = []
                            
                            player_model = PlayerModel(**player_data)
                            players.append(player_model)
                        except Exception as e:
                            self._log(
                                "warning",
                                f"Failed to deserialize player {player_data.get('idEspn', player_data.get('id', 'unknown'))}: {str(e)}",
                            )
                            continue

                    self._log(
                        "info",
                        f"Retrieved and deserialized {len(players)} existing players from GraphQL",
                    )
                    return players
                else:
                    self._log("error", f"Unexpected GraphQL response: {data}")
                    return []
            else:
                self._log("error", f"GraphQL query failed: HTTP {response.status_code}")
                return []

        except Exception as e:
            self._log("error", f"Failed to query existing players: {str(e)}")
            return []
