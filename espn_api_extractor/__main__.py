import argparse
import asyncio

from espn_api_extractor.runners import LeagueExtractRunner, PlayerExtractRunner


def create_player_parser(subparsers):
    """Create the player-extract subcommand parser"""
    player_parser = subparsers.add_parser(
        "player-extract",
        help="Extract player data from ESPN Fantasy Baseball API",
        aliases=["players-extract"],
    )

    player_parser.add_argument(
        "--year", type=int, default=2025, help="League year (default: 2025)"
    )
    player_parser.add_argument(
        "--league_id",
        type=int,
        default=10998,
        help="ESPN Fantasy League ID (optional, defaults to None for all players)",
    )
    player_parser.add_argument(
        "--threads",
        type=int,
        default=None,
        help="Number of threads to use for player hydration (default: 4x CPU cores)",
    )
    player_parser.add_argument(
        "--batch_size",
        type=int,
        default=100,
        help="Number of players to process in each batch for progress tracking (default: 100)",
    )
    player_parser.add_argument(
        "--as_models",
        action="store_true",
        help="Return Pydantic models instead of Player objects (default: False)",
    )
    player_parser.add_argument(
        "--output_dir",
        type=str,
        required=True,  # Make required at CLI level
        help="Directory path to write JSON output",
    )
    player_parser.add_argument(
        "--force_full_extraction",
        action="store_true",
        help="Force full ESPN extraction, bypassing GraphQL optimization (default: False)",
    )
    player_parser.add_argument(
        "--graphql_config",
        type=str,
        default="hasura_config.json",
        help="Path to GraphQL configuration file (default: hasura_config.json)",
    )
    player_parser.add_argument(
        "--sample_size",
        type=int,
        help="Optional maximum number of players to process",
    )

    return player_parser


def create_league_parser(subparsers):
    """Create the league-extract subcommand parser"""
    league_parser = subparsers.add_parser(
        "league-extract", help="Extract league data from ESPN Fantasy Baseball API"
    )

    league_parser.add_argument(
        "--year", type=int, default=2025, help="League year (default: 2025)"
    )
    league_parser.add_argument(
        "--league_id",
        type=int,
        default=10998,
        help="ESPN Fantasy League ID (default: 10998)",
    )
    league_parser.add_argument(
        "--espn_s2",
        type=str,
        default=None,
        help="ESPN S2 cookie for private league access",
    )
    league_parser.add_argument(
        "--swid",
        type=str,
        default=None,
        help="ESPN SWID cookie for private league access",
    )
    league_parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="Directory path to write JSON output",
    )

    return league_parser


def create_parser():
    parser = argparse.ArgumentParser(description="ESPN Fantasy ETL Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add player extract subcommand
    create_player_parser(subparsers)
    create_league_parser(subparsers)

    # TODO
    # create_fantasy_parser(subparsers)

    return parser


async def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.command in {"player-extract", "players-extract"}:
        runner = PlayerExtractRunner(args)
        return await runner.run()
    if args.command == "league-extract":
        runner = LeagueExtractRunner(args)
        return await runner.run()
    else:
        parser.print_help()
        return None


def cli_main():
    """Synchronous entry point for console script."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
