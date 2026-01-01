# Lineup Slot IDs vs Position IDs

ESPN provides two different ID systems:

- **Lineup slot IDs** are used in roster slots, lineupSlotId, and eligibleSlots.
- **Position IDs** are used in player defaultPositionId and gamesPlayedByPosition.

These are **not** the same mapping. Use the correct map for the field you are reading.

## Lineup Slot IDs

These map to `LINEUP_SLOT_MAP` and are used for lineup slots and eligibility.

| ID | Slot |
| --- | --- |
| 0 | C |
| 1 | 1B |
| 2 | 2B |
| 3 | 3B |
| 4 | SS |
| 5 | OF |
| 6 | 2B/SS |
| 7 | 1B/3B |
| 8 | LF |
| 9 | CF |
| 10 | RF |
| 11 | DH |
| 12 | UTIL |
| 13 | P |
| 14 | SP |
| 15 | RP |
| 16 | BE |
| 17 | IL |
| 19 | IF |

## Position IDs

These map to `NOMINAL_POSITION_MAP` and are used for player positions.

| ID | Position |
| --- | --- |
| 1 | SP |
| 2 | C |
| 3 | 1B |
| 4 | 2B |
| 5 | 3B |
| 6 | SS |
| 7 | LF |
| 8 | CF |
| 9 | RF |
| 10 | DH |
| 11 | RP |

## Usage Notes

- `lineupSlotId` and `eligibleSlots` -> use lineup slot IDs
- `defaultPositionId` and `gamesPlayedByPosition` -> use position IDs
