#!/usr/bin/env python3
import argparse

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.requests.core_requests import EspnCoreRequests

# Using absolute imports
from espn_api_extractor.requests.fantasy_requests import EspnFantasyRequests
from espn_api_extractor.utils.logger import Logger


def main():
    parser = argparse.ArgumentParser(description="Access ESPN Fantasy Baseball API")

    parser.add_argument(
        "--year", type=int, default=2025, help="League year (default: 2025)"
    )
    args = parser.parse_args()

    logger = Logger("player-extractor")
    try:
        requestor = EspnFantasyRequests(
            sport="mlb",
            year=args.year,
            league_id=None,
            cookies={},
            logger=logger,
        )
        players = requestor.get_pro_players()
        logger.logging.info(f"successfully got {len(players)} players")
        # cast the json response into Player objects
        player_objs = [Player(player) for player in players]

        # Hydrate player objects with additional data
        logger.logging.info("Hydrating player objects with additional data")
        core_requestor = EspnCoreRequests(
            sport="mlb",
            year=args.year,
            logger=logger,
        )
        try:
            # Get detailed player data and hydrate the player object
            hydrated_players = core_requestor.hydrate_players(player_objs)
            logger.logging.debug(
                f"Successfully hydrated number of players players: {len(hydrated_players)}"
            )
            # Return the list of fully hydrated player objects
            return hydrated_players
        except Exception as e:
            logger.logging.error(f"Error hydrating players: {e}")

    except Exception as e:
        print(f"Error: {e}")
        print(
            "\nNote: If this is a private league, you need to provide espn_s2 and swid cookies."
        )
        print(
            "You can find these cookies in your browser after logging into ESPN Fantasy."
        )


if __name__ == "__main__":
    main()
