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
    logger=logger,
)

# Get all professional players
players = requestor.get_pro_players()

# Get league data
league_data = requestor.get_league()

# Other available methods
pro_schedule = requestor.get_pro_schedule()
pro_projections = requestor.get_pro_projections(filters)
```

#### EspnCoreRequests

Handles ESPN's Core API for detailed professional player data:

```python
from espn_api_extractor.requests.core_requests import EspnCoreRequests

# Initialize the core requestor
core_requestor = EspnCoreRequests(
    sport="mlb",
    year=2025,
    logger=logger,
    max_workers=32,  # Optional: Number of threads to use for player hydration (default: min(32, 4 * CPU cores))
)

# Hydrate player objects with detailed data
hydrated_players, failed_players = core_requestor.hydrate_players(
    player_objects,
    batch_size=100  # Optional: Number of players to process in each batch for progress tracking
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

# Access player attributes
player.name               # Player name
player.id                 # ESPN player ID
player.pro_team           # MLB team (now uses snake_case naming)
player.primary_position   # Position
player.date_of_birth      # Birth date (YYYY-MM-DD format)
player.stats              # Player statistics
# ... and many more attributes after hydration
```

### Runners

The package includes command-line runners for extracting data:

#### Player Runner

There are multiple ways to run the player extractor:

```bash
# Option 1: Using the installed command-line script
espn-players --year 2025 --threads 32 --batch-size 100

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
3. Hydrates those objects with detailed player information via the Core API using multi-threading
4. Returns the fully hydrated player objects

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

# Hydrate players with detailed information using multi-threading
hydrated_players, failed_players = core_requestor.hydrate_players(player_objects, batch_size=100)

# Use the fully hydrated player objects
for player in hydrated_players:
    print(f"{player.name} ({player.pro_team}) - Bats: {player.bats}, Throws: {player.throws}")
```

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
- Support for nested models (e.g., BirthPlace)
- Serialization/deserialization for database storage

## Installation

```bash
pip install espn-api-extractor
```

## Development

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
### Resources
- https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/seasons/2025/segments/0/leagues/10998/?view=kona_player_info
- https://stmorse.github.io/journal/espn-fantasy-v3.html
- http://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/athletes?lang=en&region=us
- http://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/athletes/39832
- http://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/athletes/39832?lang=en&region=us
