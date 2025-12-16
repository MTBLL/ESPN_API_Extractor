# ESPN API Data Sources - Comprehensive Analysis

## Overview
This document maps all ESPN API endpoints used by the extractor, what data each provides, and when to use each source.

---

## API Endpoint Comparison Matrix

| Feature | kona_playercard | kona_playerinfo | v2 Core Stats | v3 Splits |
|---------|----------------|-----------------|---------------|-----------|
| **Endpoint Pattern** | `?view=kona_playercard` | `?view=kona_player_info` | `/athletes/{id}/statistics/0` | `/athletes/{id}/splits` |
| **Projections (2025)** | ✅ 102025 | ✅ 102025 | ❌ | ❌ |
| **Fantasy Scoring** | ✅ appliedStats/appliedTotal | ❌ | ❌ | ❌ |
| **Full Season Stats** | ✅ 002025 | ✅ 002025 | ✅ All Splits | ✅ All Splits |
| **Previous Season** | ✅ 002024 | ✅ 002024 | ❌ | ❌ |
| **Last 7 Games** | ✅ 012025 | ✅ 012025 | ❌ | ❌ (days) |
| **Last 15 Games** | ✅ 022025 | ✅ 022025 | ❌ | ❌ (days) |
| **Last 30 Games** | ✅ 032025 | ✅ 032025 | ❌ | ❌ (days) |
| **Game-by-Game** | ✅ statSplitTypeId: 5 | ✅ statSplitTypeId: 5 | ❌ | ❌ |
| **Home/Away Splits** | ❌ | ❌ | ❌ | ✅ |
| **vs L/R Splits** | ❌ | ❌ | ❌ | ✅ |
| **Monthly Splits** | ❌ | ❌ | ❌ | ✅ |
| **Rankings (ESPN)** | ❌ | ❌ | ✅ | ❌ |
| **Ratings (Fantasy)** | ✅ By scoring period | ✅ By scoring period | ❌ | ❌ |
| **Advanced Metrics** | ❌ (WAR from Fangraphs) | ❌ | ✅ WAR, OPS, ISOP | ❌ |
| **Stat Descriptions** | ❌ | ❌ | ✅ Full names, abbrevs | ❌ |
| **seasonOutlook** | ✅ | ✅ | ❌ | ❌ |
| **Draft Ranks** | ✅ | ✅ | ❌ | ❌ |
| **Ownership Data** | ✅ Detailed | ✅ Detailed | ❌ | ❌ |

---

## Detailed API Analysis

### 1. kona_playercard (Fantasy API v3) ⭐ PRIMARY SOURCE

**Endpoint:**
```
https://fantasy.espn.com/apis/v3/games/flb/seasons/{year}/segments/0/leaguedefaults/1?
  view=kona_playercard&scoringPeriodId={period}
```

**Request Headers:**
```json
{
  "players": {
    "filterIds": {
      "value": [39832, 42404]  // Optional: specific player IDs to fetch
    },
    "filterStatsForTopScoringPeriodIds": {
      "value": 1,
      "additionalValue": [
        "002025",    // Full season cumulative
        "102025",    // Projections
        "002024",    // Previous season
        "012025",    // Last 7 games
        "022025",    // Last 15 games
        "032025"     // Last 30 games
      ]
    }
  }
}
```

**Filter Options:**
- **filterIds:** Array of specific player IDs to retrieve (omit for all players)
- **filterStatsForTopScoringPeriodIds:** Which stat periods to include in response
  - Omit unwanted stat types to reduce response size
  - Can customize per use case (e.g., skip previous season for incremental updates)

**What It Provides:**
- ✅ **Complete fantasy data** including projections with fantasy scoring
- ✅ **appliedStats** - Shows which stats count for fantasy scoring with point values
- ✅ **appliedTotal** / **appliedAverage** - Pre-calculated fantasy points
- ✅ **Multiple stat types:**
  - `102025` - Projections (statSourceId: 1, statSplitTypeId: 0)
  - `002025` - Full season cumulative (statSourceId: 0, statSplitTypeId: 0)
  - `012025` - Last 7 games (statSplitTypeId: 1)
  - `022025` - Last 15 games (statSplitTypeId: 2)
  - `032025` - Last 30 games (statSplitTypeId: 3)
  - `002024` - Previous season full (year: 2024, statSplitTypeId: 0)
  - `05{gameId}` - Individual game stats (statSplitTypeId: 5)

  **Note:** Recent game splits (7/15/30) are based on **games played**, not calendar days. This provides consistent relative metrics across all players.
