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

        # Handle case where player info might be missing
        try:
            player = data.get("playerPoolEntry", {}).get("player") or data.get(
                "player", {}
            )
            self.injury_status = player.get("injuryStatus", self.injury_status)
            self.injured = player.get("injured", False)

            # add available stats from player data
        except (KeyError, TypeError):
            # If we can't get player data, set defaults
            self.injured = False
            self.percent_owned = round(
                data.get("ownership", {}).get("percentOwned", -1), 2
            )

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

    @classmethod
    def from_model(cls, player_model: PlayerModel):
        """
        Create a Player instance from a PlayerModel.

        Args:
            player_model (PlayerModel): The Pydantic model to convert

        Returns:
            Player: A new Player instance
        """
        # Convert the model to a dict for initialization
        player_dict = player_model.to_player_dict()
        player = cls(player_dict)

        standard_field_mappings = [
            ("name", lambda m: getattr(m, "name", None)),
            ("pro_team", lambda m: getattr(m, "pro_team", None)),
            ("primary_position", lambda m: getattr(m, "primary_position", None)),
            ("season_outlook", lambda m: getattr(m, "season_outlook", None)),
            ("draft_ranks", lambda m: getattr(m, "draft_ranks", None)),
            ("games_played_by_position", lambda m: getattr(m, "games_played_by_position", None)),
            ("draft_auction_value", lambda m: getattr(m, "draft_auction_value", None)),
            ("on_team_id", lambda m: getattr(m, "on_team_id", None)),
            ("auction_value_average", lambda m: getattr(m, "auction_value_average", None)),
            ("injured", lambda m: getattr(m, "injured", None)),
            ("injury_status", lambda m: getattr(m, "injury_status", None)),
        ]

        for attr_name, getter_func in standard_field_mappings:
            value = getter_func(player_model)
            if value is not None:
                setattr(player, attr_name, value)

        cls._handle_eligible_slots(player, player_model)

        # Handle stats - now only contains kona stats with 4 specific keys
        if player_model.stats:
            player.stats = player_model.stats

        # Handle season statistics
        if player_model.season_stats:
            player.season_stats = {}
            player.season_stats["split_id"] = player_model.season_stats.split_id
            player.season_stats["split_name"] = player_model.season_stats.split_name
            player.season_stats["split_abbreviation"] = (
                player_model.season_stats.split_abbreviation
            )
            player.season_stats["split_type"] = player_model.season_stats.split_type
            player.season_stats["categories"] = {}

            # Process each category
            for cat_name, category in player_model.season_stats.categories.items():
                cat_dict: Dict[str, Any] = {
                    "display_name": category.display_name,
                    "short_display_name": category.short_display_name,
                    "abbreviation": category.abbreviation,
                    "summary": category.summary,
                    "stats": {},
                }

                # Process stats in the category
                for stat_name, stat_detail in category.stats.items():
                    # Convert StatDetail to a dictionary for storage
                    stat_dict = {
                        "display_name": stat_detail.display_name,
                        "short_display_name": stat_detail.short_display_name,
                        "description": stat_detail.description,
                        "abbreviation": stat_detail.abbreviation,
                        "value": stat_detail.value,
                        "display_value": stat_detail.display_value,
                        "rank": stat_detail.rank,
                        "rank_display_value": stat_detail.rank_display_value,
                    }
                    cat_dict["stats"][stat_name] = stat_dict

                player.season_stats["categories"][cat_name] = cat_dict


        return player

    def to_model(self) -> PlayerModel:
        """
        Convert this Player instance to a PlayerModel.

        Returns:
            PlayerModel: A new PlayerModel instance
        """
        return PlayerModel.from_player(self)

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

    def hydrate_statistics(self, data: Dict[str, Any]) -> None:
        """
        Hydrates the player object with statistics data from the statistics API.

        Args:
            data (dict): The statistics data from the ESPN API
        """
        # Initialize the statistics dictionary if it doesn't exist
        if not hasattr(self, "season_stats"):
            self.season_stats = {}

        # Get the splits data which contains all the statistics
        splits = data.get("splits", {})
        if not splits:
            return

        # Get the split id and name
        split_id = splits.get("id")
        split_name = splits.get("name")
        split_abbreviation = splits.get("abbreviation")
        split_type = splits.get("type")

        # Store basic split information
        self.season_stats["split_id"] = split_id
        self.season_stats["split_name"] = split_name
        self.season_stats["split_abbreviation"] = split_abbreviation
        self.season_stats["split_type"] = split_type

        # Initialize categories dictionary
        self.season_stats["categories"] = {}

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
            self.season_stats["categories"][category_name] = {
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
                self.season_stats["categories"][category_name]["stats"][stat_name] = {
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
        
        # Initialize stats structure with kona stat keys
        if not hasattr(self, 'stats') or not isinstance(self.stats, dict):
            self.stats = {}
        
        # Ensure kona stat keys exist
        kona_stat_keys = ['projections', 'preseason', 'regular_season', 'previous_season']
        for key in kona_stat_keys:
            if key not in self.stats:
                self.stats[key] = {}

    def _extract_games_by_position(self, kona_data: Dict[str, Any]) -> None:
        """Extract and map games played by position."""
        games_by_pos = safe_get(kona_data, "gamesPlayedByPosition", {})
        if games_by_pos:
            self.games_played_by_position = {
                str(POSITION_MAP.get(int(pos_id), pos_id)): games
                for pos_id, games in games_by_pos.items()
            }

    def _hydrate_kona_stats(self, stats: List[Dict[str, Any]]) -> None:
        # Process stats array to extract projections and seasonal stats
        current_year = str(datetime.now().year)
        previous_year = str(int(current_year) - 1)

        for stat_entry in stats:
            stat_id = stat_entry.get("id", "")
            stats_data = stat_entry.get("stats", {})

            # Map numeric stat keys to readable names, skip unknown keys
            mapped_stats = {}
            for key, value in stats_data.items():
                stat_key = int(key)
                if stat_key in STATS_MAP:
                    mapped_stats[STATS_MAP[stat_key]] = value

            # Identify stat type based on ID pattern and namespace under stats property
            if stat_id == f"10{current_year}":  # Projections (102025)
                self.stats["projections"] = mapped_stats
            elif stat_id == f"01{current_year}":  # Preseason stats (012025)
                self.stats["preseason"] = mapped_stats
            elif stat_id == f"02{current_year}":  # Regular season stats (022025)
                self.stats["regular_season"] = mapped_stats
            elif stat_id == f"00{previous_year}":  # Previous season stats (002024)
                self.stats["previous_season"] = mapped_stats

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
            ("draft_auction_value", "draftAuctionValue", player_dict, None),  # top-level
            ("on_team_id", "onTeamId", player_dict, None),  # top-level
            ("season_outlook", "seasonOutlook", player_data, None),  # nested in player
            ("draft_ranks", "draftRanksByRankType", player_data, {}),  # nested in player
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
