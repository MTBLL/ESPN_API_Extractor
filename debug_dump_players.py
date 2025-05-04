#!/usr/bin/env python3
import argparse
from espn_api_extractor.runners.players import main as players_main

def main():
    parser = argparse.ArgumentParser(description="Get player data and save to JSON for debugging")
    
    parser.add_argument(
        "--year", type=int, default=2025, help="League year (default: 2025)"
    )
    parser.add_argument(
        "--threads", type=int, default=16, 
        help="Number of threads to use for player hydration (default: 16)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=100,
        help="Number of players to process in each batch (default: 100)"
    )
    parser.add_argument(
        "--output", type=str, default="test.json",
        help="Output JSON file path (default: test.json)"
    )
    parser.add_argument(
        "--sample", type=int, default=20,
        help="Number of players to include in the sample (default: 20)"
    )
    parser.add_argument(
        "--pretty", action="store_true",
        help="Output pretty-printed (indented) JSON (default: False)"
    )
    
    args = parser.parse_args()
    
    # Set args for the player module to use
    import sys
    sys.argv = [
        sys.argv[0], 
        f"--year={args.year}", 
        f"--threads={args.threads}", 
        f"--batch-size={args.batch_size}",
        "--as-models",  # Always use Pydantic models for serialization
        f"--output={args.output}"  # Pass the output file path
    ]
    
    if args.pretty:
        sys.argv.append("--pretty")
    
    print(f"Getting player data with {args.threads} threads...")
    # Pass the sample size to limit API calls and get models directly
    player_models = players_main(sample_size=args.sample)
    
    if not player_models:
        print("No players returned. Check the logs for errors.")
        return
    
    print(f"Got {len(player_models)} players and saved to {args.output}")
    
    # Print a summary of what attributes are available
    example_model = player_models[0].model_dump() if player_models else {}
    all_keys = sorted(example_model.keys())
    
    print("\nAvailable player attributes:")
    for key in all_keys:
        print(f"- {key}")

if __name__ == "__main__":
    main()