"""
Fixtures for testing player statistics functionality.
"""

SAMPLE_PLAYER_STATS_RESPONSE = {
    "$ref": "http://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/seasons/2025/types/2/athletes/42404/statistics/0?lang=en&region=us",
    "season": {
        "$ref": "http://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/seasons/2025?lang=en&region=us"
    },
    "athlete": {
        "$ref": "http://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/seasons/2025/athletes/42404?lang=en&region=us"
    },
    "splits": {
        "id": "0",
        "name": "All Splits",
        "abbreviation": "Total",
        "type": "total",
        "categories": [
            {
                "name": "batting",
                "displayName": "Batting",
                "shortDisplayName": "Batting",
                "abbreviation": "b",
                "summary": "55-197, 14 HR, 5 3B, 9 2B, 32 RBI, 38 R, 18 BB, 9 SB, 53 K",
                "stats": [
                    {
                        "name": "gamesPlayed",
                        "displayName": "Games Played",
                        "shortDisplayName": "GP",
                        "description": "Games Played",
                        "abbreviation": "GP",
                        "value": 47.0,
                        "displayValue": "47",
                        "rank": 6,
                        "rankDisplayValue": "6th"
                    },
                    {
                        "name": "homeRuns",
                        "displayName": "Home Runs",
                        "shortDisplayName": "HR",
                        "description": "The number of hits that allowed the batter to round the bases and score without the aid of an error of the defense.",
                        "abbreviation": "HR",
                        "value": 14.0,
                        "displayValue": "14",
                        "rank": 5,
                        "rankDisplayValue": "Tied-5th"
                    },
                    {
                        "name": "avg",
                        "displayName": "Batting Average",
                        "shortDisplayName": "AVG",
                        "description": "The average number of times the batter reached successfully on base due to a hit: hits / atBats",
                        "abbreviation": "AVG",
                        "value": 0.2791878,
                        "displayValue": ".279",
                        "rank": 49,
                        "rankDisplayValue": "Tied-49th"
                    }
                ]
            },
            {
                "name": "fielding",
                "displayName": "Fielding",
                "shortDisplayName": "Fielding",
                "abbreviation": "f",
                "summary": "",
                "stats": [
                    {
                        "name": "gamesPlayed",
                        "displayName": "Games Played",
                        "shortDisplayName": "GP",
                        "description": "Games Played",
                        "abbreviation": "GP",
                        "value": 47.0,
                        "displayValue": "47",
                        "rank": 18,
                        "rankDisplayValue": "18th"
                    },
                    {
                        "name": "fieldingPct",
                        "displayName": "Fielding Percentage",
                        "shortDisplayName": "FP",
                        "description": "The percentage of plays made by a fielder given the total number of chances.",
                        "abbreviation": "FP",
                        "value": 0.99115044,
                        "displayValue": "0.991"
                    }
                ]
            }
        ]
    },
    "seasonType": {
        "$ref": "http://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/seasons/2025/types/2?lang=en&region=us"
    }
}

SAMPLE_PLAYER_BASIC_INFO = {
    "id": 42404,
    "fullName": "Test Player",
    "firstName": "Test",
    "lastName": "Player",
    "defaultPositionId": 9,  # CF position
    "eligibleSlots": [9, 10, 5, 16, 17],
    "proTeamId": 10,  # Some team ID
    "status": "ACTIVE",
    "injuryStatus": "ACTIVE"
}