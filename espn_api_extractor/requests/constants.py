from enum import Enum

FANTASY_BASE_ENDPOINT = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/"
NEWS_BASE_ENDPOINT = "https://site.api.espn.com/apis/fantasy/v3/games/"


class FantasySports(Enum):
    NFL = "ffl"
    NBA = "fba"
    NHL = "fhl"
    MLB = "flb"
    WNBA = "wfba"


ESPN_CORE_ENDPOINT_V2 = "http://sports.core.api.espn.com/v2"
ESPN_CORE_ENDPOINT_V3 = "https://site.web.api.espn.com/apis/common/v3"
ESPN_CORE_MLB_ENDPOINT = ESPN_CORE_ENDPOINT_V2 + "/sports/baseball/leagues/mlb"
ESPN_CORE_MLB_PLAYERS_ENDPOINT = ESPN_CORE_MLB_ENDPOINT + "/athletes"
ESPN_CORE_SPORT_ENDPOINTS = {
    "mlb": ESPN_CORE_ENDPOINT_V2 + "/sports/baseball/leagues/mlb",
    "nba": ESPN_CORE_ENDPOINT_V2 + "/sports/basketball/leagues/nba",
    "nfl": ESPN_CORE_ENDPOINT_V2 + "/sports/football/leagues/nfl",
    "nhl": ESPN_CORE_ENDPOINT_V2 + "/sports/hockey/leagues/nhl",
}

# Statistics endpoints and constants
# Type 2 = Regular Season, Type 1 = Spring Training
STAT_SEASON_TYPE = 2
# Stats category 0 = All Splits
STAT_CATEGORY = 0
