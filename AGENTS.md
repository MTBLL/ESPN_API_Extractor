# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands
- Install dependencies: `uv sync --all-extras`
- Run all tests: `uv run pytest tests/`
- Run a single test: `uv run pytest tests/test_file.py::TestClass::test_function`
- Test with coverage: `uv run pytest --cov=espn_api_extractor --cov-report=term-missing` 
- Run mypy type checking: `uv run mypy espn_api_extractor`
- Run mypy with stricter checking: `uv run mypy --check-untyped-defs espn_api_extractor`
- Run the player extractor:
  - `uv run espn player-extract --output_dir ./output`
- Debug with players dump: `uv run python debug_dump_players.py`

## Code Style Guidelines
- **Python Version**: 3.13+
- **Type Annotations**: Use proper type hints for all function parameters and return values
- **Type Checking**: All code must pass mypy type checking
- **Imports**: Group standard library, third-party, and local imports in separate blocks
- **Exceptions**: Use specific exception types and add proper error handling
- **Formatting**: Follow PEP 8 guidelines
- **Classes**: Use proper object-oriented principles with clear inheritance
- **Logging**: Use the Logger class from utils.logger for consistent logging
- **Threading**: Use thread-safe logging with locks when implementing multi-threading
- **Testing**: Create comprehensive tests with pytest fixtures and mocks
- **Documentation**: Add docstrings to all classes and methods

## DEVELOPMENT TODO LIST

---

## ✅ BRANCH: feature/mtbl-121-correct-hierarchy-and-namespace - COMPLETED (Dec 2025)

### Summary
This branch successfully corrected the data flow and control hierarchy for the ESPN API Extractor. All critical architecture components are now implemented and all tests are passing.

### Key Accomplishments

#### 1. Architecture Implementation (Runner → Controller → Handlers)
- ✅ **PlayerExtractRunner**: Full extraction workflow with GraphQL optimization
- ✅ **PlayerController**: Strategic routing between update vs full hydration
- ✅ **UpdatePlayerHandler**: Selective updates for existing players
- ✅ **FullHydrationHandler**: Complete extraction for new players

#### 2. Data Structure Fixes
- ✅ Implemented stats processing in `Player.__init__` with STATS_MAP
- ✅ Fixed SeasonStats model → dict conversion in `Player.from_model()`
- ✅ Added field validators for stats keys and injured field
- ✅ All PlayerModel projection fields working correctly

#### 4. Tooling Migration
- ✅ Migrated from Poetry to UV
- ✅ Fixed all mypy type errors (Optional types in handlers)
- ✅ Updated pyproject.toml to standard PEP 621 format
- ✅ Fixed CLI entry point with async wrapper

#### 5. Code Quality
- ✅ All mypy checks pass
- ✅ Proper type annotations with Optional types
- ✅ Extract-only design (no database mutations)
- ✅ Clean separation of concerns

---

### IMMEDIATE FIXES (Must complete to get system working)

#### 1. Fix Test Failures ✅ COMPLETED (Dec 2025)
- [x] **PlayerModel Schema Issues** - ALL FIXED
  - [x] Fix stats dictionary key validation (expects string keys, gets int `0`) ✅
    - Fixed by field validator in `player_model.py:158-166`
    - Validator automatically converts integer keys to strings
    - Test: `test_player_model_from_dict` verifies this works
  - [x] Add missing `projections` field to PlayerModel ✅
    - Field exists at `player_model.py:110-114`
    - Multiple projection fields: `projections`, `preseason_stats`, `regular_season_stats`, `previous_season_stats`
    - Tests: All 11 tests in `TestPlayerModelProjections` pass
  - [x] Fix `injured` field validation (boolean required, gets None) ✅
    - Fixed by field validator in `player_model.py:150-156`
    - Validator converts None to False automatically
    - Test: `test_player_from_model_with_hasura_fixture` verifies this works
  - [x] Ensure tests use correct Player hydration methods before accessing stats ✅
    - All hydration methods properly initialize stats structure (`player.py:309-357`)
    - Implemented stats processing in `Player.__init__` (`player.py:53-89`)
    - Fixed SeasonStats round-trip conversion in `Player.from_model()` (`player.py:175-177`)
    - Test results: **ALL TESTS PASSING** - 36/36 player tests, 16/16 model tests, 32/32 requests tests

