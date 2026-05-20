import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from threading import Lock

import requests
from requests.cookies import RequestsCookieJar
from rich.console import Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from typing_extensions import Any, Dict, List, Optional, Tuple

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.utils.logger import Logger

from .constants import ESPN_CORE_SPORT_ENDPOINTS, STAT_CATEGORY, STAT_SEASON_TYPE


class EspnCoreRequests:
    def __init__(self, sport: str, year: int, max_workers: int | None = None):
        try:
            assert sport in ["nfl", "mlb"]
            self.sport = sport
            self.sport_endpoint = ESPN_CORE_SPORT_ENDPOINTS[sport]
            self.year = year
        except AssertionError:
            print("Invalid sport")
            exit()

        self.logger = Logger(EspnCoreRequests.__name__)
        self.logger_lock = Lock()  # Thread-safe logging

        # Configure default number of workers if not specified (use CPU count)
        cpu_count = os.cpu_count()
        if cpu_count is None:
            cpu_count = 1
        self.max_workers = (
            max_workers if max_workers is not None else min(32, cpu_count * 4)
        )

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
            }
        )
        self.session.cookies = RequestsCookieJar()

        # In-memory store of players that returned 404 during hydration.
        # Populated by _get_player_data / _fetch_player_stats and reported
        # in aggregate at the end of hydrate_players to avoid interrupting
        # the rich progress bar with per-request 404 log lines.
        self.not_found_players: List[Dict[str, Any]] = []

    def _check_request_status(
        self,
        status: int,
        extend: str = "",
        params: dict | None = None,
        headers: dict | None = None,
    ):
        """Handles ESPN API response status codes and endpoint format switching"""
        if status == 200:
            return

        # Use thread-safe logging
        with self.logger_lock:
            if status == 404:
                # 404s are tracked separately via not_found_players and
                # reported in aggregate at the end of hydrate_players.
                return
            elif status == 429:
                self.logger.logging.warning("Rate limit exceeded")
            elif status == 500:
                self.logger.logging.warning("Internal server error")
            elif status == 503:
                self.logger.logging.warning("Service unavailable")
            else:
                self.logger.logging.warning(f"Unknown error: {status}")

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

    def _get_player_data(
        self,
        player_id: int,
        params: dict = {},
        max_retries: int = 3,
        player: Optional[Player] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get player data with retry mechanism.
        Returns player data as dictionary on success, None on failure after retries.
        Thread-safe implementation.

        Note: 404 errors are not retried since they indicate the player ID doesn't exist.
        When `player` is provided, 404 hits are recorded to ``self.not_found_players``
        (instead of logged inline) so the rich progress bar isn't interrupted.
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
                    timeout=10,  # Add timeout to avoid hanging requests
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

                # Don't retry 404 errors - player ID doesn't exist.
                # Record to in-memory store and skip inline logging so the
                # progress bar isn't interrupted; reported at end of run.
                if r.status_code == 404:
                    self._record_not_found(
                        player_id=player_id, player=player, kind="bio"
                    )
                    return None

                # Log non-404 errors normally
                self._check_request_status(
                    r.status_code, extend=endpoint, params=params
                )
                with self.logger_lock:
                    self.logger.logging.warning(
                        f"Failed to fetch player {player_id} (attempt {retries + 1}/{max_retries}): HTTP {r.status_code}"
                    )

            except Exception as e:
                # Handle connection errors, timeouts, etc.
                with self.logger_lock:
                    self.logger.logging.warning(
                        f"Exception getting player {player_id} (attempt {retries + 1}/{max_retries}): {str(e)}"
                    )

            # Increment retry counter and apply exponential backoff
            retries += 1
            if retries < max_retries:
                time.sleep(backoff_time)
                backoff_time *= 2  # Exponential backoff

        # If we get here, all retries failed
        with self.logger_lock:
            self.logger.logging.error(
                f"Failed to fetch player {player_id} after {max_retries} attempts"
            )
        return None

    def _fetch_player_stats(
        self,
        player_id: int,
        params: dict = {},
        max_retries: int = 3,
        player: Optional[Player] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get player statistics with retry mechanism.
        Returns player statistics data as dictionary on success, None on failure after retries.
        Thread-safe implementation.

        Note: 404 errors are not retried since they indicate the player ID doesn't exist.
        When `player` is provided, 404 hits are recorded to ``self.not_found_players``
        (instead of logged inline) so the rich progress bar isn't interrupted.
        """
        current_year = datetime.now().year
        season_type = STAT_SEASON_TYPE  # 2 for regular season
        stat_category = STAT_CATEGORY  # 0 for all splits

        endpoint = f"{self.sport_endpoint}/seasons/{current_year}/types/{season_type}/athletes/{player_id}/statistics/{stat_category}"
        retries = 0
        backoff_time = 1  # Start with 1 second backoff

        while retries < max_retries:
            try:
                r = requests.get(
                    endpoint,
                    params=params,
                    headers=self.session.headers,
                    cookies=self.session.cookies,
                    timeout=10,  # Add timeout to avoid hanging requests
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

                # 404: record silently, don't retry.
                if r.status_code == 404:
                    self._record_not_found(
                        player_id=player_id, player=player, kind="stats"
                    )
                    return None

                # Non-404: log via shared status handler and continue retrying.
                self._check_request_status(
                    r.status_code, extend=endpoint, params=params
                )

            except Exception as e:
                # Handle connection errors, timeouts, etc.
                with self.logger_lock:
                    self.logger.logging.warning(
                        f"Exception getting statistics for player {player_id} (attempt {retries + 1}/{max_retries}): {str(e)}"
                    )

            # Increment retry counter and apply exponential backoff
            retries += 1
            if retries < max_retries:
                time.sleep(backoff_time)
                backoff_time *= 2  # Exponential backoff

        # If we get here, all retries failed
        with self.logger_lock:
            self.logger.logging.error(
                f"Failed to fetch statistics for player {player_id} after {max_retries} attempts"
            )
        return None

    def _record_not_found(
        self, player_id: int, player: Optional[Player], kind: str
    ) -> None:
        """Record a 404 hit for later aggregated reporting.

        Thread-safe; writes through ``logger_lock`` to keep the in-memory
        list consistent across worker threads.
        """
        name = getattr(player, "name", None) if player is not None else None
        team = getattr(player, "pro_team", None) if player is not None else None
        with self.logger_lock:
            self.not_found_players.append(
                {
                    "id": player_id,
                    "name": name or "Unknown",
                    "team": team or "Unknown",
                    "kind": kind,
                }
            )

    def _hydrate_player_with_bio(self, player: Player) -> Tuple[Player, bool]:
        """
        Hydrate a player with biographical data from API.
        Returns a tuple of (player, success_flag).
        Thread-safe implementation.
        """
        assert player.id is not None, "Player ID is required"

        data = self._get_player_data(player.id, player=player)
        if data is None:
            return player, False

        try:
            # Hydrate with basic biographical data
            hydrated_player = player
            hydrated_player.hydrate_bio(data)
            return hydrated_player, True
        except Exception as e:
            with self.logger_lock:
                self.logger.logging.error(
                    f"Error hydrating player {player.id} with biographical data: {str(e)}"
                )
            return player, False

    def _hydrate_player_worker(
        self, player: Player, include_stats: bool = False
    ) -> Tuple[Player, bool]:
        """
        Worker function for ThreadPoolExecutor that handles the hydration logic.
        Calls appropriate hydration methods based on include_stats parameter.
        Stats hydration is no longer performed; include_stats is retained for compatibility.
        """
        if include_stats:
            pass
        # First, hydrate with biographical data
        hydrated_player, bio_success = self._hydrate_player_with_bio(player)

        if not bio_success:
            return hydrated_player, False

        return hydrated_player, bio_success

    def hydrate_players(
        self, players: list[Player], batch_size: int = 100, include_stats: bool = False
    ) -> Tuple[List[Player], List[Player]]:
        """
        Hydrate a list of players with additional data using multi-threading.
        Returns a tuple of (hydrated_players, failed_players).

        Args:
            players: List of Player objects to hydrate
            batch_size: Number of players to process in each batch (to manage progress bar)
            include_stats: Ignored. Kona playercard provides stats, so Core API
                hydration only fetches biographical data.
        """
        hydrated_players: List[Player] = []
        failed_players: List[Player] = []
        total_players = len(players)

        # Reset 404 store for this hydration cycle so the aggregated summary
        # at the end reflects only the current run.
        self.not_found_players = []

        # Log start of multi-threaded hydration
        with self.logger_lock:
            self.logger.logging.info(
                f"Starting multi-threaded hydration of {total_players} players with {self.max_workers} workers"
            )

        total_batches = (total_players + batch_size - 1) // batch_size
        hydration_start = time.perf_counter()

        # Two separate Progress instances grouped in a Live render so batch
        # progress stays above the overall total bar regardless of when each
        # task was added.
        progress_columns = (
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        )
        batch_progress = Progress(*progress_columns, transient=True)
        overall_progress = Progress(*progress_columns, transient=False)

        with Live(Group(batch_progress, overall_progress), refresh_per_second=10):
            overall_task = overall_progress.add_task(
                "Total progress", total=total_players
            )

            for i in range(0, total_players, batch_size):
                batch = players[i : i + batch_size]
                batch_size_actual = len(batch)
                batch_num = i // batch_size + 1

                batch_task = batch_progress.add_task(
                    f"Batch {batch_num}/{total_batches}",
                    total=batch_size_actual,
                )
                try:
                    with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                        futures_to_players = {
                            executor.submit(
                                self._hydrate_player_worker, player, include_stats
                            ): player
                            for player in batch
                        }

                        for future in as_completed(futures_to_players):
                            player = futures_to_players[future]
                            try:
                                hydrated_player, success = future.result()

                                if success:
                                    hydrated_players.append(hydrated_player)
                                else:
                                    # Per-player failure logs would interrupt the
                                    # rich progress bar; the end-of-run summary
                                    # below reports failures in aggregate.
                                    failed_players.append(hydrated_player)
                            except Exception as exc:
                                with self.logger_lock:
                                    self.logger.logging.error(
                                        f"Player {player.id} generated an exception: {exc}"
                                    )
                                failed_players.append(player)

                            batch_progress.advance(batch_task)
                            overall_progress.advance(overall_task)
                finally:
                    batch_progress.remove_task(batch_task)

        hydration_elapsed = time.perf_counter() - hydration_start

        with self.logger_lock:
            self.logger.logging.info(
                f"Successfully hydrated {len(hydrated_players)} players in {hydration_elapsed:.1f}s"
            )

            # Aggregate report for 404s collected during this run. Printed
            # after the progress bar exits so it doesn't get clobbered.
            if self.not_found_players:
                self.logger.logging.warning(
                    f"Skipped {len(self.not_found_players)} player(s) returning 404:"
                )
                for entry in self.not_found_players:
                    self.logger.logging.warning(
                        f"  [404 {entry['kind']}] {entry['id']}, "
                        f"{entry['name']}, {entry['team']}"
                    )

            if failed_players:
                self.logger.logging.warning(
                    f"Unable to hydrate {len(failed_players)} players"
                )
                for i, player in enumerate(
                    failed_players[:10]
                ):  # Log first 10 failed players
                    player_name = (
                        player.display_name
                        if hasattr(player, "display_name") and player.display_name
                        else getattr(player, "name", None) or "Unknown"
                    )
                    player_team = getattr(player, "pro_team", None) or "Unknown"
                    self.logger.logging.warning(
                        f"  Failed player {i + 1}: {player.id}, "
                        f"{player_name}, {player_team}"
                    )
                if len(failed_players) > 10:
                    self.logger.logging.warning(
                        f"  ... and {len(failed_players) - 10} more players"
                    )

        return hydrated_players, failed_players