- ✅ **seasonOutlook** - Expert analysis text
- ✅ **draftRanksByRankType** - Draft rankings for different formats
- ✅ **ownership** - Detailed ownership/draft data
- ✅ **gamesPlayedByPosition**
- ✅ **starterStatusByProGame**

**Stat Format:** Numeric keys mapped via STATS_MAP
```json
{
  "stats": {
    "0": 334.0,  // AB (at bats)
    "1": 98.0,   // H (hits)
    "5": 28.0    // HR (home runs)
  }
}
```

**Use When:**
- You need projections
- You need fantasy scoring calculations
- You want complete player profile data
- Initial full extraction

**Optimization Strategies:**
```python
# Full extraction - all stat types including recent trends
additionalValue = ["002025", "102025", "002024", "012025", "022025", "032025"]

# Standard extraction - skip recent game splits
additionalValue = ["002025", "102025", "002024"]

# Minimal update - only current + projections
additionalValue = ["002025", "102025"]

# Recent performance tracking - for "hot players" feature
additionalValue = ["012025", "022025", "032025"]  # Last 7/15/30 games

# Specific players only
filterIds = [39832, 42404]  # Ohtani, Carroll

# All players (omit filterIds entirely)
# filterIds not included in request
```

**Decision:** ✅ **Use as PRIMARY source** - Most comprehensive, has unique data

---

### 2. kona_playerinfo (Fantasy API v3)

**Endpoint:**
```
https://fantasy.espn.com/apis/v3/games/flb/seasons/{year}/segments/0/leaguedefaults/1?
  view=kona_player_info&scoringPeriodId={period}
```

**What It Provides:**
- Nearly identical to kona_playercard BUT:
  - ❌ **NO appliedStats/appliedTotal/appliedAverage** in projections
  - ❌ **NO Split Type 3** (032025)
  - ❌ **NO game-by-game stats** (statSplitTypeId: 5)
- ✅ Same stats structure with numeric keys
- ✅ seasonOutlook, draft ranks, ownership

**Decision:** ❌ **Skip this endpoint** - kona_playercard has everything this has plus more

---

### 3. v2 Core Stats API (ESPN Sports Core)

**Endpoint:**
```
http://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/seasons/{year}/types/2/athletes/{player_id}/statistics/0
```

**What It Provides:**
- ✅ **Human-readable format** with full stat names and descriptions
- ✅ **Rankings** for each stat (e.g., "8th in runs scored")
- ✅ **Advanced sabermetrics:**
  - WAR (Wins Above Replacement)
  - OWAR (Offensive WAR)
  - DWAR (Defensive WAR)
  - OPS (On-base Plus Slugging)
  - ISOP (Isolated Power)
  - BIPA (Balls In Play Average)
  - RC/27 (Runs Created per 27 outs)
  - Many more
- ✅ **Categories:** batting, fielding, (pitching for pitchers)
- ❌ **NO projections** - only actual stats
- ❌ **NO fantasy scoring**
- ❌ **NO previous seasons**

**Stat Format:** Detailed objects with metadata
```json
{
  "name": "homeRuns",
  "displayName": "Home Runs",
  "abbreviation": "HR",
  "value": 31.0,
  "displayValue": "31",
  "rank": 21,
  "rankDisplayValue": "Tied-21st",
  "description": "..."
}
```

**Use When:**
- You need advanced sabermetrics (WAR, OPS, etc.)
- You want player rankings
- You need human-readable stat descriptions
- Building UI with stat definitions

**Decision:** ⚠️ **Use selectively** - Only when advanced metrics/rankings are needed

---

### 4. v3 Splits API (Fantasy API v3)

**Endpoint:**
```
https://fantasy.espn.com/apis/v3/games/flb/seasons/{year}/segments/0/leaguedefaults/1?
  view=splits_${player_id}
```