#### 2. Complete Refactoring Architecture ✅ COMPLETED (Dec 2025)
- [x] **PlayerExtractRunner** (runners/player_extract_runner.py) ✅
  - [x] Setup Hasura/GraphQL connection initialization
  - [x] Handle GraphQL client configuration and connection testing
  - [x] Control overall extraction workflow
  - [x] Save results to JSON (Extract-only, no GraphQL mutations)

- [x] **PlayerController** (controllers/player_controller.py) ✅
  - [x] **DESIGN FINALIZED**: Unified interface with strategic routing
  - [x] Implement `execute(existing_players: List[Player])` method
  - [x] Single ESPN API call to get all current players
  - [x] Route existing players → UpdatePlayerHandler (selective updates)
  - [x] Route new players → FullHydrationHandler (complete hydration)
  - [x] Return unified `{"players": [Player, ...], "failures": [...]}`
  - [x] Consumer gets clean interface regardless of update vs new player source

- [x] **Handlers** (handlers/) ✅
  - [x] **UpdatePlayerHandler**: Selective updates for existing players
    - [x] Uses pro_players data for quick updates
    - [x] Optional stats refresh from Core API
    - [x] Proper type annotations with Optional types
  - [x] **FullHydrationHandler**: Complete extraction for new players
    - [x] Fantasy API calls (get_pro_players, get_player_cards)
    - [x] Multi-threaded Core API hydration (bio + stats)
    - [x] Player object hydration pipeline
    - [x] Error handling and retry logic

### ARCHITECTURE IMPLEMENTATION ✅ COMPLETED (Dec 2025)

#### 3. Runner Responsibilities ✅
- [x] **Hasura Connection Management** ✅
  - [x] Initialize GraphQL client with config (`requests/graphql_requests.py`)
  - [x] Test connection and HITL fallback handling
  - [x] Maintain connection throughout extraction process

- [x] **Pre-Extraction Analysis** ✅
  - [x] Query existing player IDs from Hasura
  - [x] Determine extraction strategy (full vs incremental)
  - [x] Pass optimization data to controller

- [x] **Post-Extraction Data Save** ✅
  - [x] Save extracted players to JSON files (`_save_extraction_results()`)
  - [x] Timestamp-based output files
  - [x] Separate failure logging
  - Note: GraphQL mutations moved to separate Transform/Load apps (Extract-only design)

#### 4. Controller Responsibilities ✅ COMPLETED
- [x] **Strategic Decision Making** ✅
  - [x] Single ESPN API call to get all current players
  - [x] Compare ESPN player list vs Hasura existing IDs
  - [x] Split into existing vs new players for optimal processing
  - [x] ESPN is single source of truth (fantasy league hosted there)

- [x] **Handler Orchestration Strategy** ✅
  - [x] **UpdatePlayerHandler**: Selective updates for existing players (stats, team, fantasy team, injury, positions, ownership)
  - [x] **FullHydrationHandler**: Complete player data extraction for new players
  - [x] Both handlers return List[Player] objects only
  - [x] Collect results into unified list - consumer doesn't care about source
  - [x] Track failures with descriptive messages ("Player ID X in Hasura but not found in ESPN")

- [x] **Implementation Details** ✅
  - [x] Process existing player updates first, then new players 
  - [x] All processing in-memory, no direct Hasura mutations
  - [x] Serialize final unified player list to local JSON for transformation workflow

#### 5. Handler Responsibilities ✅ COMPLETED
- [x] **Complete ESPN API Workflow** ✅
  - [x] Execute ESPN API calls in correct sequence
  - [x] Handle ESPN API rate limiting and errors (retry logic in `core_requests.py`)
  - [x] Manage multi-threaded hydration process (ThreadPoolExecutor with configurable workers)
  - [x] Return fully hydrated Player objects

