import requests
from requests.sessions import cookies
from typing_extensions import List

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.utils.logger import Logger

from .constant import ESPN_CORE_SPORT_ENDPOINTS


class EspnCoreRequests:
    def __init__(self, sport: str, year: int, logger: Logger):
        try:
            assert sport in ["nfl", "mlb"]
            self.sport = sport
            self.sport_endpoint = ESPN_CORE_SPORT_ENDPOINTS[sport]
            self.year = year
        except AssertionError:
            print("Invalid sport")
            exit()

        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
            }
        )
        self.session.cookies = cookies.RequestsCookieJar()

    def _checkRequestStatus(
        self,
        status: int,
        extend: str = "",
        params: dict | None = None,
        headers: dict | None = None,
    ) -> dict | None:
        """Handles ESPN API response status codes and endpoint format switching"""
        if status == 200:
            return None
        elif status == 404:
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
        self._checkRequestStatus(r.status_code)

        if self.logger:
            self.logger.log_request(
                endpoint=endpoint, params=params, headers=headers, response=r.json()
            )
        return r.json()

    def _get_player_data(self, player_id: int, params: dict = {}):
        endpoint = self.sport_endpoint + f"/athletes/{player_id}"
        r = requests.get(
            endpoint,
            params=params,
            headers=self.session.headers,
            cookies=self.session.cookies,
        )
        self._checkRequestStatus(r.status_code)

        if self.logger:
            self.logger.log_request(
                endpoint=endpoint,
                params=params,
                headers=self.session.headers,
                response=r.json(),
            )
        return r.json()

    def _hydrate_player(self, player: Player) -> Player:
        assert player.id is not None, "Player ID is required"
        data = self._get_player_data(player.id)

        hydrated_player = player
        hydrated_player.hydrate(data)
        return hydrated_player

    def hydrate_players(self, players: list[Player]) -> List[Player]:
        hydrated_players: List[Player] = []
        for player in players:
            hydrated_players.append(self._hydrate_player(player))

        return hydrated_players
