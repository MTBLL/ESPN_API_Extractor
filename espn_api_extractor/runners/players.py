#!/usr/bin/env python3
import argparse

from espn_api_extractor.baseball.player import Player

# Using absolute imports
from espn_api_extractor.requests.espn_requests import EspnFantasyRequests
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
        # once we have the player objects, we need to hydrate the rest of the player data,
        # either by self mutable calls or a functional method that returns the hydrated players

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
