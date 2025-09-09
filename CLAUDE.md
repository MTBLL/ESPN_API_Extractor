# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands
- Install dependencies: `poetry install`
- Run all tests: `poetry run pytest tests/`
- Run a single test: `poetry run pytest tests/test_file.py::TestClass::test_function`
- Test with coverage: `poetry run pytest --cov=espn_api_extractor --cov-report=xml tests/`
- Run mypy type checking: `poetry run mypy espn_api_extractor`
- Run mypy with stricter checking: `poetry run mypy --check-untyped-defs espn_api_extractor`
- Run the player extractor (any of these options works):
  - `poetry run espn-players --output_dir ./output`
  - `poetry run python -m espn_api_extractor.players --output_dir ./output`
  - `poetry run python -m espn_api_extractor.runners.players --output_dir ./output`
- Debug with players dump: `poetry run python debug_dump_players.py`

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

### IMMEDIATE FIXES (Must complete to get system working)

#### 1. Fix Test Failures
- [ ] **PlayerModel Schema Issues**
  - [ ] Fix stats dictionary key validation (expects string keys, gets int `0`)
  - [ ] Add missing `projections` field to PlayerModel or fix test expectations
  - [ ] Fix `injured` field validation (boolean required, gets None)
  - [ ] Ensure tests use correct Player hydration methods before accessing stats

#### 2. Complete Refactoring Architecture
- [ ] **PlayerExtractRunner** (runners/player_extract_runner.py)
  - [ ] Setup Hasura/GraphQL connection initialization
  - [ ] Handle GraphQL client configuration and connection testing
  - [ ] Control overall extraction workflow
  - [ ] Handle final GraphQL updates after extraction complete

- [ ] **PlayerController** (controllers/player_controller.py)  
  - [x] **DESIGN FINALIZED**: Unified interface with strategic routing
  - [ ] Implement `execute(existing_player_ids: Set[int])` method
  - [ ] Single ESPN API call to get all current players
  - [ ] Route existing players → UpdatePlayerHandler (selective updates)
  - [ ] Route new players → FullHydrationHandler (complete hydration)
  - [ ] Return unified `{"players": [Player, ...], "failures": [...]}`
  - [ ] Consumer gets clean interface regardless of update vs new player source

- [ ] **PlayerHandler** (handlers/pro_players_handler.py)
  - [ ] Expand beyond just `get_pro_players()`
  - [ ] Handle complete ESPN API extraction workflow:
    - [ ] Fantasy API calls (get_pro_players, get_player_cards)
    - [ ] Multi-threaded Core API hydration (bio + stats)
    - [ ] Player object hydration pipeline
    - [ ] Error handling and retry logic

### ARCHITECTURE IMPLEMENTATION

#### 3. Runner Responsibilities
- [ ] **Hasura Connection Management**
  - [ ] Initialize GraphQL client with config
  - [ ] Test connection and fallback handling
  - [ ] Maintain connection throughout extraction process
  
- [ ] **Pre-Extraction Analysis**
  - [ ] Query existing player IDs from Hasura
  - [ ] Determine extraction strategy (full vs incremental)
  - [ ] Pass optimization data to controller

- [ ] **Post-Extraction GraphQL Updates**  
  - [ ] Efficient GraphQL mutations for new players
  - [ ] Selective field updates for existing players
  - [ ] Batch mutations for optimal performance
  - [ ] Handle GraphQL errors and rollback scenarios

#### 4. Controller Responsibilities (DESIGN COMPLETE)
- [x] **Strategic Decision Making**
  - [x] Single ESPN API call to get all current players  
  - [x] Compare ESPN player list vs Hasura existing IDs
  - [x] Split into existing vs new players for optimal processing
  - [x] ESPN is single source of truth (fantasy league hosted there)

- [x] **Handler Orchestration Strategy**
  - [x] **UpdatePlayerHandler**: Selective updates for existing players (stats, team, fantasy team, injury, positions, ownership)
  - [x] **FullHydrationHandler**: Complete player data extraction for new players  
  - [x] Both handlers return List[Player] objects only
  - [x] Collect results into unified list - consumer doesn't care about source
  - [x] Track failures with descriptive messages ("Player ID X in Hasura but not found in ESPN")

