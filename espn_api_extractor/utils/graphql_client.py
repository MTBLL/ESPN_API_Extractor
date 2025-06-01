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

    def __init__(self, config_path: str = "hasura_config.json", logger: Optional[Logger] = None):
        """
        Initialize GraphQL client with configuration.
        
        Args:
            config_path: Path to GraphQL configuration file
            logger: Optional logger instance
        """
        self.logger = logger
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

    def load_config(self) -> bool:
        """
        Load GraphQL configuration from file.
        
        Returns:
            True if config loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(self.config_path):
                self._log("warning", f"GraphQL config file not found: {self.config_path}")
                return False
                
            with open(self.config_path, 'r') as f:
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

    def test_connection(self) -> Tuple[bool, Optional[str]]:
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
                self.endpoint,
                json={"query": introspection_query},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "__schema" in data["data"]:
                    self._log("info", "GraphQL connection test successful")
                    return True, None
                else:
                    error_msg = data.get("errors", [{"message": "Unknown GraphQL error"}])[0]["message"]
                    return False, f"GraphQL error: {error_msg}"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:200]}"
                
        except requests.exceptions.ConnectTimeout:
            return False, f"Connection timeout to {self.endpoint}"
        except requests.exceptions.ConnectionError:
            return False, f"Connection failed to {self.endpoint}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def prompt_user_for_fallback(self, error_message: str) -> bool:
        """
        Human-in-the-loop prompt for GraphQL connection failures.
        Implements HITL mechanism from User Story 4.
        
        Args:
            error_message: Detailed error message to show user
            
        Returns:
            True if user confirms to continue without GraphQL, False to abort
        """
        print(f"\n🔴 GraphQL Connection Failed")
        print(f"Endpoint: {self.endpoint}")
        print(f"Error: {error_message}")
        print(f"\nThis will result in a full ESPN API extraction (~4,600 API calls)")
        print(f"vs ~200-800 calls with GraphQL integration.")
        
        while True:
            response = input(f"\nContinue with full ESPN extraction? (y/N): ").strip().lower()
            
            if response in ['', 'n', 'no']:
                print("❌ Aborting extraction. Please fix GraphQL endpoint and re-run.")
                return False
            elif response in ['y', 'yes']:
                print("⚠️  Proceeding with full ESPN extraction...")
                return True
            else:
                print("Please enter 'y' for yes or 'n' for no (default: no)")

    def initialize_with_hitl(self, force_full_extraction: bool = False) -> bool:
        """
        Initialize GraphQL client with HITL validation.
        
        Args:
            force_full_extraction: If True, bypass GraphQL even if available
            
        Returns:
            True if GraphQL should be used, False for full ESPN extraction
        """
        if force_full_extraction:
            self._log("info", "Forcing full ESPN extraction (GraphQL bypassed)")
            self.is_available = False
            return False
            
        # Try to load config
        if not self.load_config():
            self._log("info", "No GraphQL config available, proceeding with full ESPN extraction")
            self.is_available = False
            return False
            
        # Test connection
        success, error_message = self.test_connection()
        
        if success:
            self._log("info", "GraphQL endpoint available - will use for player population optimization")
            self.is_available = True
            return True
        else:
            error_msg = error_message or "Unknown connection error"
            self._log("warning", f"GraphQL connection failed: {error_msg}")
            
            # HITL prompt for failure handling
            if self.prompt_user_for_fallback(error_msg):
                self._log("info", "User confirmed: proceeding with full ESPN extraction")
                self.is_available = False
                return False
            else:
                self._log("info", "User aborted: fix GraphQL and re-run")
                raise SystemExit("Extraction aborted by user - fix GraphQL endpoint and re-run")

    def get_existing_player_ids(self) -> Set[int]:
        """
        Query existing player IDs from GraphQL API.
        
        Returns:
            Set of ESPN player IDs that exist in the database
        """
        if not self.is_available or not self.endpoint:
            return set()
            
        # Example query - adjust based on your actual schema
        query = """
        query GetExistingPlayers {
            players {
                espn_id
            }
        }
        """
        
        try:
            response = self.session.post(
                self.endpoint,
                json={"query": query},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "players" in data["data"]:
                    player_ids = {player["espn_id"] for player in data["data"]["players"]}
                    self._log("info", f"Retrieved {len(player_ids)} existing player IDs from GraphQL")
                    return player_ids
                else:
                    self._log("error", f"Unexpected GraphQL response: {data}")
                    return set()
            else:
                self._log("error", f"GraphQL query failed: HTTP {response.status_code}")
                return set()
                
        except Exception as e:
            self._log("error", f"Failed to query existing players: {str(e)}")
            return set()

