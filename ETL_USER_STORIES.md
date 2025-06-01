# ESPN ETL Pipeline User Stories

## Overview
This document outlines the user stories for the ESPN API Extractor ETL pipeline, designed for iterative data extraction with GraphQL integration for resource optimization.

## Core ETL Pipeline Stories

### User Story 1: GraphQL-First Player Population Check
> **As a** developer and consumer of the GraphQL API  
> **I want** the ESPN_API_Extractor to first query the existing GraphQL API to check for existing players and their biographical data  
> **So that** I can avoid unnecessary ESPN API calls for players that already exist and only fetch missing players from the ESPN API

**Acceptance Criteria:**
- Query GraphQL API for existing player population (if endpoint available)
- Compare ESPN player universe against GraphQL player population 
- Identify missing players that need hydration from ESPN API
- If GraphQL endpoint unavailable, proceed with full ESPN extraction
- Log population comparison metrics when GraphQL is available

---

### User Story 2: Unified Bio+Stats Hydration Strategy
> **As a** data engineer running any ETL extraction  
> **I want** all runs to hydrate both biographical data and statistics for all processed players  
> **So that** I have complete, consistent data in a single pass without complex conditional logic, allowing downstream processes to filter irrelevant players as needed

**Acceptance Criteria:**
- Bio+stats hydration is hardcoded as the default behavior (no conditional flags)
- If GraphQL endpoint available: Only hydrate missing players from ESPN API
- If GraphQL endpoint unavailable: Hydrate all players from ESPN API (bio + stats)
- Handle 404s gracefully for players without current season stats
- Downstream filtering handles player relevance, not the extraction phase

---

### User Story 3: Iterative Daily/Nightly Updates
> **As a** data engineer running regular updates  
> **I want** to update existing players' statistics while adding any new players that have appeared in the ESPN universe  
> **So that** I maintain current season data for the complete player population

**Acceptance Criteria:**
- Query existing players from GraphQL API
- Compare against current ESPN player universe
- Hydrate stats for existing players + bio+stats for new players
- Single execution mode: always fetch complete data when processing any player
- Support incremental player additions mid-season

---

## GraphQL Integration Stories

### User Story 4: GraphQL Client with Human-in-the-Loop Validation
> **As the** ETL pipeline  
> **I want** a GraphQL client that validates endpoint availability with human confirmation for failures  
> **So that** I can ensure intentional vs unintentional GraphQL unavailability and prevent unintended full extractions

**Acceptance Criteria:**
- GraphQL client with connection testing at startup
- **HITL Mechanism**: If GraphQL connection fails:
  - Display connection failure details to user
  - Prompt: "GraphQL endpoint unavailable. Continue with full ESPN extraction? (y/N)"
  - Allow user to abort, fix GraphQL server, and re-run
  - Default to abort (N) to prevent accidental resource usage
- Clear logging of GraphQL availability status and user decisions
- When GraphQL available: Player existence queries and mutation support

---

### User Story 5: Incremental Player Detection
> **As the** ETL pipeline  
> **I want** to efficiently identify which players need processing based on GraphQL population comparison  
> **So that** I minimize ESPN API calls while ensuring complete coverage

**Acceptance Criteria:**
- Fast player ID comparison (ESPN universe vs GraphQL population)
- Batch processing of missing players only
- Support for force-refresh of existing players when needed
- Metrics on API call savings from GraphQL integration

---

## Operational Stories

### User Story 6: Simplified ETL Configuration
> **As a** data engineer  
> **I want** a single extraction mode that handles both initial and incremental scenarios automatically based on GraphQL availability  
> **So that** I don't need different execution strategies for different operational contexts

**Acceptance Criteria:**
- Single CLI execution: `poetry run espn-players --output_dir ./output`
- Automatic GraphQL detection with HITL validation for failures
- Bio+stats extraction hardcoded (no conditional flags needed)
- Comprehensive logging showing GraphQL status and extraction decisions
- Configurable GraphQL endpoint via environment variables

---

## Implementation Architecture

### Execution Flow
```
1. Test GraphQL endpoint connection
2. If connection fails:
   - Display error details to user
   - Prompt for confirmation to continue without GraphQL
   - Default to abort, allow user to fix GraphQL and re-run
3. If GraphQL available:
   - Get existing player population
   - Extract missing players (bio+stats)
4. If GraphQL unavailable (with user confirmation):
   - Extract all ESPN players (bio+stats)
5. Always include complete data in extraction
6. Let downstream processes filter/transform as needed
```

### Key Design Principles
1. **Always Complete Data**: Bio+stats extraction is hardcoded behavior
2. **Human Validation**: HITL confirmation for GraphQL failures prevents accidents
3. **Single Mode**: No separate initial/incremental/maintenance modes
4. **Downstream Filtering**: Let subsequent ETL stages handle player relevance
5. **Resource Efficiency**: GraphQL integration saves API calls when available

### Resource Management
- **With GraphQL**: ~200-800 API calls (only missing players)
- **Without GraphQL**: ~4,600 API calls (full ESPN universe)
- **HITL Protection**: Prevents accidental full extractions when GraphQL should be available

---

## Environment Configuration

### Required Environment Variables
```bash
# GraphQL Configuration (optional)
GRAPHQL_ENDPOINT=https://your-graphql-api.com/graphql
GRAPHQL_AUTH_TOKEN=your_auth_token_here

# ESPN API Configuration
ESPN_API_RATE_LIMIT=100  # requests per minute
```

### CLI Usage
```bash
# Standard execution (auto-detects GraphQL)
poetry run espn-players --output_dir ./output

# Force full extraction (bypass GraphQL even if available)
poetry run espn-players --output_dir ./output --force-full-extraction

# Custom batch size
poetry run espn-players --output_dir ./output --batch-size 50
```