from typing import Dict

filter1: Dict = {
    "players": {
        "filterSlotIds": {"value": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 19]},
        "filterStatsForExternalIds": {"value": [2025]},
        "filterStatsForSourceIds": {"value": [1]},
        "sortAppliedStatTotal": {
            "sortAsc": False,
            "sortPriority": 3,
            "value": "102025",
        },
        "sortDraftRanks": {"sortPriority": 2, "sortAsc": True, "value": "ROTO"},
        "sortPercOwned": {"sortPriority": 4, "sortAsc": False},
        "limit": 50,
        "offset": 0,
        "sortStatId": {
            "additionalValue": "102025",
            "sortAsc": False,
            "sortPriority": 1,
            "value": 5,
        },
        "filterRanksForScoringPeriodIds": {"value": [45]},
        "filterRanksForRankTypes": {"value": ["STANDARD"]},
        "filterStatsForTopScoringPeriodIds": {
            "value": 5,
            "additionalValue": [
                "002025",
                "102025",
                "002024",
                "012025",
                "022025",
                "032025",
                "042025",
                "062025",
                "010002025",
            ],
        },
    }
}

filter2: Dict = {
    "players": {
        "filterSlotIds": {"value": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 19]},
        "filterStatsForExternalIds": {"value": [2025]},
        "filterStatsForSourceIds": {"value": [1]},
        "sortAppliedStatTotal": {
            "sortAsc": False,
            "sortPriority": 3,
            "value": "102025",
        },
        "sortDraftRanks": {"sortPriority": 2, "sortAsc": True, "value": "ROTO"},
        "sortPercOwned": {"sortPriority": 4, "sortAsc": False},
        "limit": 50,
        "offset": 0,
        "sortStatId": {
            "additionalValue": "102025",
            "sortAsc": False,
            "sortPriority": 1,
            "value": 5,
        },
        "filterRanksForScoringPeriodIds": {"value": [45]},
        "filterRanksForRankTypes": {"value": ["STANDARD"]},
        "filterStatsForTopScoringPeriodIds": {
            "value": 5,
            "additionalValue": [
                "002025",
                "102025",
                "002024",
                "012025",
                "010002025",
            ],
        },
    },
}

CURRENT_YEAR = "002025"
PROJ_CURRENT_YEAR = "102025"