**What It Provides:**
- ✅ **Time-based recent performance:** ⭐
  - Last 7 Days
  - Last 15 Days
  - Last 30 Days
- ✅ **Situational splits:**
  - vs. Left / vs. Right
  - Home / Away
  - Day / Night
- ✅ **Monthly splits:**
  - March through September
- ❌ **NO projections**
- ❌ **NO previous seasons**
- ❌ **NO fantasy scoring**

**Stat Format:** Arrays without keys (order-dependent)
```json
{
  "displayName": "Last 7 Days",
  "stats": [
    "13",    // AB
    "1",     // R
    "3",     // H
    "1",     // 2B
    "0",     // 3B
    "0",     // HR
    "1",     // RBI
    "5",     // BB
    "0",     // HBP
    "5",     // K
    "2",     // SB
    "0",     // CS
    ".231",  // AVG
    ".444",  // OBP
    ".308",  // SLG
    ".752"   // OPS
  ]
}
```

**Use When:**
- Analyzing recent hot/cold streaks
- Building "trending" or "hot players" features
- Situational analysis (platoon splits, home/road performance)
- Monthly performance tracking

**Decision:** ⚠️ **Use for specific features only** - Unique data but specialized use case

---

## Data Retrieval Framework

### Primary Strategy: Minimize API Calls

**Core Principle:** Get maximum data from minimum endpoints

### Recommended Architecture:

#### **Phase 1: Initial Full Extraction**
```python
1. Call: kona_playercard (batch, all players)
   → Get: projections, all season stats, fantasy scoring, outlook, draft ranks

2. Call: v2 Core Stats (parallel, per player, optional)
   → Get: Advanced metrics (WAR, OPS, rankings)
   → Only if needed for your use case
```

**Result:** Complete player profiles with fantasy data

#### **Phase 2: Incremental Updates**
```python
1. Call: kona_playercard (batch, changed players only)
   → Update: current season stats, projections, outlook

2. Call: v3 Splits (on-demand, specific players)
   → Get: Last 7/15/30 day performance for trending analysis
```

**Result:** Keep data fresh without unnecessary calls

---

## Stats Structure Design Recommendation

### Unified Stats Dictionary Structure

Based on data sources analysis, recommended structure:

```python
player.stats = {
    # From kona_playercard - Core fantasy data
    "projections": {
        "AB": 334.0,
        "H": 98.0,
        "HR": 28.0,
        # ... all stats with readable names
        "_fantasy_scoring": {  # New: preserve fantasy calculations
            "applied_total": 470.0,
            "applied_average": 5.595,
            "applied_stats": {
                "8": 206.0,   # Total bases
                "10": 59.0,   # Walks
                # ... only stats that count for fantasy scoring
            }
        }
    },

    "current_season": {  # 002025 - Full season to date
        "AB": 611.0,
        "H": 172.0,
        # ...
    },

    "previous_season": {  # 002024
        "AB": 636.0,
        "H": 197.0,
        # ...
    },

    "last_7_games": {  # 012025 - Recent performance
        "AB": 21.0,
        "H": 5.0,
        # ...
    },

    "last_15_games": {  # 022025
        "AB": 54.0,
        "H": 15.0,
        # ...
    },

    "last_30_games": {  # 032025
        "AB": 100.0,
        "H": 30.0,
        # ...
    },

    # From v2 Core Stats - Advanced metrics (optional)
    # Note: WAR will come from Fangraphs API in separate app
    "advanced": {
        "OPS": 0.883,
        "ISOP": 0.282,
        "BIPA": 0.303,
        # ... ESPN advanced stats
        "_rankings": {
            "runs": {"rank": 8, "display": "8th"},
            "HR": {"rank": 21, "display": "Tied-21st"}
        }
    },

    # From v3 Splits - Situational (optional, rarely needed)
    "splits": {
        "vs_left": { /* ... */ },
        "vs_right": { /* ... */ },
        "home": { /* ... */ },
        "away": { /* ... */ },
        "last_7_days": { /* ... */ },  # Calendar days (vs games above)
        "last_15_days": { /* ... */ },
        "last_30_days": { /* ... */ }
    }
}
```

### Key Design Decisions:

1. **Flat dictionary keys** (not nested by split type ID)
   - Easier to access: `player.stats["projections"]["HR"]`
   - Clear semantic meaning

