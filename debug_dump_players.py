#!/usr/bin/env python3
import json
import argparse
from espn_api_extractor.runners.players import main as players_main
from espn_api_extractor.models.player_model import PlayerModel

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
        f"--batch-size={args.batch_size}"
    ]
    
    print(f"Getting player data with {args.threads} threads...")
    players = players_main()
    
    if not players:
        print("No players returned. Check the logs for errors.")
        return
    
    print(f"Got {len(players)} players, saving {min(args.sample, len(players))} to {args.output}")
    
    # Take a sample of players to keep the file size reasonable
    sample_size = min(args.sample, len(players))
    sample_players = players[:sample_size]
    
    # Convert player objects to Pydantic models
    player_models = [player.to_model() for player in sample_players]
    
    # Serialize to JSON
    if args.pretty:
        # Pretty print with indentation
        json_data = "[\n"
        for i, model in enumerate(player_models):
            model_json = model.model_dump_json(indent=2)
            json_data += "  " + model_json.replace("\n", "\n  ")
            if i < len(player_models) - 1:
                json_data += ",\n"
            else:
                json_data += "\n"
        json_data += "]\n"
        
        with open(args.output, 'w') as f:
            f.write(json_data)
    else:
        # Use standard JSON serialization
        json_list = [model.model_dump() for model in player_models]
        with open(args.output, 'w') as f:
            json.dump(json_list, f, indent=2)
    
    print(f"Saved {len(player_models)} players to {args.output}")
    
    # Print a summary of what attributes are available
    example_model = player_models[0].model_dump() if player_models else {}
    all_keys = sorted(example_model.keys())
    
    print("\nAvailable player attributes:")
    for key in all_keys:
        print(f"- {key}")

if __name__ == "__main__":
    main()