- [ ] **Implementation Details**
  - [ ] Process existing player updates first, then new players
  - [ ] All processing in-memory, no direct Hasura mutations
  - [ ] Serialize final unified player list to local JSON for transformation workflow

#### 5. Handler Responsibilities
- [ ] **Complete ESPN API Workflow**
  - [ ] Execute all 4 ESPN API calls in correct sequence
  - [ ] Handle ESPN API rate limiting and errors
  - [ ] Manage multi-threaded hydration process
  - [ ] Return fully hydrated Player objects

- [ ] **Data Processing Pipeline**
  - [ ] ESPN Fantasy API: get_pro_players() -> Player objects
  - [ ] ESPN Fantasy API: get_player_cards() -> kona hydration
  - [ ] ESPN Core API: parallel bio + stats hydration
  - [ ] PlayerModel conversion and validation

### DATA STRUCTURE FIXES

#### 6. PlayerModel Schema Updates
- [ ] **Add Missing Fields**
  - [ ] Add `projections: Dict[str, float]` field for direct access
  - [ ] Ensure all kona_playercard fields are properly mapped
  - [ ] Add proper validation for all data types

- [ ] **Fix Stats Structure**
  - [ ] Ensure stats uses string keys: `{"projections": {...}, "preseason": {...}}`
  - [ ] Update tests to match actual data structure
  - [ ] Add validation for nested stats dictionaries

#### 7. Player Class Improvements
- [ ] **Hydration Method Consistency**
  - [ ] Ensure all hydration methods properly initialize stats structure
  - [ ] Add validation for required fields during hydration
  - [ ] Handle None values appropriately (especially `injured` field)

### TESTING & VALIDATION

#### 8. Test Suite Fixes
- [ ] **Update Test Data**
  - [ ] Fix stats dictionary structures in test fixtures
  - [ ] Ensure test Player objects are properly hydrated
  - [ ] Update PlayerModel expectations to match schema

- [ ] **Integration Tests**
  - [ ] Test complete Runner -> Controller -> Handler workflow
  - [ ] Test GraphQL optimization scenarios
  - [ ] Test error handling and fallback mechanisms

#### 9. Performance Optimization
- [ ] **GraphQL Efficiency**
  - [ ] Implement batch mutations for multiple player updates
  - [ ] Use GraphQL fragments for consistent field selection
  - [ ] Add connection pooling for GraphQL client

- [ ] **ESPN API Optimization**  
  - [ ] Maintain existing multi-threading for Core API calls
  - [ ] Add intelligent retry logic with exponential backoff
  - [ ] Implement request caching where appropriate

### CONFIGURATION & DEPLOYMENT

#### 10. Configuration Management
- [ ] **GraphQL Configuration**
  - [ ] Update hasura_config.json structure if needed
  - [ ] Add environment-based configuration options
  - [ ] Document GraphQL endpoint requirements

- [ ] **CLI Command Updates**
  - [ ] Update working CLI commands in CLAUDE.md after refactoring
  - [ ] Test all entry points work correctly
  - [ ] Add new command options for GraphQL configuration

### PRIORITY ORDER
1. **CRITICAL**: Fix test failures (items 1, 6, 8)
2. **HIGH**: Complete Controller implementation (item 2, 4)
3. **HIGH**: Expand Handler functionality (item 2, 5)  
4. **MEDIUM**: Runner GraphQL integration (items 3, 9)
5. **LOW**: Performance optimization (item 9)
6. **LOW**: Configuration improvements (item 10)

### ARCHITECTURE FLOW
```
Runner (Setup Hasura) -> Controller (Strategic Decisions) -> Handler (ESPN Execution) -> Controller (Data Return) -> Runner (GraphQL Updates)
```

This ensures clean separation of concerns:
- **Runner**: Infrastructure (GraphQL connection, final updates)
- **Controller**: Business logic (what to extract, how to optimize)  
- **Handler**: Technical execution (ESPN API calls, data processing)