#!/usr/bin/env python3
import argparse

from espn_api_extractor.baseball.league import League


def main():
    parser = argparse.ArgumentParser(description="Access ESPN Fantasy Baseball League")
    parser.add_argument(
        "--league_id",
        type=int,
        default=10998,
        help="ESPN Fantasy Baseball League ID (default: 10998)",
    )
    parser.add_argument(
        "--year", type=int, default=2025, help="League year (default: 2025)"
    )
    parser.add_argument(
        "--espn_s2",
        type=str,
        default=None,
        help="ESPN S2 cookie for private league access",
    )
    parser.add_argument(
        "--swid",
        type=str,
        default=None,
        help="ESPN SWID cookie for private league access",
    )
    args = parser.parse_args()

    try:
        # Initialize the league
        league = League(
            league_id=args.league_id,
            year=args.year,
            espn_s2=args.espn_s2,
            swid=args.swid,
        )
        breakpoint()
        print(
            f"Successfully connected to league: {args.league_id} for year {args.year}"
        )
        print(f"Scoring Type: {league.scoring_type}")
        print(f"Current matchup period: {league.currentMatchupPeriod}")
        print("\nTeams:")
        for team in league.teams:
            print(f"  - {team.team_name} (Owner: {team.owner})")

        # Display current standings
        print("\nCurrent Standings:")
        standings = league.standings()
        for i, team in enumerate(standings, 1):
            print(f"{i}. {team.team_name} ({team.wins}-{team.losses})")

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
