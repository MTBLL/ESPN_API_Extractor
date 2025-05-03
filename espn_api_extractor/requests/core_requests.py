import requests
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.cookies import RequestsCookieJar
from tqdm import tqdm
from typing_extensions import List, Dict, Tuple, Optional, Any
from threading import Lock

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.utils.logger import Logger

from .constant import ESPN_CORE_SPORT_ENDPOINTS


class EspnCoreRequests:
    def __init__(self, sport: str, year: int, logger: Logger, max_workers: int = None):
        try:
            assert sport in ["nfl", "mlb"]
            self.sport = sport
            self.sport_endpoint = ESPN_CORE_SPORT_ENDPOINTS[sport]
            self.year = year
        except AssertionError:
            print("Invalid sport")
            exit()

        self.logger = logger
        self.logger_lock = Lock()  # Thread-safe logging
        
        # Configure default number of workers if not specified (use CPU count)
        self.max_workers = max_workers if max_workers is not None else min(32, os.cpu_count() * 4)
        
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
            }
        )
        self.session.cookies = RequestsCookieJar()

    def _check_request_status(
        self,
        status: int,
        extend: str = "",
        params: dict | None = None,
        headers: dict | None = None,
    ) -> dict | None:
        """Handles ESPN API response status codes and endpoint format switching"""
        if status == 200:
            return None
            
        # Use thread-safe logging
        with self.logger_lock:
            if status == 404:
                self.logger.logging.warn(f"Endpoint not found: {extend}")
            elif status == 429:
                self.logger.logging.warn("Rate limit exceeded")
            elif status == 500:
                self.logger.logging.warn("Internal server error")
            elif status == 503:
                self.logger.logging.warn("Service unavailable")
            else:
                self.logger.logging.warn(f"Unknown error: {status}")

    def _get(self, params: dict = {}, headers: dict = {}, extend: str = ""):
        endpoint = self.sport_endpoint + extend
        r = requests.get(
            endpoint, params=params, headers=headers, cookies=self.session.cookies
        )
        self._check_request_status(r.status_code)

        if self.logger:
            with self.logger_lock:
                self.logger.log_request(
                    endpoint=endpoint, params=params, headers=headers, response=r.json()
                )
        return r.json()

    def _get_player_data(self, player_id: int, params: dict = {}, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Get player data with retry mechanism.
        Returns player data as dictionary on success, None on failure after retries.
        Thread-safe implementation.
        
        Note: 404 errors are not retried since they indicate the player ID doesn't exist.
        """
        endpoint = self.sport_endpoint + f"/athletes/{player_id}"
        retries = 0
        backoff_time = 1  # Start with 1 second backoff
        
        while retries < max_retries:
            try:
                r = requests.get(
                    endpoint,
                    params=params,
                    headers=self.session.headers,
                    cookies=self.session.cookies,
                    timeout=10  # Add timeout to avoid hanging requests
                )
                
                # Check if request was successful
                if r.status_code == 200:
                    if self.logger:
                        with self.logger_lock:
                            self.logger.log_request(
                                endpoint=endpoint,
                                params=params,
                                headers=self.session.headers,
                                response=r.json(),
                            )
                    return r.json()
                else:
                    # Log the error status using existing method
                    self._check_request_status(r.status_code, extend=endpoint, params=params)
                    with self.logger_lock:
                        self.logger.logging.warning(
                            f"Failed to fetch player {player_id} (attempt {retries+1}/{max_retries}): HTTP {r.status_code}"
                        )
                    
                    # Don't retry 404 errors - player ID doesn't exist
                    if r.status_code == 404:
                        with self.logger_lock:
                            self.logger.logging.warning(f"Player ID {player_id} not found (404) - skipping retries")
                        return None
                    
            except Exception as e:
                # Handle connection errors, timeouts, etc.
                with self.logger_lock:
                    self.logger.logging.warning(
                        f"Exception getting player {player_id} (attempt {retries+1}/{max_retries}): {str(e)}"
                    )
            
            # Increment retry counter and apply exponential backoff
            retries += 1
            if retries < max_retries:
                time.sleep(backoff_time)
                backoff_time *= 2  # Exponential backoff
        
        # If we get here, all retries failed
        with self.logger_lock:
            self.logger.logging.error(f"Failed to fetch player {player_id} after {max_retries} attempts")
        return None

    def _hydrate_player(self, player: Player) -> Tuple[Player, bool]:
        """
        Hydrate a player with additional data from API.
        Returns a tuple of (player, success_flag).
        Thread-safe implementation.
        """
        assert player.id is not None, "Player ID is required"
        data = self._get_player_data(player.id)
        
        if data is None:
            return player, False
        
        try:
            # Create a deep copy is not needed since each thread works on a different player
            hydrated_player = player
            hydrated_player.hydrate(data)
            return hydrated_player, True
        except Exception as e:
            with self.logger_lock:
                self.logger.logging.error(f"Error hydrating player {player.id}: {str(e)}")
            return player, False

    def hydrate_players(self, players: list[Player], batch_size: int = 100) -> Tuple[List[Player], List[Player]]:
        """
        Hydrate a list of players with additional data using multi-threading.
        Returns a tuple of (hydrated_players, failed_players).
        
        Args:
            players: List of Player objects to hydrate
            batch_size: Number of players to process in each batch (to manage progress bar)
        """
        hydrated_players: List[Player] = []
        failed_players: List[Player] = []
        total_players = len(players)
        
        # Log start of multi-threaded hydration
        with self.logger_lock:
            self.logger.logging.info(f"Starting multi-threaded hydration of {total_players} players with {self.max_workers} workers")
        
        # Create an overall progress bar
        with tqdm(total=total_players, desc="Total progress", unit="player", position=0) as overall_progress:
            # Process players in batches to provide progress feedback
            for i in range(0, total_players, batch_size):
                batch = players[i:i+batch_size]
                batch_size_actual = len(batch)
                
                # Create progress bar for current batch (position=1 places it below the overall progress bar)
                with tqdm(total=batch_size_actual, 
                          desc=f"Batch {i//batch_size + 1}/{(total_players+batch_size-1)//batch_size}", 
                          unit="player", 
                          position=1, 
                          leave=False) as batch_progress:
                    
                    # Use thread pool to process players in parallel
                    with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                        # Submit all player hydration tasks to thread pool
                        futures_to_players = {executor.submit(self._hydrate_player, player): player for player in batch}
                        
                        # Process results as they complete
                        for future in as_completed(futures_to_players):
                            player = futures_to_players[future]
                            try:
                                # Get result from the future
                                hydrated_player, success = future.result()
                                
                                # Update collections based on success
                                if success:
                                    hydrated_players.append(hydrated_player)
                                else:
                                    failed_players.append(hydrated_player)
                                    with self.logger_lock:
                                        self.logger.logging.warn(
                                            f"Failed to hydrate player: {player.id} - "
                                            f"{player.displayName if hasattr(player, 'displayName') else 'Unknown'}"
                                        )
                            except Exception as exc:
                                # Handle any uncaught exceptions from the thread
                                with self.logger_lock:
                                    self.logger.logging.error(f"Player {player.id} generated an exception: {exc}")
                                failed_players.append(player)
                            
                            # Update both progress bars
                            batch_progress.update(1)
                            overall_progress.update(1)
        
        # Log summary of hydration results
        with self.logger_lock:
            self.logger.logging.info(f"Successfully hydrated {len(hydrated_players)} players")
            if failed_players:
                self.logger.logging.warning(f"Failed to hydrate {len(failed_players)} players")
                for i, player in enumerate(failed_players[:10]):  # Log first 10 failed players
                    player_name = player.displayName if hasattr(player, 'displayName') else 'Unknown'
                    self.logger.logging.warning(f"  Failed player {i+1}: ID={player.id}, Name={player_name}")
                if len(failed_players) > 10:
                    self.logger.logging.warning(f"  ... and {len(failed_players) - 10} more players")
        
        return hydrated_players, failed_players
