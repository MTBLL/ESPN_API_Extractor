#!/usr/bin/env python
"""
Test script to verify the statistics fetching functionality.
This script:
1. Fetches a small number of players
2. Hydrates them with basic information
3. Hydrates them with statistics
4. Prints out key statistics for each player
"""

import logging
import os
import sys

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.requests.core_requests import EspnCoreRequests
from espn_api_extractor.requests.fantasy_requests import EspnFantasyRequests
from espn_api_extractor.utils.logger import Logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = Logger("debugger")


def main():
    """Main function to test the statistics fetching functionality."""
    # Initialize request objects
    year = 2025  # Current season
    fantasy_requests = EspnFantasyRequests(sport="mlb", year=year, logger=logger)
    core_requests = EspnCoreRequests(sport="mlb", year=year, logger=logger)

    # Fetch a small number of players
    print("Fetching players...")
    players_data = fantasy_requests.get_pro_players()

    # Create Player objects
    players = []
    for player_data in players_data:
        player = Player(player_data)
        players.append(player)

    # Hydrate players with both basic data and statistics
    print(f"Hydrating {len(players)} players with basic data and statistics...")
    stats_players, failed_stats = core_requests.hydrate_players(
        players, include_stats=True
    )

    if failed_stats:
        print(f"Warning: Failed to hydrate {len(failed_stats)} players")

    # Print out key statistics for each player
    print("\nPlayer Statistics Summary:")
    print("=" * 80)

    for player in stats_players:
        print(f"\n{player.display_name} (ID: {player.id})")
        print("-" * 40)

        if hasattr(player, "season_stats") and player.season_stats:
            # Print split information
            print(
                f"Split: {player.season_stats.get('split_name', 'Unknown')} "
                f"({player.season_stats.get('split_abbreviation', 'Unknown')})"
            )

            # Print batting category if available
            batting = player.season_stats.get("categories", {}).get("batting")
            if batting:
                print(f"\nBatting Summary: {batting.get('summary', 'N/A')}")

                # Print key batting statistics
                stats = batting.get("stats", {})
                key_stats = ["avg", "homeRuns", "RBIs", "runs", "stolenBases", "OPS"]

                for stat_name in key_stats:
                    if stat_name in stats:
                        stat = stats[stat_name]
                        display_name = stat.get("display_name", stat_name)
                        value = stat.get("display_value", "N/A")
                        rank = stat.get("rank_display_value", "N/A")
                        print(f"{display_name}: {value} (Rank: {rank})")

            # Print pitching category if available
            pitching = player.season_stats.get("categories", {}).get("pitching")
            if pitching:
                print(f"\nPitching Summary: {pitching.get('summary', 'N/A')}")

                # Print key pitching statistics
                stats = pitching.get("stats", {})
                key_stats = [
                    "ERA",
                    "wins",
                    "strikeouts",
                    "WHIP",
                    "saveOpportunities",
                    "saves",
                ]

                for stat_name in key_stats:
                    if stat_name in stats:
                        stat = stats[stat_name]
                        display_name = stat.get("display_name", stat_name)
                        value = stat.get("display_value", "N/A")
                        rank = stat.get("rank_display_value", "N/A")
                        print(f"{display_name}: {value} (Rank: {rank})")
        else:
            print("No season statistics available")

    # Save player models to file
    output_dir = "debug_output"
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nSaving player models to {output_dir}...")
    for player in stats_players:
        model = player.to_model()
        player_file = os.path.join(output_dir, f"player_{player.id}.json")

        with open(player_file, "w") as f:
            f.write(model.model_dump_json(indent=2))

    print(f"Saved {len(stats_players)} player models to {output_dir}")
    print("Done!")


if __name__ == "__main__":
    main()