2. **Preserve fantasy scoring metadata**
   - Store `appliedStats`, `appliedTotal`, `appliedAverage` under `_fantasy_scoring`
   - Don't lose ESPN's fantasy point calculations

3. **Recent performance = games not days**
   - `last_7_games`, `last_15_games`, `last_30_games` from kona_playercard
   - Games-based metrics are more consistent than calendar days
   - Provides apples-to-apples comparison across all players

4. **Optional advanced/splits sections**
   - Only populate if those API calls are made
   - v2 Core Stats for ESPN rankings/advanced metrics (OPS, ISOP, etc.)
   - v3 Splits for situational data (vs L/R, home/away, calendar days)
   - Keeps structure lightweight when not needed

5. **WAR from external source**
   - ESPN v2 has WAR, but Fangraphs will be the authoritative source
   - Separate Fangraphs API extractor app will handle WAR data

6. **Consistent stat naming**
   - All use STATS_MAP to convert numeric keys → readable names
   - "AB" not "0", "HR" not "5"

---

## Outstanding Questions

### 1. Confirm Split Type 3 = Last 30 Games
- **032025** appears to follow the pattern (7/15/30)
- Need to verify by checking games played in the response
- If confirmed, this **replaces v3 Splits API** for recent performance tracking

### 2. When to call v2 Core Stats?
- **If building public-facing app:** YES - users want WAR, rankings
- **If internal fantasy tool:** NO - kona has all fantasy-relevant stats
- **Decision:** Make it optional/configurable

### 3. When to call v3 Splits?
- **For "trending players" feature:** YES - last 7/15/30 days essential
- **For basic fantasy app:** NO - current season stats sufficient
- **Decision:** On-demand only, not part of bulk extraction

---

## Recommended Implementation Plan

### Step 1: Refactor Stats Structure
1. Change `player.stats` from integer keys to semantic keys
2. Preserve fantasy scoring in `projections._fantasy_scoring`
3. Rename `hydrate_statistics()` → `hydrate_stats()`
4. Update `season_stats` → merge into `stats.advanced` or separate

### Step 2: Update kona_playercard Processing
1. Map all stat split types to new structure:
   - `102025` → `projections` (with `_fantasy_scoring`)
   - `002025` → `current_season`
   - `012025` → `preseason`
   - `022025` → `regular_season`
   - `032025` → investigate and map appropriately
   - `002024` → `previous_season`

### Step 3: Optional Enhancements
1. Add v2 Core Stats hydration (make configurable)
   - Add `hydrate_advanced_metrics()` method
   - Populate `player.stats.advanced`
2. Add v3 Splits support (on-demand)
   - Add `hydrate_recent_performance()` method
   - Populate `player.stats.recent`

### Step 4: Update Tests
1. Fix all test fixtures to use new structure
2. Test fantasy scoring preservation
3. Verify STATS_MAP conversions

---

## API Call Cost Analysis

### Current Implementation
```
get_pro_players()        →  1 call  (all players, lightweight)
get_player_cards()       →  1 call  (batch, ~3000 players)
hydrate_bio()            →  N calls (parallel, per player)
hydrate_statistics()     →  N calls (parallel, per player, optional)
```

### Proposed Optimization
```
Skip: get_pro_players()        (redundant - kona has this data)
Use:  kona_playercard          →  1 call  (batch, complete data)
Use:  v2 Core Stats            →  N calls (optional, only if advanced metrics needed)
Use:  v3 Splits                →  on-demand (for trending/splits features)
```

**Savings:** Eliminate 1 + N API calls by skipping get_pro_players and making hydrate_statistics optional

---

## Conclusion

**Primary Data Source:** `kona_playercard`
- Contains all essential fantasy data
- Includes projections with fantasy scoring
- Has complete stat history
- Single batch call for all players

**Secondary Sources (Optional):**
- `v2 Core Stats` - For advanced sabermetrics and rankings
- `v3 Splits` - For recent performance and situational splits

**Eliminate:**
- `players_wl` (get_pro_players) - Redundant
- `kona_playerinfo` - Subset of kona_playercard

This architecture minimizes API calls while maximizing data completeness.
