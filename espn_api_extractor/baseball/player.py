from datetime import datetime
from typing import Any, Dict, List

from espn_api_extractor.models.player_model import PlayerModel
from espn_api_extractor.utils.utils import json_parsing, safe_get_nested

from .constants import LINEUP_SLOT_MAP, NOMINAL_POSITION_MAP, PRO_TEAM_MAP, STATS_MAP


class Player(object):
    """Player are part of team"""

    STAT_FIELD_ORDER = [
        "projections",
        "current_season_stats",
        "previous_season_stats",
        "last_7_games",
        "last_15_games",
        "last_30_games",
    ]

    def __init__(self, data, current_season: int | None = None):
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
            str(LINEUP_SLOT_MAP.get(pos, pos))
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
        self.transactions: List[Dict[str, Any]] = []
        self.display_name: str | None = None
        self.short_name: str | None = None
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
        player = data.get("playerPoolEntry", {}).get("player") or data.get("player", {})
        self.injury_status = player.get("injuryStatus", self.injury_status)
        self.injured = player.get("injured", False)
        self.season_outlook = player.get("seasonOutlook", self.season_outlook)
        self.draft_ranks = (
            player.get("draftRanksByRankType", {}) if isinstance(player, dict) else {}
        )
        games_by_pos = (
            player.get("gamesPlayedByPosition", {}) if isinstance(player, dict) else {}
        )
        if isinstance(games_by_pos, dict) and games_by_pos:
            self.games_played_by_position = {
                str(NOMINAL_POSITION_MAP.get(int(pos_id), pos_id)): games
                for pos_id, games in games_by_pos.items()
            }
        self.on_team_id = data.get("onTeamId", self.on_team_id)
        transactions = data.get("transactions", [])
        self.transactions = transactions if isinstance(transactions, list) else []
        self.auction_value_average = safe_get_nested(
            player, "ownership", "auctionValueAverage", default=None
        )

        self.draft_auction_value = data.get("draftAuctionValue")
        if self.draft_auction_value is not None:
            self.draft_auction_value = int(self.draft_auction_value)
        if self.draft_auction_value in (None, 0):
            transaction_value = self._extract_draft_auction_value(self.transactions)
            if transaction_value is not None:
                self.draft_auction_value = transaction_value

        self.current_season = current_season or datetime.now().year

        # Process stats from player data if available
        if "stats" in player and isinstance(player["stats"], list):
            previous_year = self.current_season - 1

            for stat_entry in player["stats"]:
                season_id = stat_entry.get("seasonId")
                split_type = stat_entry.get("statSplitTypeId")
                stat_source = stat_entry.get("statSourceId", 0)

                # Skip individual game stats (split type 5)
                if split_type == 5:
                    continue

                # Determine stat key based on split type and season
                stat_key = None

                if season_id == self.current_season:
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
                        STATS_MAP.get(int(k), str(k)): v for k, v in raw_stats.items()
                    }
                    self.stats[stat_key].update(mapped_stats)

                elif stat_source == 1:
                    # Projected stats - store separately under "projections" key
                    if "projections" not in self.stats:
                        self.stats["projections"] = {}

                    raw_projected = stat_entry.get("stats", {})
                    mapped_projected = {
                        STATS_MAP.get(int(k), str(k)): v
                        for k, v in raw_projected.items()
                    }
                    self.stats["projections"].update(mapped_projected)

        self._add_pitching_rate_stats()
        self._reorder_stats()

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
    def from_model(
        cls, player_model: PlayerModel, current_season: int | None = None
    ) -> "Player":
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
        season = current_season or player_data.get("current_season")
        player = cls(player_data, current_season=season)

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
            "transactions",
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
        for field in cls.STAT_FIELD_ORDER:
            value = getattr(player_model, field, None)
            if value:
                # Remove _stats suffix to get the stats key
                stats_key = field.replace("_stats", "")
                player.stats[stats_key] = value

        player._reorder_stats()

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
        if not hasattr(self, "stats") or not isinstance(self.stats, dict):
            self.stats = {}

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

        self._reorder_stats()

    def _extract_draft_auction_value(
        self, transactions: List[Dict[str, Any]]
    ) -> int | None:
        for transaction in transactions:
            transaction_type = transaction.get("type")
            items = transaction.get("items", [])
            if transaction_type != "DRAFT" and not any(
                item.get("type") == "DRAFT" for item in items if isinstance(item, dict)
            ):
                continue
            bid_amount = transaction.get("bidAmount")
            if bid_amount is not None:
                return int(bid_amount)
        return None

    def _add_pitching_rate_stats(self) -> None:
        for stat_dict in self.stats.values():
            if not isinstance(stat_dict, dict):
                continue
            outs = stat_dict.get("OUTS")
            if not isinstance(outs, (int, float)):
                continue
            outs_int = int(outs)
            if "IP" not in stat_dict:
                innings = outs_int // 3
                remainder = outs_int % 3
                stat_dict["IP"] = innings + remainder / 10
            ip_real = outs_int / 3
            strikeouts = stat_dict.get("K")
            if (
                ip_real > 0
                and "K/9" not in stat_dict
                and isinstance(strikeouts, (int, float))
            ):
                stat_dict["K/9"] = (strikeouts / ip_real) * 9

    def _reorder_stats(self) -> None:
        if not isinstance(self.stats, dict):
            return

        ordered: Dict[str, Any] = {}
        seen = set()

        def add_key(key: str) -> None:
            if key in self.stats and key not in seen:
                ordered[key] = self.stats[key]
                seen.add(key)

        for field in self.STAT_FIELD_ORDER:
            stats_key = field.replace("_stats", "")
            if stats_key == "previous_season":
                for key in self.stats:
                    if key.startswith("previous_season"):
                        add_key(key)
                continue

            add_key(stats_key)

        for key, value in self.stats.items():
            if key not in seen:
                ordered[key] = value

        self.stats = ordered
