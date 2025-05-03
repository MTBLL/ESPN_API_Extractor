# ESPN Baseball API Extractor

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
player.name        # Player name
player.id          # ESPN player ID
player.proTeam     # MLB team
player.stats       # Player statistics
# ... and many more attributes after hydration
```

### Runners

The package includes command-line runners for extracting data:

#### Player Runner

```bash
python -m espn_api_extractor.runners.players --year 2025 --threads 32 --batch-size 100
```

Command-line options:
- `--year`: League year (default: 2025)
- `--threads`: Number of threads to use for player hydration (default: 4x CPU cores)
- `--batch-size`: Number of players to process in each batch for progress tracking (default: 100)

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
    print(f"{player.name} ({player.proTeam}) - Bats: {player.bats}, Throws: {player.throws}")
```

### Using with Pydantic (Future Feature)

The hydrated Player objects are designed to be easily serializable with Pydantic:

```python
# Example of future Pydantic integration
from pydantic import BaseModel

class PlayerModel(BaseModel):
    id: int
    name: str
    team: str
    position: str
    # ... other fields

# Convert hydrated Player objects to Pydantic models
player_models = [PlayerModel.model_validate(player.__dict__) for player in hydrated_players]
```

## Installation

```bash
pip install espn-api-extractor
```

## Credits

This project builds upon the work of:
- https://github.com/cwendt94/espn-api
- https://github.com/EnderLocke/pyespn/blob/dev/pyespn/sports/sports.py
