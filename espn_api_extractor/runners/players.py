#!/usr/bin/env python3
import argparse
from typing import List, Optional, Union

from espn_api_extractor.baseball.player import Player
from espn_api_extractor.models.player_model import PlayerModel
from espn_api_extractor.requests.core_requests import EspnCoreRequests
from espn_api_extractor.runners.handlers import ProPlayersHandler
from espn_api_extractor.utils.graphql_client import GraphQLClient
from espn_api_extractor.utils.utils import write_models_to_json

from . import CoreRunner


def main(
    sample_size: Optional[int] = None,
    output_dir: str = ".",
) -> Union[List[Player], List[PlayerModel]]:
    """
    Main function to extract player data from ESPN Fantasy Baseball API with GraphQL optimization.

    Implements User Stories 1-6 for iterative ETL pipeline:
    - GraphQL-first player population check for resource optimization
    - HITL validation for GraphQL connection failures
    - Always extracts bio+stats data (User Story 2)
    - Extract-only functionality (outputs saved locally for next ETL stage)

    Args:
        sample_size: Optional maximum number of players to process. If provided,
                    this will limit API calls to save time when only a sample is needed.
        output_dir: Optional path to write the JSON output. If None, no file is written.

    Returns:
        Either a list of Player objects or PlayerModel objects (if as_models=True)

    CLI Usage:
        # Standard execution with GraphQL optimization
        poetry run espn-players --output_dir ./output

        # Force full extraction (bypass GraphQL)
        poetry run espn-players --output_dir ./output --force-full-extraction

        # Custom GraphQL config
        poetry run espn-players --output_dir ./output --graphql-config ./custom_config.json
    """
    parser = argparse.ArgumentParser(description="Access ESPN Fantasy Baseball API")

    parser.add_argument(
        "--year", type=int, default=2025, help="League year (default: 2025)"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=None,
        help="Number of threads to use for player hydration (default: 4x CPU cores)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of players to process in each batch for progress tracking (default: 100)",
    )
    parser.add_argument(
        "--as-models",
        action="store_true",
        help="Return Pydantic models instead of Player objects (default: False)",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        help="Directory path to write JSON output. If not specified, no file is written.",
    )
    parser.add_argument(
        "--force-full-extraction",
        action="store_true",
        help="Force full ESPN extraction, bypassing GraphQL optimization (default: False)",
    )
    parser.add_argument(
        "--graphql-config",
        type=str,
        default="hasura_config.json",
        help="Path to GraphQL configuration file (default: hasura_config.json)",
    )
    args: argparse.Namespace = parser.parse_args()

    runner = CoreRunner(parser, "player-runner", output_dir)
    log = runner.logger.logging

    try:
        # Get ESPN player universe
        espn_players = ProPlayersHandler(runner).fetch()

        # Initialize GraphQL client for extraction optimization (User Story 1 & 4)
        graphql_client = GraphQLClient(
            config_path=runner.graphql_config_path, logger=runner.logger
        )
        use_graphql = graphql_client.initialize_with_hitl(
            force_full_extraction=runner.force_full_extraction
        )

        # Apply GraphQL optimization if available
        if use_graphql:
            existing_player_ids = graphql_client.get_existing_player_ids()
            if existing_player_ids:
                # Filter to only missing players to minimize ESPN API calls
                missing_players = [
                    p for p in espn_players if p.get("id") not in existing_player_ids
                ]
                players_to_process = missing_players
                log.info(
                    f"GraphQL optimization: {len(existing_player_ids)} existing players found"
                )
                log.info(
                    f"Processing {len(players_to_process)} missing players (saved {len(existing_player_ids)} ESPN API calls)"
                )
            else:
                # No existing players found, process all
                players_to_process = espn_players
                log.info(
                    "No existing players found in GraphQL, processing all ESPN players"
                )
        else:
            # Full extraction mode
            players_to_process = espn_players
            log.info("Full extraction mode: processing all ESPN players")

        # Apply sample size limit if specified
        if sample_size is not None and sample_size < len(players_to_process):
            players_to_process = players_to_process[:sample_size]
            log.info(f"Limited to {sample_size} players as specified")

        # Cast the json response into Player objects
        player_objs = [Player(player) for player in players_to_process]

        # Fetch player card data (projections, seasonal stats, outlook) for all players before bio hydration
        log.info(
            "Fetching player cards with projections and seasonal data for all players"
        )
        player_ids = [player.id for player in player_objs if player.id is not None]

        if player_ids:
            try:
                player_cards_data = fantasy_requestor.get_player_cards(player_ids)
                # Create a lookup dictionary for player card data by player ID
                player_cards_lookup = {}
                top_level_lookup = {}
                for player_data in player_cards_data.get("players", []):
                    player_id = player_data.get("id")
                    if player_id:
                        player_cards_lookup[player_id] = player_data.get("player", {})
                        # Store top-level data separately
                        top_level_lookup[player_id] = {
                            "draftAuctionValue": player_data.get("draftAuctionValue"),
                            "onTeamId": player_data.get("onTeamId"),
                        }

                # Hydrate each player with their player card data (projections, seasonal stats, outlook, fantasy data)
                for player in player_objs:
                    if player.id in player_cards_lookup:
                        player.hydrate_kona_playercard(
                            player_cards_lookup[player.id],
                            top_level_lookup.get(player.id, {}),
                        )

                log.info(
                    f"Successfully fetched player cards for {len(player_cards_lookup)} players"
                )
            except Exception as e:
                log.warning(f"Failed to fetch player cards data: {e}")

        # Hydrate player objects with additional data
        log.info(
            f"Hydrating player objects with additional data using {'auto-detected' if threads is None else threads} threads"
        )
        core_requestor = EspnCoreRequests(
            sport="mlb",
            year=year,
            logger=logger,
            max_workers=threads,  # Pass the thread count (None will use the default)
        )
        try:
            # Get detailed player data and hydrate the player object
            hydrated_players, failed_players = core_requestor.hydrate_players(
                player_objs,
                batch_size=batch_size,  # Pass the batch size for progress tracking
                include_stats=include_stats,
            )

            # Log summary of hydration process
            log.info(
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

            # Convert to Pydantic models for all output operations
            player_models = [player.to_model() for player in hydrated_players]

            # Write to JSON file if output path is specified
            output_dir_val = args.output_dir  # type: ignore
            if output_dir_val:
                write_models_to_json(
                    player_models, output_dir_val, "espn_player_universe.json"
                )
                logger.logging.info(
                    f"Wrote {len(player_models)} player models to {output_dir_val}"
                )

            # Return the requested format (models or player objects)
            if args.as_models:  # type: ignore
                return player_models
            else:
                # Return the list of fully hydrated player objects
                return hydrated_players

        except Exception as e:
            log.error(f"Error hydrating players: {e}")
            return []

    except Exception as e:
        print(f"Error: {e}")
        print(
            "\nNote: If this is a private league, you need to provide espn_s2 and swid cookies."
        )
        print(
            "You can find these cookies in your browser after logging into ESPN Fantasy."
        )
        return []


if __name__ == "__main__":
    main()
