from datetime import datetime
from typing import Any, Dict, List

from espn_api_extractor.models.player_model import PlayerModel
from espn_api_extractor.utils.utils import json_parsing, safe_get, safe_get_nested

from .constants import NOMINAL_POSITION_MAP, POSITION_MAP, PRO_TEAM_MAP, STATS_MAP


class Player(object):
    """Player are part of team"""

    def __init__(self, data):
        self.id: int | None = json_parsing(data, "id")
        self.name: str | None = json_parsing(data, "fullName")
        self.first_name: str | None = json_parsing(data, "firstName")
        self.last_name: str | None = json_parsing(data, "lastName")

        # Handle potential None/empty results from json_parsing
        position_id = json_parsing(data, "defaultPositionId")
        self.primary_position = (
            NOMINAL_POSITION_MAP.get(position_id) if position_id is not None else None
        )

        eligible_slots = json_parsing(data, "eligibleSlots")
        self.eligible_slots = [
            str(POSITION_MAP.get(pos, pos))
            for pos in (eligible_slots if eligible_slots else [])
            if pos != 16 and pos != 17  # Filter out Bench (BE) and Injured List (IL)
        ]  # if position isn't in position map, just use the position id number as a string

        pro_team_id = json_parsing(data, "proTeamId")
        self.pro_team = (
            PRO_TEAM_MAP.get(pro_team_id) if pro_team_id is not None else None
        )

        self.injury_status = json_parsing(data, "injuryStatus")
        self.status = json_parsing(data, "status")
        self.stats: Dict[str, Any] = {}
        percent_owned_value = json_parsing(data, "percentOwned")
        self.percent_owned = (
            round(percent_owned_value, 2) if percent_owned_value else -1
        )

        # Initialize all additional fields with appropriate empty/default values
        self.injured: bool = False
        self.season_outlook: str | None = None
        self.draft_ranks: Dict[str, Any] = {}
        self.games_played_by_position: Dict[str, int] = {}
        self.draft_auction_value: int | None = None
        self.on_team_id: int | None = None
        self.auction_value_average: float | None = None
        self.display_name: str | None = None
        self.short_name: str | None = None
        self.nickname: str | None = None
        self.weight: int | None = None
        self.height: str | None = None
        self.date_of_birth: str | None = None
        self.birth_place: str | None = None
        self.debut_year: int | None = None
        self.jersey: str | None = None
        self.headshot: str | None = None
        self.bats: str | None = None
        self.throws: str | None = None
        self.active: bool | None = None

        # Handle case where player info might be missing
        player = data.get("playerPoolEntry", {}).get("player") or data.get(
            "player", {}
        )
        self.injury_status = player.get("injuryStatus", self.injury_status)
        self.injured = player.get("injured", False)

        # Process stats from player data if available
        if "stats" in player and isinstance(player["stats"], list):
            current_year = datetime.now().year
            previous_year = current_year - 1

            for stat_entry in player["stats"]:
                season_id = stat_entry.get("seasonId")
                split_type = stat_entry.get("statSplitTypeId")
                stat_source = stat_entry.get("statSourceId", 0)

                # Skip individual game stats (split type 5)
                if split_type == 5:
                    continue

                # Determine stat key based on split type and season
                stat_key = None

                if season_id == current_year:
                    # Current year stats
                    stat_type_map = {
                        0: "current_season",
                        1: "last_7_games",
                        2: "last_15_games",
                        3: "last_30_games",
                    }
                    stat_key = stat_type_map.get(split_type)

                elif season_id == previous_year and split_type == 0:
                    # Previous season full stats (only split type 0)
                    # Use 2-digit year suffix (e.g., "previous_season_24" for 2024)
                    stat_key = f"previous_season_{str(previous_year)[-2:]}"

                # Skip if we couldn't map the stat type
                if not stat_key:
                    continue

                # Initialize stat key if not exists
                if stat_key not in self.stats:
                    self.stats[stat_key] = {}

                # Map statSourceId: 0 = actual, 1 = projected
                if stat_source == 0:
                    # Actual stats
                    raw_stats = stat_entry.get("stats", {})
                    mapped_stats = {
                        STATS_MAP.get(int(k), str(k)): v
                        for k, v in raw_stats.items()
                    }
                    self.stats[stat_key].update(mapped_stats)

                    # Add fantasy scoring if available
                    if "appliedTotal" in stat_entry:
                        if "_fantasy_scoring" not in self.stats[stat_key]:
                            self.stats[stat_key]["_fantasy_scoring"] = {}
                        self.stats[stat_key]["_fantasy_scoring"]["applied_total"] = stat_entry.get("appliedTotal", 0)

                elif stat_source == 1:
                    # Projected stats - store separately under "projections" key
                    if "projections" not in self.stats:
                        self.stats["projections"] = {}

                    raw_projected = stat_entry.get("appliedStats", {})
                    mapped_projected = {
                        STATS_MAP.get(int(k), str(k)): v
                        for k, v in raw_projected.items()
                    }
                    self.stats["projections"].update(mapped_projected)

                    # Add fantasy scoring for projections
                    if "_fantasy_scoring" not in self.stats["projections"]:
                        self.stats["projections"]["_fantasy_scoring"] = {}
                    if "appliedTotal" in stat_entry:
                        self.stats["projections"]["_fantasy_scoring"]["applied_total"] = stat_entry.get("appliedTotal", 0)
                    if "appliedAverage" in stat_entry:
                        self.stats["projections"]["_fantasy_scoring"]["applied_average"] = stat_entry.get("appliedAverage", 0)

    def __repr__(self) -> str:
        return "Player(%s)" % (self.name,)

    @classmethod
    def _handle_eligible_slots(
        cls, player: "Player", player_model: PlayerModel
    ) -> None:
        """Handle eligible_slots conversion with type safety."""
        eligible_slots = getattr(player_model, "eligible_slots", None)
        if eligible_slots:
            player.eligible_slots = [str(slot) for slot in eligible_slots]

    def to_model(self) -> PlayerModel:
        """
        Convert this Player instance to a PlayerModel.

        Returns:
            PlayerModel: A new PlayerModel instance
        """
        return PlayerModel.from_player(self)

    @classmethod
    def from_model(cls, player_model: PlayerModel) -> "Player":
        """
        Create a Player instance from a PlayerModel.

        This enables conversion from validated Pydantic models back to Player objects
        which contain all the business logic and hydration methods. This is the primary
        method used by the runner to convert GraphQL PlayerModel objects to Player objects.

        Args:
            player_model: PlayerModel instance from GraphQL/database

        Returns:
            Player: A new Player instance with data from the model
        """
        # Use the existing to_player_dict method to get properly formatted data
        player_data = player_model.to_player_dict()

        # Create a new Player instance using the converted data
        player = cls(player_data)

        # Initialize kona fields to ensure they exist
        player._initialize_kona_fields()

        # Handle additional fields that the constructor doesn't set automatically
        # These are fields that come from PlayerModel but aren't in the basic player_data
        # Note: These fields are now initialized in __init__ with defaults, so we only
        # need to overwrite them if the PlayerModel has non-None values
        additional_fields = [
            "injured",
            "injury_status",
            "pro_team",
            "primary_position",
            "season_outlook",
            "draft_ranks",
            "games_played_by_position",
            "draft_auction_value",
            "on_team_id",
            "auction_value_average",
            "display_name",
            "short_name",
            "nickname",
            "weight",
            "height",
            "date_of_birth",
            "birth_place",
            "debut_year",
            "jersey",
            "headshot",
            "bats",
            "throws",
            "active",
            "eligible_slots",
        ]

        for field in additional_fields:
            value = getattr(player_model, field, None)
            if value is not None:
                setattr(player, field, value)

        # Handle stats - PlayerModel stats should be preserved
        if player_model.stats:
            player.stats = player_model.stats

        # Handle stat fields stored directly in PlayerModel
        stat_fields = [
            "projections",
            "current_season_stats",
            "previous_season_stats",
            "last_7_games",
            "last_15_games",
            "last_30_games",
        ]

        for field in stat_fields:
            value = getattr(player_model, field, None)
            if value:
                # Remove _stats suffix to get the stats key
                stats_key = field.replace("_stats", "")
                player.stats[stats_key] = value

        return player

    def hydrate_bio(self, data: dict) -> None:
        """
        Hydrates the player object with additional data from the player details API.

        Args:
            data (dict): The player details data from the ESPN API
        """
        # Basic display information
        self.display_name = data.get("displayName", "")
        self.short_name = data.get("shortName", "")
        self.nickname = data.get("nickname", "")
        self.slug = data.get("slug", "")

        # Physical attributes
        self.weight = data.get("weight")
        self.display_weight = data.get("displayWeight", "")
        self.height = data.get("height")
        self.display_height = data.get("displayHeight", "")

        # Biographical information
        date_of_birth = data.get("dateOfBirth")
        if date_of_birth and "T" in date_of_birth:
            # Remove the time part from the ISO date format (everything from T onwards)
            self.date_of_birth = date_of_birth.split("T")[0]
        else:
            self.date_of_birth = date_of_birth
        self.birth_place = data.get("birthPlace", {})
        self.debut_year = data.get("debutYear")

        # Jersey and position information
        self.jersey = data.get("jersey", "")
        if data.get("position"):
            self.position_name = data.get("position", {}).get("name")
            self.pos = data.get("position", {}).get("abbreviation")

        # Playing characteristics
        if data.get("bats"):
            self.bats = data.get("bats", {}).get("displayValue")
        if data.get("throws"):
            self.throws = data.get("throws", {}).get("displayValue")

        # Status information
        self.active = data.get("active", False)
        if data.get("status"):
            self.status = data.get("status", {}).get("type")

        # Headshot URL if available
        if data.get("headshot"):
            self.headshot = data.get("headshot", {}).get("href")

    def hydrate_stats(self, data: Dict[str, Any]) -> None:
        """
        Hydrates the player object with stats data from the stats API.

        Args:
            data (dict): The stats data from the ESPN API
        """
        # Initialize detailed stats entry in the stats dict
        if not hasattr(self, "stats") or not isinstance(self.stats, dict):
            self.stats = {}

        if "detailed" not in self.stats:
            self.stats["detailed"] = {}

        # Get the splits data which contains all the statistics
        splits = data.get("splits", {})
        if not splits:
            return

        # Get the split id and name
        split_id = splits.get("id")
        split_name = splits.get("name")
        split_abbreviation = splits.get("abbreviation")
        split_type = splits.get("type")

        # Store basic split information directly in stats
        self.stats["split_id"] = split_id
        self.stats["split_name"] = split_name
        self.stats["split_abbreviation"] = split_abbreviation
        self.stats["split_type"] = split_type

        # Initialize categories dictionary
        self.stats["categories"] = {}

        # Process each category (e.g., batting, pitching, fielding)
        categories = splits.get("categories", [])
        for category in categories:
            category_name = category.get("name")
            if not category_name:
                continue

            # Get the category display name and summary
            category_display_name = category.get("displayName", category_name)
            category_summary = category.get("summary", "")

            # Initialize the category dictionary
            self.stats["categories"][category_name] = {
                "display_name": category_display_name,
                "short_display_name": category.get(
                    "shortDisplayName", category_display_name
                ),
                "abbreviation": category.get("abbreviation", ""),
                "summary": category_summary,
                "stats": {},
            }

            # Process each stat in the category
            stats = category.get("stats", [])
            for stat in stats:
                stat_name = stat.get("name")
                if not stat_name:
                    continue

                # Store the stat with all its attributes
                self.stats["categories"][category_name]["stats"][stat_name] = {
                    "display_name": stat.get("displayName", stat_name),
                    "short_display_name": stat.get("shortDisplayName", stat_name),
                    "description": stat.get("description", ""),
                    "abbreviation": stat.get("abbreviation", ""),
                    "value": stat.get("value"),
                    "display_value": stat.get("displayValue", ""),
                    "rank": stat.get("rank"),
                    "rank_display_value": stat.get("rankDisplayValue", ""),
                }

    def _initialize_kona_fields(self) -> None:
        """Initialize all kona_playercard fields with default values."""
        field_defaults: Dict[str, Any] = {
            "season_outlook": None,
            "draft_auction_value": None,
            "on_team_id": None,
            "draft_ranks": {},
            "games_played_by_position": {},
            "auction_value_average": None,
        }

        for field, default in field_defaults.items():
            if not hasattr(self, field):
                setattr(self, field, default)

        # Initialize stats structure with semantic stat keys
        if not hasattr(self, "stats") or not isinstance(self.stats, dict):
            self.stats = {}

        # Ensure semantic stat keys exist
        # Note: previous_season uses dynamic year suffix (e.g., "previous_season_24")
        current_year = datetime.now().year
        previous_year = current_year - 1
        stat_keys = [
            "projections",
            "current_season",
            f"previous_season_{str(previous_year)[-2:]}",
            "last_7_games",
            "last_15_games",
            "last_30_games",
        ]
        for key in stat_keys:
            if key not in self.stats:
                self.stats[key] = {}

    def _extract_games_by_position(self, kona_data: Dict[str, Any]) -> None:
        """Extract and map games played by position.

        Note: gamesPlayedByPosition uses NOMINAL_POSITION_MAP, not POSITION_MAP.
        """
        games_by_pos = safe_get(kona_data, "gamesPlayedByPosition", {})
        if games_by_pos:
            self.games_played_by_position = {
                str(NOMINAL_POSITION_MAP.get(int(pos_id), pos_id)): games
                for pos_id, games in games_by_pos.items()
            }

    def _hydrate_kona_stats(self, stats: List[Dict[str, Any]]) -> None:
        """
        Process stats array from kona_playercard to extract projections and seasonal stats.

        Stat ID format: {splitTypeId}{year}
        - 102025: Projections (statSourceId: 1, statSplitTypeId: 0)
        - 002025: Current season full stats (split type 0)
        - 002024: Previous season full stats (split type 0)
        - 012025: Last 7 games (split type 1)
        - 022025: Last 15 games (split type 2)
        - 032025: Last 30 games (split type 3)

        Note: Split type 5 (individual games) is skipped due to ambiguity with two-way players.
        """
        current_year = str(datetime.now().year)
        previous_year = str(int(current_year) - 1)

        for stat_entry in stats:
            stat_id = stat_entry.get("id", "")
            stats_data = stat_entry.get("stats", {})
            applied_stats = stat_entry.get("appliedStats", {})
            applied_total = stat_entry.get("appliedTotal")
            applied_average = stat_entry.get("appliedAverage")

            # Map numeric stat keys to readable names, skip unknown keys
            mapped_stats = {}
            for key, value in stats_data.items():
                numeric_key = int(key)
                if numeric_key in STATS_MAP:
                    mapped_stats[STATS_MAP[numeric_key]] = value

            # Map applied stats for projections (uses appliedStats instead of stats)
            mapped_applied_stats = {}
            for key, value in applied_stats.items():
                numeric_key = int(key)
                if numeric_key in STATS_MAP:
                    mapped_applied_stats[STATS_MAP[numeric_key]] = value

            # Determine stat key based on stat ID pattern
            stat_key: str | None = None

            if stat_id == f"10{current_year}":  # Projections (102025)
                stat_key = "projections"
                # Use appliedStats for projections (more detailed than stats)
                if mapped_applied_stats:
                    self.stats[stat_key] = mapped_applied_stats
                elif mapped_stats:
                    self.stats[stat_key] = mapped_stats
                else:
                    self.stats[stat_key] = {}

                # Add fantasy scoring for projections
                if applied_total is not None or applied_average is not None:
                    self.stats[stat_key]["_fantasy_scoring"] = {}
                    if applied_total is not None:
                        self.stats[stat_key]["_fantasy_scoring"]["applied_total"] = applied_total
                    if applied_average is not None:
                        self.stats[stat_key]["_fantasy_scoring"]["applied_average"] = applied_average

            elif stat_id == f"00{current_year}":  # Current season full stats (002025)
                stat_key = "current_season"
                self.stats[stat_key] = mapped_stats

            elif stat_id == f"00{previous_year}":  # Previous season full stats (002024)
                # Use 2-digit year suffix (e.g., "previous_season_24" for 2024)
                stat_key = f"previous_season_{str(previous_year)[-2:]}"
                self.stats[stat_key] = mapped_stats

            elif stat_id == f"01{current_year}":  # Last 7 games (012025)
                stat_key = "last_7_games"
                self.stats[stat_key] = mapped_stats

            elif stat_id == f"02{current_year}":  # Last 15 games (022025)
                stat_key = "last_15_games"
                self.stats[stat_key] = mapped_stats

            elif stat_id == f"03{current_year}":  # Last 30 games (032025)
                stat_key = "last_30_games"
                self.stats[stat_key] = mapped_stats

            # Skip split type 5 (individual games) - ambiguous for two-way players

            # Add fantasy scoring for non-projection stats if available
            if stat_key and stat_key != "projections" and applied_total is not None:
                if "_fantasy_scoring" not in self.stats[stat_key]:
                    self.stats[stat_key]["_fantasy_scoring"] = {}
                self.stats[stat_key]["_fantasy_scoring"]["applied_total"] = applied_total

    def hydrate_kona_playercard(self, player_dict: Dict[str, Any]) -> None:
        """
        Hydrates the player object with comprehensive kona_playercard data including projections,
        seasonal stats, fantasy information, and player outlook from the ESPN kona_playercard API.

        Args:
            player_dict (dict): The complete player dictionary from kona_playercard API response
                              containing top-level fields (draftAuctionValue, onTeamId) and
                              nested 'player' object with seasonOutlook, stats array, etc.
        """
        # Initialize all fields first
        self._initialize_kona_fields()

        # Extract nested player data
        player_data = player_dict.get("player", {})

        # Define field mappings: (attribute_name, json_key, data_source, default_value)
        field_mappings: List[tuple[str, str, Dict[str, Any], Any]] = [
            (
                "draft_auction_value",
                "draftAuctionValue",
                player_dict,
                None,
            ),  # top-level
            ("on_team_id", "onTeamId", player_dict, None),  # top-level
            ("season_outlook", "seasonOutlook", player_data, None),  # nested in player
            (
                "draft_ranks",
                "draftRanksByRankType",
                player_data,
                {},
            ),  # nested in player
            ("injured", "injured", player_data, None),  # nested in player
            ("injury_status", "injuryStatus", player_data, None),  # nested in player
        ]

        # Apply field mappings
        for attr_name, json_key, source, default in field_mappings:
            setattr(self, attr_name, safe_get(source, json_key, default))

        self.auction_value_average = safe_get_nested(
            player_data, "ownership", "auctionValueAverage", default=None
        )
        self._extract_games_by_position(player_data)

        if "stats" in player_data:
            self._hydrate_kona_stats(player_data["stats"])
