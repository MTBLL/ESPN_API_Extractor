from datetime import datetime

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
        self.primaryPosition = (
            NOMINAL_POSITION_MAP.get(position_id) if position_id is not None else None
        )

        self.lineupSlot = POSITION_MAP.get(data.get("lineupSlotId"), "")

        eligible_slots = json_parsing(data, "eligibleSlots")
        self.eligibleSlots = [
            POSITION_MAP.get(pos, pos)
            for pos in (eligible_slots if eligible_slots else [])
            if pos != 16 or pos != 17
        ]  # if position isn't in position map, just use the position id number

        pro_team_id = json_parsing(data, "proTeamId")
        self.proTeam = (
            PRO_TEAM_MAP.get(pro_team_id) if pro_team_id is not None else None
        )

        self.injuryStatus = json_parsing(data, "injuryStatus")
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
            self.injuryStatus = player.get("injuryStatus", self.injuryStatus)
            self.injured = player.get("injured", False)
            self.percent_started = round(
                player.get("ownership", {}).get("percentStarted", -1), 2
            )
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

    def hydrate(self, data: dict) -> None:
        """
        Hydrates the player object with additional data from the player details API.

        Args:
            data (dict): The player details data from the ESPN API
        """
        # Basic display information
        self.displayName = data.get("displayName", "")
        self.shortName = data.get("shortName", "")
        self.nickname = data.get("nickname", "")
        self.slug = data.get("slug", "")

        # Physical attributes
        self.weight = data.get("weight")
        self.displayWeight = data.get("displayWeight", "")
        self.height = data.get("height")
        self.displayHeight = data.get("displayHeight", "")

        # Biographical information
        self.dateOfBirth = data.get("dateOfBirth")
        self.birthPlace = data.get("birthPlace", {})
        self.debutYear = data.get("debutYear")

        # Jersey and position information
        self.jersey = data.get("jersey", "")
        if data.get("position"):
            self.positionName = data.get("position", {}).get("name")
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
