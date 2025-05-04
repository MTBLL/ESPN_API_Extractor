from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class BirthPlace(BaseModel):
    city: Optional[str] = None
    country: Optional[str] = None


class StatPeriod(BaseModel):
    points: float = 0.0
    projected_points: float = 0.0
    breakdown: Dict[str, Any] = {}
    projected_breakdown: Dict[str, Any] = {}


class PlayerModel(BaseModel):
    """Pydantic model for baseball player data"""

    # Basic player info
    id: Optional[int] = None
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
    active: bool = False

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

    # Statistics
    stats: Dict[Union[int, str], StatPeriod] = Field(default_factory=dict)

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

        # Convert stats dictionary to use StatPeriod model
        if hasattr(player, "stats") and player.stats:
            processed_stats = {}
            for period, stats in player.stats.items():
                stat_period = StatPeriod(
                    points=stats.get("points", 0.0),
                    projected_points=stats.get("projected_points", 0.0),
                    breakdown=stats.get("breakdown", {}),
                    projected_breakdown=stats.get("projected_breakdown", {}),
                )
                processed_stats[period] = stat_period
            data["stats"] = processed_stats

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

        # Process stats into the format expected by Player
        if "stats" in data:
            processed_stats = {}
            for period, stats in data["stats"].items():
                period_stats = {}
                for key, value in stats.items():
                    if isinstance(value, dict):
                        period_stats[key] = value
                    else:
                        period_stats[key] = value
                processed_stats[period] = period_stats
            data["stats"] = processed_stats

        return data
