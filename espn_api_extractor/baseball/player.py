from datetime import datetime

from espn_api_extractor.models.player_model import PlayerModel
from espn_api_extractor.utils.utils import json_parsing

from .constant import NOMINAL_POSITION_MAP, POSITION_MAP, PRO_TEAM_MAP, STATS_MAP


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
        self.stats = {}
        percent_owned_value = json_parsing(data, "percentOwned")
        self.percent_owned = (
            round(percent_owned_value, 2) if percent_owned_value else -1
        )

        player_stats = []
        # Handle case where player info might be missing
        try:
            player = data.get("playerPoolEntry", {}).get("player") or data.get(
                "player", {}
            )
            self.injury_status = player.get("injuryStatus", self.injury_status)
            self.injured = player.get("injured", False)
            player_stats = player.get("stats", [])

            # add available stats from player data
        except (KeyError, TypeError):
            # If we can't get player data, set defaults
            self.injured = False
            self.percent_owned = round(
                data.get("ownership", {}).get("percentOwned", -1), 2
            )

        year = datetime.now().year
        for stats in player_stats:
            stats_split_type = stats.get("statSplitTypeId")
            if stats.get("seasonId") != year or (
                stats_split_type != 0 and stats_split_type != 5
            ):
                continue
            stats_breakdown = stats.get("stats") or stats.get("appliedStats", {})
            breakdown = {
                STATS_MAP.get(int(k), k): v for (k, v) in stats_breakdown.items()
            }
            points = round(stats.get("appliedTotal", 0), 2)
            scoring_period = stats.get("scoringPeriodId")
            stat_source = stats.get("statSourceId")
            # TODO update stats to include stat split type (0: Season, 1: Last 7 Days, 2: Last 15 Days, 3: Last 30, 4: ??, 5: ?? Used in Box Scores)
            (points_type, breakdown_type) = (
                ("points", "breakdown")
                if stat_source == 0
                else ("projected_points", "projected_breakdown")
            )
            if self.stats.get(scoring_period):
                self.stats[scoring_period][points_type] = points
                self.stats[scoring_period][breakdown_type] = breakdown
            else:
                self.stats[scoring_period] = {
                    points_type: points,
                    breakdown_type: breakdown,
                }

    def __repr__(self) -> str:
        return "Player(%s)" % (self.name,)

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

        # Create a new Player instance
        player = cls(player_dict)

        # Copy fields that might have been missed in initialization
        if hasattr(player_model, "name") and player_model.name:
            player.name = player_model.name

        if hasattr(player_model, "pro_team") and player_model.pro_team:
            player.pro_team = player_model.pro_team

        if hasattr(player_model, "primary_position") and player_model.primary_position:
            player.primary_position = player_model.primary_position

        if hasattr(player_model, "eligible_slots") and player_model.eligible_slots:
            # Ensure eligible_slots are always strings
            player.eligible_slots = [str(slot) for slot in player_model.eligible_slots]

        # Handle special fields not covered by the standard initialization
        if player_model.stats:
            player.stats = {}
            for period, stat in player_model.stats.items():
                player.stats[period] = {
                    "points": stat.points,
                    "projected_points": stat.projected_points,
                    "breakdown": stat.breakdown,
                    "projected_breakdown": stat.projected_breakdown,
                }

        return player

    def to_model(self) -> PlayerModel:
        """
        Convert this Player instance to a PlayerModel.

        Returns:
            PlayerModel: A new PlayerModel instance
        """
        return PlayerModel.from_player(self)

    def hydrate(self, data: dict) -> None:
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