- [x] **Data Processing Pipeline** ✅
  - [x] ESPN Fantasy API: get_pro_players() -> Player objects
  - [x] ESPN Fantasy API: get_player_cards() -> kona hydration
  - [x] ESPN Core API: parallel bio + stats hydration
  - [x] PlayerModel conversion and validation

### DATA STRUCTURE FIXES ✅ COMPLETED (Dec 2025)

#### 6. PlayerModel Schema Updates ✅
- [x] **Add Missing Fields** ✅
  - [x] Add `projections: Dict[str, float]` field for direct access 
  - [x] Ensure all kona_playercard fields are properly mapped
  - [x] Add proper validation for all data types

- [x] **Fix Stats Structure** ✅
  - [x] Ensure stats uses string keys: `{"projections": {...}, "preseason": {...}}`
  - [x] Field validator converts integer keys to strings 
  - [x] Update tests to match actual data structure ✅
  - [x] Add validation for nested stats dictionaries

#### 7. Player Class Improvements ✅ COMPLETED
- [x] **Hydration Method Consistency** ✅
  - [x] Ensure all hydration methods properly initialize stats structure
  - [x] Implemented stats processing in `Player.__init__` 
    - Filters by current year and season stats (statSplitTypeId 0 or 5)
    - Maps statSourceId: 0 = actual, 1 = projected
    - Maps numeric stat keys to readable names using STATS_MAP
  - [x] Add validation for required fields during hydration
  - [x] Handle None values appropriately (especially `injured` field)
  - [x] Fixed SeasonStats model → dict conversion in `from_model()` 

#### 9. Performance Optimization
- [ ] **GraphQL Efficiency**
  - [ ] Implement batch mutations for multiple player updates
  - [ ] Use GraphQL fragments for consistent field selection
  - [ ] Add connection pooling for GraphQL client

- [ ] **ESPN API Optimization**  
  - [ ] Maintain existing multi-threading for Core API calls
  - [ ] Add intelligent retry logic with exponential backoff
  - [ ] Implement request caching where appropriate

### CONFIGURATION & DEPLOYMENT ✅ COMPLETED (Dec 2025)

#### 10. Configuration Management ✅
- [x] **GraphQL Configuration** ✅
  - [x] GraphQL client with HITL validation (`requests/graphql_requests.py`)
  - [x] Configuration file support (`hasura_config.json`)
  - [x] Document GraphQL endpoint requirements

- [x] **CLI Command Updates** ✅
  - [x] **MIGRATED FROM POETRY TO UV** ✅
  - [x] Updated `pyproject.toml` to standard PEP 621 format
  - [x] Updated all CLI commands in CLAUDE.md Build & Test Commands section
  - [x] Fixed entry point: `espn = "espn_api_extractor.__main__:cli_main"`
  - [x] Added sync wrapper for async main function
  - [x] Test all entry points work correctly
  - [x] Fixed mypy type errors (Optional types in handlers)
  - [x] Updated `.claude/settings.local.json` with uv permissions

### PRIORITY ORDER
1. ✅ **CRITICAL**: Fix test failures (items 1, 6, 8) - COMPLETED
2. ✅ **HIGH**: Complete Controller implementation (item 2, 4) - COMPLETED
3. ✅ **HIGH**: Expand Handler functionality (item 2, 5) - COMPLETED
4. ✅ **MEDIUM**: Runner GraphQL integration (items 3) - COMPLETED
5. **LOW**: Performance optimization (item 9) - Not needed for this branch
6. ✅ **LOW**: Configuration improvements (item 10) - COMPLETED (UV migration)

### ARCHITECTURE FLOW
```
Runner (Setup Hasura) -> Controller (Strategic Decisions) -> Handler (ESPN Execution) -> Controller (Data Return) -> Runner (GraphQL Updates)
```

This ensures clean separation of concerns:
- **Runner**: Infrastructure (GraphQL connection, final updates)
- **Controller**: Business logic (what to extract, how to optimize)  
- **Handler**: Technical execution (ESPN API calls, data processing)
