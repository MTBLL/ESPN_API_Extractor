import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BirthPlace(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


class StatPeriod(BaseModel):
    points: float = 0.0
    projected_points: float = 0.0
    breakdown: Dict[str, Any] = {}
    projected_breakdown: Dict[str, Any] = {}


class StatDetail(BaseModel):
    """Model for a single statistic"""

    display_name: Optional[str] = None
    short_display_name: Optional[str] = None
    description: Optional[str] = None
    abbreviation: Optional[str] = None
    value: Optional[float] = None
    display_value: Optional[str] = None
    rank: Optional[int] = None
    rank_display_value: Optional[str] = None


class StatCategory(BaseModel):
    """Model for a category of statistics (e.g., batting, pitching)"""

    display_name: Optional[str] = None
    short_display_name: Optional[str] = None
    abbreviation: Optional[str] = None
    summary: Optional[str] = None
    stats: Dict[str, StatDetail] = Field(default_factory=dict)


class SeasonStats(BaseModel):
    """Model for player season statistics"""

    split_id: Optional[str] = None
    split_name: Optional[str] = None
    split_abbreviation: Optional[str] = None
    split_type: Optional[str] = None
    categories: Dict[str, StatCategory] = Field(default_factory=dict)


class PlayerModel(BaseModel):
    """Pydantic model for baseball player data"""

    # Basic player info
    id: Optional[int] = Field(None, alias="idEspn")
    name: Optional[str] = None
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")

    # Display information
    display_name: Optional[str] = Field(None, alias="displayName")
    short_name: Optional[str] = Field(None, alias="shortName")
    nickname: Optional[str] = None
    slug: Optional[str] = None

    # Position information
    primary_position: Optional[str] = Field(None, alias="primaryPosition")
    eligible_slots: List[str] = Field(default_factory=list, alias="eligibleSlots")
    position_name: Optional[str] = Field(None, alias="positionName")
    pos: Optional[str] = None

    # Team information
    pro_team: Optional[str] = Field(None, alias="proTeam")

    # Status information
    injury_status: Optional[str] = Field(None, alias="injuryStatus")
    status: Optional[str] = None
    injured: bool = False
    active: Optional[bool] = False

    # Ownership statistics
    percent_owned: float = -1

    # Physical attributes
    weight: Optional[float] = None
    display_weight: Optional[str] = Field(None, alias="displayWeight")
    height: Optional[int] = None
    display_height: Optional[str] = Field(None, alias="displayHeight")

    # Playing characteristics
    bats: Optional[str] = None
    throws: Optional[str] = None

    # Biographical information
    date_of_birth: Optional[str] = Field(None, alias="dateOfBirth")
    birth_place: Optional[BirthPlace] = Field(None, alias="birthPlace")
    debut_year: Optional[int] = Field(None, alias="debutYear")

    # Jersey information
    jersey: Optional[str] = ""

    # Media information
    headshot: Optional[str] = None

    # Projections and outlook
    season_outlook: Optional[str] = Field(None, alias="seasonOutlook")

    # Fantasy and draft information from kona_playercard
    draft_auction_value: Optional[float] = Field(None, alias="draftAuctionValue")
    on_team_id: Optional[int] = Field(None, alias="onTeamId")
    draft_ranks: Dict[str, Any] = Field(default_factory=dict, alias="draftRanks")
    games_played_by_position: Dict[str, int] = Field(
        default_factory=dict, alias="gamesPlayedByPosition"
    )
    auction_value_average: Optional[float] = Field(None, alias="auctionValueAverage")

    # Statistics - kona stats with semantic keys: projections, current_season, previous_season, last_7_games, last_15_games, last_30_games
    # Also includes split_id, split_name, split_abbreviation, split_type, categories from season stats
    stats: Dict[str, Any] = Field(default_factory=dict)

    # Season statistics from the statistics endpoint
    season_stats: Optional[SeasonStats] = None

    @field_validator('eligible_slots', mode='before')
    @classmethod
    def parse_eligible_slots(cls, v):
        """Parse eligible_slots from JSON string if needed"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v or []
    
    @field_validator('jersey', mode='before')
    @classmethod
    def parse_jersey(cls, v):
        """Convert jersey number to string"""
        if v is None:
            return ""
        return str(v)
    
    @field_validator('injured', mode='before')
    @classmethod
    def parse_injured(cls, v):
        """Convert injured to boolean, handling None"""
        if v is None:
            return False
        return bool(v)
    
    @field_validator('stats', mode='before')
    @classmethod
    def parse_stats(cls, v):
        """Convert stats dictionary to use string keys"""
        if not isinstance(v, dict):
            return v
        
        # Convert integer keys to strings
        return {str(key): value for key, value in v.items()}

    model_config = ConfigDict(
        populate_by_name=True, arbitrary_types_allowed=True, str_strip_whitespace=True
    )

    @classmethod
    def from_player(cls, player):
        """Convert a Player object to PlayerModel"""
        data = {}

        # Copy all attributes from player object
        for key, value in player.__dict__.items():
            # Special handling for date_of_birth to ensure it's always in YYYY-MM-DD format
            if key == "date_of_birth" and value and "T" in value:
                data[key] = value.split("T")[0]
            else:
                data[key] = value

        # Convert stats dictionary - contains kona stats with semantic keys
        if hasattr(player, "stats") and player.stats:
            data["stats"] = player.stats

        # Convert season_stats dictionary to use SeasonStats model
        if hasattr(player, "season_stats") and player.season_stats:
            season_stats_data = player.season_stats

            # Process categories and their stats
            categories = {}
            for cat_name, cat_data in season_stats_data.get("categories", {}).items():
                # Process stats in this category
                stats = {}
                for stat_name, stat_data in cat_data.get("stats", {}).items():
                    stats[stat_name] = StatDetail(**stat_data)

                # Create the category with its stats
                cat_dict = {
                    "display_name": cat_data.get("display_name"),
                    "short_display_name": cat_data.get("short_display_name"),
                    "abbreviation": cat_data.get("abbreviation"),
                    "summary": cat_data.get("summary"),
                    "stats": stats,
                }
                categories[cat_name] = StatCategory(**cat_dict)

            # Create the SeasonStats object
            season_stats = SeasonStats(
                split_id=season_stats_data.get("split_id"),
                split_name=season_stats_data.get("split_name"),
                split_abbreviation=season_stats_data.get("split_abbreviation"),
                split_type=season_stats_data.get("split_type"),
                categories=categories,
            )
            data["season_stats"] = season_stats

        # Convert camelCase attributes to snake_case to match Player class
        for camel, snake in [
            ("primaryPosition", "primary_position"),
            ("eligibleSlots", "eligible_slots"),
            ("proTeam", "pro_team"),
            ("injuryStatus", "injury_status"),
            ("displayName", "display_name"),
            ("shortName", "short_name"),
            ("displayWeight", "display_weight"),
            ("displayHeight", "display_height"),
            ("dateOfBirth", "date_of_birth"),
            ("birthPlace", "birth_place"),
            ("debutYear", "debut_year"),
            ("positionName", "position_name"),
        ]:
            if camel in data:
                data[snake] = data.pop(camel)

        return cls(**data)

    def to_player_dict(self) -> dict:
        """Convert PlayerModel to a dictionary ready for Player class initialization"""
        # Convert to dict with all fields - use snake_case
        data = self.model_dump(exclude_none=True)

        # Add a few fields that are necessary for Player initialization
        if self.name:
            data["fullName"] = self.name

        # Convert snake_case fields back to camelCase for Player constructor
        field_mappings = {
            "first_name": "firstName",
            "last_name": "lastName",
            "display_name": "displayName",
            "short_name": "shortName",
            "primary_position": "defaultPositionId",  # Note: Player expects position ID, not name
            "eligible_slots": "eligibleSlots",
            "pro_team": "proTeamId",  # Note: Player expects team ID, not name
            "injury_status": "injuryStatus",
            "display_weight": "displayWeight",
            "display_height": "displayHeight",
            "date_of_birth": "dateOfBirth",
            "birth_place": "birthPlace",
            "debut_year": "debutYear",
            "position_name": "positionName",
            "percent_owned": "percentOwned",
        }

        for snake_key, camel_key in field_mappings.items():
            if snake_key in data:
                data[camel_key] = data.pop(snake_key)

        # Convert stats keys back to integers for Player class compatibility
        if "stats" in data and data["stats"]:
            stats_with_int_keys = {}
            for key, value in data["stats"].items():
                # Convert string keys back to integers if they represent numbers
                try:
                    int_key = int(key)
                    stats_with_int_keys[int_key] = value
                except ValueError:
                    # Keep string keys that aren't numeric (like "projections", "current_season", "last_7_games", etc.)
                    stats_with_int_keys[key] = value
            data["stats"] = stats_with_int_keys

        # Process season_stats into the format expected by Player
        if "season_stats" in data and data["season_stats"]:
            season_stats = data["season_stats"]
            processed_season_stats: Dict[str, Any] = {
                "split_id": season_stats["split_id"]
                if "split_id" in season_stats
                else None,
                "split_name": season_stats["split_name"]
                if "split_name" in season_stats
                else None,
                "split_abbreviation": season_stats["split_abbreviation"]
                if "split_abbreviation" in season_stats
                else None,
                "split_type": season_stats["split_type"]
                if "split_type" in season_stats
                else None,
                "categories": {},
            }

            # Process each category
            if "categories" in season_stats:
                for cat_name, category in season_stats["categories"].items():
                    cat_dict = {
                        "display_name": category.get("display_name"),
                        "short_display_name": category.get("short_display_name"),
                        "abbreviation": category.get("abbreviation"),
                        "summary": category.get("summary"),
                        "stats": {},
                    }

                    # Process each stat in the category
                    if "stats" in category:
                        for stat_name, stat in category["stats"].items():
                            cat_dict["stats"][stat_name] = {
                                "display_name": stat.get("display_name"),
                                "short_display_name": stat.get("short_display_name"),
                                "description": stat.get("description"),
                                "abbreviation": stat.get("abbreviation"),
                                "value": stat.get("value"),
                                "display_value": stat.get("display_value"),
                                "rank": stat.get("rank"),
                                "rank_display_value": stat.get("rank_display_value"),
                            }

                    processed_season_stats["categories"][cat_name] = cat_dict

            data["season_stats"] = processed_season_stats

        return data
