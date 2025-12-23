# ESPN Baseball API Extractor
[![codecov](https://codecov.io/gh/MTBLL/ESPN_API_Extractor/graph/badge.svg?token=ZfastHrmnz)](https://codecov.io/gh/MTBLL/ESPN_API_Extractor)
[![Mypy Type Check](https://github.com/MTBLL/ESPN_API_Extractor/actions/workflows/mypy.yml/badge.svg)](https://github.com/MTBLL/ESPN_API_Extractor/actions/workflows/mypy.yml)

A Python library for interacting with ESPN's Fantasy and Core APIs to extract detailed baseball player and league data.

## Architecture

The ESPN API Extractor is organized around two main API integrations:

1. **Fantasy API** - For fantasy league data, teams, and players
2. **Core API** - For detailed ESPN professional player data

### API Interface Classes

#### EspnFantasyRequests

Handles all Fantasy ESPN API interactions:

```python
from espn_api_extractor.requests.fantasy_requests import EspnFantasyRequests

# Initialize the requestor
requestor = EspnFantasyRequests(
    sport="mlb",
    year=2025,
    league_id=None,  # Set league_id for specific league data
    cookies={},      # For private leagues, provide espn_s2 and SWID cookies
)

# Get all professional players
players = requestor.get_pro_players()

# Get comprehensive kona_playercard data (projections, seasonal stats, fantasy info, outlook)
player_cards = requestor.get_player_cards([42404, 39832])  # Pass list of player IDs

# Get league data
league_data = requestor.get_league()

# Other available methods
pro_schedule = requestor.get_pro_schedule()
```

#### EspnCoreRequests

Handles ESPN's Core API for detailed professional player data:

```python
from espn_api_extractor.requests.core_requests import EspnCoreRequests

# Initialize the core requestor
core_requestor = EspnCoreRequests(
    sport="mlb",
    year=2025,
    max_workers=32,  # Optional: Number of threads to use for player hydration (default: min(32, 4 * CPU cores))
)

# Option 1: Hydrate player objects with biographical data only (default)
hydrated_players, failed_players = core_requestor.hydrate_players(
    player_objects,
    batch_size=100  # Optional: Number of players to process in each batch for progress tracking
)

# Option 2: Hydrate player objects with both biographical data AND statistics (recommended)
complete_players, failed_players = core_requestor.hydrate_players(
    player_objects,
    batch_size=100,  # Optional: Number of players to process in each batch for progress tracking
    include_stats=True  # Include both biographical data and statistics in a single efficient pass
)
```

### Data Models

The library features OOP data models that represent various entities:

#### Player

```python
from espn_api_extractor.baseball.player import Player

# Create a player from API data
player = Player(player_data)

# Hydrate with additional detailed data
player.hydrate(detailed_data)

# Hydrate with statistics data
player.hydrate_statistics(statistics_data)

# Hydrate with comprehensive kona_playercard data (projections, seasonal stats, fantasy info)
player.hydrate_kona_playercard(player_card_data)

# Access player attributes
player.name                  # Player name
player.id                    # ESPN player ID
player.pro_team              # MLB team (now uses snake_case naming)
player.primary_position      # Position
player.date_of_birth         # Birth date (YYYY-MM-DD format)
player.stats                 # Basic player statistics
player.season_stats          # Detailed player statistics from ESPN Core API

# Comprehensive kona_playercard data attributes
player.season_outlook        # Season outlook narrative text
player.projections           # 2025 projected statistics (mapped to readable names)
player.preseason_stats       # 2025 preseason statistics
player.regular_season_stats  # 2025 regular season statistics  
player.previous_season_stats # 2024 season statistics

# Fantasy-specific kona_playercard attributes
player.draft_auction_value   # Draft auction value
player.on_team_id           # Fantasy team ID
player.draft_ranks          # Draft rankings by type (ROTO, STANDARD)
player.games_played_by_position  # Games played by position (mapped to readable names)
player.auction_value_average     # Ownership auction value average
# ... and many more attributes after hydration

# Access detailed statistics
batting_stats = player.season_stats["categories"]["batting"]
batting_summary = batting_stats["summary"]  # "55-197, 14 HR, 5 3B, 9 2B, 32 RBI, 38 R, 18 BB, 9 SB, 53 K"
avg = batting_stats["stats"]["avg"]["value"]  # 0.2791878
avg_display = batting_stats["stats"]["avg"]["display_value"]  # ".279"
hr = batting_stats["stats"]["homeRuns"]["value"]  # 14.0
rank = batting_stats["stats"]["homeRuns"]["rank_display_value"]  # "Tied-5th"
```

### Runners

The package includes command-line runners for extracting data:

#### Player Runner

There are multiple ways to run the player extractor:

```bash
# Option 1: Using the installed command-line script
espn-extract players-extract --year 2025 --threads 32 --batch-size 100

# Option 2: Using the Python module directly
python -m espn_api_extractor.players --year 2025 --threads 32 --batch-size 100

# Option 3: Using the full path to the runner
python -m espn_api_extractor.runners.players --year 2025 --threads 32 --batch-size 100
```

Command-line options:
- `--year`: League year (default: 2025)
- `--threads`: Number of threads to use for player hydration (default: 4x CPU cores)
- `--batch-size`: Number of players to process in each batch for progress tracking (default: 100)
- `--output_dir`: Directory to write JSON output. If not specified, no file is written
- `--as-models`: Return Pydantic models instead of Player objects (default: False)

This script:
1. Fetches all professional baseball players via the Fantasy API
2. Creates Player objects from the data
3. Fetches comprehensive kona_playercard data (projections, seasonal stats, fantasy info, outlook) for all players
4. Hydrates those objects with detailed player information via the Core API using multi-threading
5. Returns the fully hydrated player objects with complete data

## Usage Examples

### Get and Hydrate All Players

```python
from espn_api_extractor.baseball.player import Player
from espn_api_extractor.requests.fantasy_requests import EspnFantasyRequests
from espn_api_extractor.requests.core_requests import EspnCoreRequests
from espn_api_extractor.utils.logger import Logger

# Setup
logger = Logger("my-script")
fantasy_requestor = EspnFantasyRequests(sport="mlb", year=2025, league_id=None, cookies={}, logger=logger)
core_requestor = EspnCoreRequests(sport="mlb", year=2025, logger=logger, max_workers=32)

# Get basic player data
players_data = fantasy_requestor.get_pro_players()
player_objects = [Player(player) for player in players_data]

# Fetch comprehensive kona_playercard data
player_ids = [player.id for player in player_objects if player.id is not None]
player_cards_data = fantasy_requestor.get_player_cards(player_ids)

# Create lookup for player card data and top-level data
player_cards_lookup = {}
top_level_lookup = {}
for player_data in player_cards_data.get("players", []):
    player_id = player_data.get("id")
    if player_id:
        player_cards_lookup[player_id] = player_data.get("player", {})
        # Store top-level fantasy data separately
        top_level_lookup[player_id] = {
            "draftAuctionValue": player_data.get("draftAuctionValue"),
            "onTeamId": player_data.get("onTeamId")
        }

# Hydrate each player with comprehensive kona_playercard data
for player in player_objects:
    if player.id in player_cards_lookup:
        player.hydrate_kona_playercard(
            player_cards_lookup[player.id],
            top_level_lookup.get(player.id, {})
        )

# Then hydrate players with biographical data only
hydrated_players, failed_players = core_requestor.hydrate_players(player_objects, batch_size=100)

# Or hydrate with both biographical data and statistics (more efficient for complete data)
complete_players, failed_players = core_requestor.hydrate_players(player_objects, batch_size=100, include_stats=True)

# Use the fully hydrated player objects
for player in complete_players:
    print(f"{player.name} ({player.pro_team}) - Bats: {player.bats}, Throws: {player.throws}")
    
    # Access comprehensive kona_playercard data
    if hasattr(player, 'season_outlook') and player.season_outlook:
        print(f"Season Outlook: {player.season_outlook[:100]}...")  # First 100 chars
    
    if hasattr(player, 'projections') and player.projections:
        proj_hr = player.projections.get('HR', 'N/A')
        proj_ab = player.projections.get('AB', 'N/A') 
        proj_sb = player.projections.get('SB', 'N/A')
        print(f"2025 Projections: {proj_ab} AB, {proj_hr} HR, {proj_sb} SB")
    
    if hasattr(player, 'previous_season_stats') and player.previous_season_stats:
        prev_hr = player.previous_season_stats.get('HR', 'N/A')
        prev_ab = player.previous_season_stats.get('AB', 'N/A')
        print(f"2024 Stats: {prev_ab} AB, {prev_hr} HR")
    
    # Access fantasy-specific kona_playercard data
    if hasattr(player, 'draft_auction_value') and player.draft_auction_value is not None:
        print(f"Draft Auction Value: ${player.draft_auction_value}")
    
    if hasattr(player, 'draft_ranks') and player.draft_ranks:
        roto_rank = player.draft_ranks.get('ROTO', {}).get('rank', 'N/A')
        standard_rank = player.draft_ranks.get('STANDARD', {}).get('rank', 'N/A')
        print(f"Draft Rankings - ROTO: {roto_rank}, STANDARD: {standard_rank}")
    
    if hasattr(player, 'games_played_by_position') and player.games_played_by_position:
        pos_games = ", ".join([f"{pos}: {games}" for pos, games in player.games_played_by_position.items()])
        print(f"Games by Position: {pos_games}")
    
    # Access player statistics (if available)
    if hasattr(player, 'season_stats') and player.season_stats:
        batting = player.season_stats.get('categories', {}).get('batting')
        if batting and 'stats' in batting:
            avg = batting['stats'].get('avg', {}).get('display_value', 'N/A')
            hr = batting['stats'].get('homeRuns', {}).get('display_value', 'N/A')
            rbi = batting['stats'].get('RBIs', {}).get('display_value', 'N/A')
            print(f"Detailed Stats: AVG: {avg}, HR: {hr}, RBI: {rbi}")
```

## Comprehensive Kona PlayerCard Data

The ESPN API Extractor supports fetching comprehensive player card data from ESPN's `kona_playercard` endpoint, which includes projections, seasonal statistics, fantasy information, and expert analysis. This data is fetched before the standard biographical hydration.

### Kona PlayerCard Data Includes:

**Statistical Data:**
- **Season Outlook**: Expert analysis and narrative text about the player's upcoming season
- **2025 Projections**: Projected statistics for the current season (mapped to readable names)
- **2025 Preseason Stats**: Spring training statistics 
- **2025 Regular Season Stats**: Current regular season statistics
- **2024 Previous Season Stats**: Complete previous season statistics

**Fantasy-Specific Data:**
- **Draft Auction Value**: Player's draft auction value
- **On Team ID**: Fantasy team assignment (0 if not on a team)
- **Draft Rankings**: Rankings by type (ROTO and STANDARD) with auction values and ranks
- **Games Played by Position**: Games played at each position (mapped to readable position names)
- **Auction Value Average**: Ownership data including auction value average
- **Updated Injury Status**: Current injury status and injured flag

### Usage Example:

```python
from espn_api_extractor.requests.fantasy_requests import EspnFantasyRequests

# Initialize requestor
requestor = EspnFantasyRequests(sport="mlb", year=2025, logger=logger)

# Get player cards for specific players
player_ids = [42404, 39832]  # Corbin Carroll, Shohei Ohtani
player_cards_data = requestor.get_player_cards(player_ids)

# Process the data
for player_data in player_cards_data["players"]:
    player_info = player_data["player"]
    
    # Access season outlook
    outlook = player_info.get("seasonOutlook", "")
    print(f"Season Outlook: {outlook[:200]}...")
    
    # Access different stat types
    for stat_entry in player_info.get("stats", []):
        stat_id = stat_entry.get("id", "")
        
        if stat_id == "102025":  # Projections
            projections = stat_entry.get("stats", {})
            print(f"Projected HR: {projections.get('5', 'N/A')}")  # '5' maps to HR
            
        elif stat_id == "002024":  # Previous season
            prev_stats = stat_entry.get("stats", {})
            print(f"2024 HR: {prev_stats.get('5', 'N/A')}")
```

### Automatic Integration in Player Runner

The player runner automatically fetches comprehensive kona_playercard data for all players before biographical hydration, so you get all statistical, fantasy, and outlook data automatically when using the command-line runner or the main extraction workflow.

### Stat Key Mapping and Unknown Key Filtering

All numeric stat keys are automatically mapped to readable names using the `STATS_MAP` constants. Unknown numeric keys (like "22") are automatically filtered out to ensure only clean, readable stat names are stored:

```python
from espn_api_extractor.baseball.constants import STATS_MAP

# Examples of stat key mappings:
# 0 -> "AB" (At Bats)
# 1 -> "H" (Hits) 
# 5 -> "HR" (Home Runs)
# 23 -> "SB" (Stolen Bases)
# Unknown keys like "22" are automatically ignored

# Access mapped stats from player objects - only readable names, no numeric keys
if player.projections:
    projected_hrs = player.projections.get("HR", 0)  # Readable key
    projected_abs = player.projections.get("AB", 0)
    
    # All stat dictionaries contain only known, readable stat names
    for stat_name, value in player.projections.items():
        print(f"{stat_name}: {value}")  # e.g., "HR: 25", "AB: 450"
```

## Hydration Options

The `hydrate_players` method provides flexible options for data collection:

### Biographical Data Only (Default)
```python
# Fast hydration with basic player information
hydrated_players, failed_players = core_requestor.hydrate_players(player_objects)

# Available data: name, team, position, physical stats, etc.
for player in hydrated_players:
    print(f"{player.display_name} - {player.pro_team} ({player.position})")
```

### Complete Data (Biographical + Statistics)
```python
# Comprehensive hydration with both bio and stats in a single efficient pass
complete_players, failed_players = core_requestor.hydrate_players(
    player_objects, 
    include_stats=True
)

# Available data: everything above PLUS season statistics
for player in complete_players:
    print(f"{player.display_name} - {player.pro_team}")
    if hasattr(player, 'season_stats'):
        batting = player.season_stats.get('categories', {}).get('batting', {})
        if batting:
            avg = batting.get('stats', {}).get('avg', {}).get('display_value', 'N/A')
            hrs = batting.get('stats', {}).get('homeRuns', {}).get('value', 'N/A')
            print(f"  Stats: {avg} AVG, {hrs} HR")
```

### Performance Considerations
- **Biographical only**: ~1-2 API calls per player, faster execution
- **Complete data**: ~2-3 API calls per player, single-pass threading for efficiency
- **Multi-threading**: Automatically uses optimal thread count (4x CPU cores, max 32)

### Using with Pydantic Models

The Player objects can be easily converted to and from Pydantic models for validation, serialization, and database integration:

```python
from espn_api_extractor.models.player_model import PlayerModel
from espn_api_extractor.baseball.player import Player
from espn_api_extractor.utils.utils import write_models_to_json

# Convert a Player object to a Pydantic model
player_model = player.to_model()

# Serialize to JSON
json_data = player_model.model_dump_json()

# Deserialize from JSON
deserialized_model = PlayerModel.model_validate_json(json_data)

# Convert back to a Player object
player_object = Player.from_model(player_model)

# Batch convert multiple Player objects
player_models = [player.to_model() for player in hydrated_players]

# Write models to a JSON file
write_models_to_json(player_models, "output_directory", "espn_player_universe.json")
```

The Pydantic model handles various data validation tasks and provides:
- Clean date format handling (YYYY-MM-DD)
- Proper type validation for all fields
- Standardized snake_case property naming
- Support for nested models (e.g., BirthPlace, StatCategory, StatDetail)
- Structured statistics data with dedicated models (SeasonStats)
- **Comprehensive kona_playercard data**: season_outlook, projections, preseason_stats, regular_season_stats, previous_season_stats
- **Fantasy-specific fields**: draft_auction_value, on_team_id, draft_ranks, games_played_by_position, auction_value_average
- Serialization/deserialization for database storage

#### Statistics Models

```python
from espn_api_extractor.models.player_model import PlayerModel, SeasonStats, StatCategory, StatDetail

# Access statistics through the Pydantic model
player_model = player.to_model()

# Check if statistics are available
if player_model.season_stats:
    # Access batting statistics
    if "batting" in player_model.season_stats.categories:
        batting = player_model.season_stats.categories["batting"]
        
        # Summary of batting performance
        batting_summary = batting.summary  # "55-197, 14 HR, 5 3B, 9 2B, 32 RBI, 38 R, 18 BB, 9 SB, 53 K"
        
        # Access specific statistics
        if "avg" in batting.stats:
            avg_stat = batting.stats["avg"]
            avg_value = avg_stat.value  # 0.2791878
            avg_display = avg_stat.display_value  # ".279"
            avg_rank = avg_stat.rank_display_value  # "Tied-49th"

# Access comprehensive kona_playercard data through the model
if player_model.season_outlook:
    print(f"Season Outlook: {player_model.season_outlook[:100]}...")

if player_model.projections:
    projected_hrs = player_model.projections.get("HR", 0)
    projected_abs = player_model.projections.get("AB", 0)
    print(f"2025 Projections: {projected_abs} AB, {projected_hrs} HR")

if player_model.previous_season_stats:
    prev_hrs = player_model.previous_season_stats.get("HR", 0)  
    prev_abs = player_model.previous_season_stats.get("AB", 0)
    print(f"2024 Stats: {prev_abs} AB, {prev_hrs} HR")

# Access fantasy-specific kona_playercard data through the model
if player_model.draft_auction_value is not None:
    print(f"Draft Auction Value: ${player_model.draft_auction_value}")

if player_model.draft_ranks:
    roto_rank = player_model.draft_ranks.get("ROTO", {}).get("rank", "N/A")
    roto_value = player_model.draft_ranks.get("ROTO", {}).get("auctionValue", "N/A")
    print(f"ROTO Ranking: #{roto_rank} (${roto_value})")

if player_model.games_played_by_position:
    for position, games in player_model.games_played_by_position.items():
        print(f"{position}: {games} games")

if player_model.auction_value_average is not None:
    print(f"Auction Value Average: ${player_model.auction_value_average:.2f}")
```

## Installation

```bash
pip install espn-api-extractor
```

## Development

### Debug Tools

The repository includes debug scripts to help test functionality:

```bash
# Test player statistics fetching
poetry run python debug_stats_fetch.py
```

This script:
1. Fetches a small number of players from the Fantasy API
2. Hydrates them with basic information using the Core API
3. Hydrates them with statistics using the new statistics endpoint
4. Prints out key statistics for each player
5. Saves the player models to JSON files in a debug_output directory

### Type Checking

This project uses mypy for static type checking to catch potential type-related errors:

```bash
# Run mypy on the codebase
poetry run mypy espn_api_extractor

# Run mypy with stricter checking of untyped function bodies
poetry run mypy --check-untyped-defs espn_api_extractor
```

Type checking is enforced via GitHub Actions on all pull requests to ensure type consistency. All code must pass mypy checks before it can be merged to the main branch.

## Credits

This project builds upon the work of:
- https://github.com/cwendt94/espn-api
- https://github.com/EnderLocke/pyespn/blob/dev/pyespn/sports/sports.py
- https://stmorse.github.io/journal/espn-fantasy-v3.html
### Resources
- https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/seasons/2025/segments/0/leagues/10998/?view=kona_player_info
- http://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/athletes?lang=en&region=us
- http://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/athletes/39832
- http://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/athletes/39832?lang=en&region=us
- https://appac.github.io/mlb-data-api-docs/
