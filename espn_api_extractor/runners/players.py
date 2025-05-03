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
    parser.add_argument(
        "--threads", type=int, default=None, 
        help="Number of threads to use for player hydration (default: 4x CPU cores)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=100,
        help="Number of players to process in each batch for progress tracking (default: 100)"
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
        logger.logging.info(f"Hydrating player objects with additional data using {'auto-detected' if args.threads is None else args.threads} threads")
        core_requestor = EspnCoreRequests(
            sport="mlb",
            year=args.year,
            logger=logger,
            max_workers=args.threads,  # Pass the thread count (None will use the default)
        )
        try:
            # Get detailed player data and hydrate the player object
            hydrated_players, failed_players = core_requestor.hydrate_players(
                player_objs,
                batch_size=args.batch_size,  # Pass the batch size for progress tracking
            )

            # Log summary of hydration process
            logger.logging.info(
                f"Successfully hydrated {len(hydrated_players)} players; Failed to hydrate {len(failed_players)} players"
            )

            # Print a summary for the user
            if failed_players:
                print("\n===== HYDRATION SUMMARY =====")
                print(f"Successfully hydrated: {len(hydrated_players)} players")
                print(f"Failed to hydrate: {len(failed_players)} players")
                print("\nFailed players (first 10):")
                for i, player in enumerate(failed_players[:10]):
                    player_name = player.name if hasattr(player, "name") else "Unknown"
                    print(f"  {i + 1}. ID={player.id}, Name={player_name}")
                if len(failed_players) > 10:
                    print(f"  ... and {len(failed_players) - 10} more players")

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
