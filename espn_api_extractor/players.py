#!/usr/bin/env python3
"""
Direct entrypoint for running the player extractor with python -m espn_api_extractor.players
"""

from espn_api_extractor.runners.players import main

if __name__ == "__main__":
    # main function signature now accepts sample_size and output_dir
    # all other parameters are handled via command-line arguments
    main()