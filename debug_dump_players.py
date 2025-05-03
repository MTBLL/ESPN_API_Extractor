#!/usr/bin/env python3
import json
import argparse
from espn_api_extractor.runners.players import main as players_main

def player_to_dict(player):
    """Convert a Player object to a dict for JSON serialization"""
    result = {}
    for attr in dir(player):
        # Skip private/special attributes and methods
        if not attr.startswith('_') and not callable(getattr(player, attr)):
            try:
                value = getattr(player, attr)
                # Handle special cases for serialization
                if isinstance(value, set):
                    value = list(value)
                result[attr] = value
            except Exception as e:
                # If we can't serialize, convert to string
                result[attr] = f"[Not serializable: {str(e)}]"
    return result

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
    
    args = parser.parse_args()
    
    # Set args for the player module to use
    import sys
    sys.argv = [
        sys.argv[0], 
        f"--year={args.year}", 
        f"--threads={args.threads}", 
        f"--batch-size={args.batch_size}"
    ]
    
    print(f"Getting player data with {args.threads} threads...")
    players = players_main()
    
    if not players:
        print("No players returned. Check the logs for errors.")
        return
    
    print(f"Got {len(players)} players, saving {min(args.sample, len(players))} to {args.output}")
    
    # Convert player objects to dicts for JSON serialization
    # Just use a sample of players to keep the file size reasonable
    sample_size = min(args.sample, len(players))
    players_data = [player_to_dict(player) for player in players[:sample_size]]
    
    # Save to JSON
    with open(args.output, 'w') as f:
        json.dump(players_data, f, indent=2, default=str)
    
    print(f"Saved {len(players_data)} players to {args.output}")
    
    # Print a summary of what attributes are available
    all_keys = set()
    for player_dict in players_data:
        all_keys.update(player_dict.keys())
    
    print("\nAvailable player attributes:")
    for key in sorted(all_keys):
        print(f"- {key}")

if __name__ == "__main__":
    main()