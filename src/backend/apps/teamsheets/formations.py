"""
Formation templates for teamsheets and tactics boards

Defines pitch coordinates for supported formations and provides helper functions for available formations and template validation
"""

from typing import TypedDict


# Typed shape for one formation slot
class PositionSlot(TypedDict):
    slot: int
    position: str
    x: float
    y: float


# ---------------------------------------------------------------------------
# Pitch coordinate constants
# ---------------------------------------------------------------------------

Y_GOALKEEPER = 5
Y_DEFENSIVE_LINE = 20
Y_FULLBACK_LINE = 25
Y_WINGBACK_LINE = 30
Y_HOLDING_MID = 35
Y_CENTRAL_MID = 45
Y_WIDE_MID = 50
Y_ATTACKING_MID = 60
Y_FORWARD_LINE = 75
Y_STRIKER_LINE = 78

X_CENTER = 50
X_HALF_LEFT = 35
X_HALF_RIGHT = 65
X_WIDE_LEFT = 15
X_WIDE_RIGHT = 85
X_TOUCHLINE_LEFT = 10
X_TOUCHLINE_RIGHT = 90


# ---------------------------------------------------------------------------
# Formation templates
# ---------------------------------------------------------------------------

FORMATION_TEMPLATES: dict[str, list[PositionSlot]] = {
    # Three-back formations
    '343': [
        {'slot': 1,  'position': 'GK',  'x': X_CENTER,      'y': Y_GOALKEEPER},
        {'slot': 2,  'position': 'CB',  'x': 70,            'y': Y_DEFENSIVE_LINE},
        {'slot': 3,  'position': 'CB',  'x': X_CENTER,      'y': Y_DEFENSIVE_LINE - 2},
        {'slot': 4,  'position': 'CB',  'x': 30,            'y': Y_DEFENSIVE_LINE},
        {'slot': 5,  'position': 'RM',  'x': X_WIDE_RIGHT,  'y': Y_WIDE_MID - 2},
        {'slot': 6,  'position': 'CM',  'x': X_HALF_RIGHT,  'y': Y_CENTRAL_MID - 3},
        {'slot': 7,  'position': 'CM',  'x': X_HALF_LEFT,   'y': Y_CENTRAL_MID - 3},
        {'slot': 8,  'position': 'LM',  'x': X_WIDE_LEFT,   'y': Y_WIDE_MID - 2},
        {'slot': 9,  'position': 'RW',  'x': 78,            'y': 72},
        {'slot': 10, 'position': 'ST',  'x': X_CENTER,      'y': Y_STRIKER_LINE},
        {'slot': 11, 'position': 'LW',  'x': 22,            'y': 72},
    ],

    '352': [
        {'slot': 1,  'position': 'GK',  'x': X_CENTER,          'y': Y_GOALKEEPER},
        {'slot': 2,  'position': 'CB',  'x': 70,                'y': Y_DEFENSIVE_LINE},
        {'slot': 3,  'position': 'CB',  'x': X_CENTER,          'y': Y_DEFENSIVE_LINE - 2},
        {'slot': 4,  'position': 'CB',  'x': 30,                'y': Y_DEFENSIVE_LINE},
        {'slot': 5,  'position': 'RWB', 'x': X_TOUCHLINE_RIGHT, 'y': Y_CENTRAL_MID},
        {'slot': 6,  'position': 'CM',  'x': X_HALF_RIGHT,      'y': Y_CENTRAL_MID - 3},
        {'slot': 7,  'position': 'CDM', 'x': X_CENTER,          'y': Y_HOLDING_MID},
        {'slot': 8,  'position': 'CM',  'x': X_HALF_LEFT,       'y': Y_CENTRAL_MID - 3},
        {'slot': 9,  'position': 'LWB', 'x': X_TOUCHLINE_LEFT,  'y': Y_CENTRAL_MID},
        {'slot': 10, 'position': 'ST',  'x': X_HALF_RIGHT,      'y': Y_FORWARD_LINE},
        {'slot': 11, 'position': 'ST',  'x': X_HALF_LEFT,       'y': Y_FORWARD_LINE},
    ],

    # Four-back formations
    '442': [
        {'slot': 1,  'position': 'GK',  'x': X_CENTER,      'y': Y_GOALKEEPER},
        {'slot': 2,  'position': 'RB',  'x': X_WIDE_RIGHT,  'y': Y_FULLBACK_LINE},
        {'slot': 3,  'position': 'CB',  'x': X_HALF_RIGHT,  'y': Y_DEFENSIVE_LINE},
        {'slot': 4,  'position': 'CB',  'x': X_HALF_LEFT,   'y': Y_DEFENSIVE_LINE},
        {'slot': 5,  'position': 'LB',  'x': X_WIDE_LEFT,   'y': Y_FULLBACK_LINE},
        {'slot': 6,  'position': 'RM',  'x': X_WIDE_RIGHT,  'y': Y_WIDE_MID},
        {'slot': 7,  'position': 'CM',  'x': X_HALF_RIGHT,  'y': Y_CENTRAL_MID},
        {'slot': 8,  'position': 'CM',  'x': X_HALF_LEFT,   'y': Y_CENTRAL_MID},
        {'slot': 9,  'position': 'LM',  'x': X_WIDE_LEFT,   'y': Y_WIDE_MID},
        {'slot': 10, 'position': 'ST',  'x': X_HALF_RIGHT,  'y': Y_FORWARD_LINE},
        {'slot': 11, 'position': 'ST',  'x': X_HALF_LEFT,   'y': Y_FORWARD_LINE},
    ],

    '433': [
        {'slot': 1,  'position': 'GK',  'x': X_CENTER,      'y': Y_GOALKEEPER},
        {'slot': 2,  'position': 'RB',  'x': X_WIDE_RIGHT,  'y': Y_FULLBACK_LINE},
        {'slot': 3,  'position': 'CB',  'x': X_HALF_RIGHT,  'y': Y_DEFENSIVE_LINE},
        {'slot': 4,  'position': 'CB',  'x': X_HALF_LEFT,   'y': Y_DEFENSIVE_LINE},
        {'slot': 5,  'position': 'LB',  'x': X_WIDE_LEFT,   'y': Y_FULLBACK_LINE},
        {'slot': 6,  'position': 'CM',  'x': X_HALF_RIGHT,  'y': Y_CENTRAL_MID},
        {'slot': 7,  'position': 'CDM', 'x': X_CENTER,      'y': Y_HOLDING_MID},
        {'slot': 8,  'position': 'CM',  'x': X_HALF_LEFT,   'y': Y_CENTRAL_MID},
        {'slot': 9,  'position': 'RW',  'x': 80,            'y': 72},
        {'slot': 10, 'position': 'ST',  'x': X_CENTER,      'y': Y_STRIKER_LINE},
        {'slot': 11, 'position': 'LW',  'x': 20,            'y': 72},
    ],

    '4321': [
        {'slot': 1,  'position': 'GK',  'x': X_CENTER,      'y': Y_GOALKEEPER},
        {'slot': 2,  'position': 'RB',  'x': X_WIDE_RIGHT,  'y': Y_FULLBACK_LINE},
        {'slot': 3,  'position': 'CB',  'x': X_HALF_RIGHT,  'y': Y_DEFENSIVE_LINE},
        {'slot': 4,  'position': 'CB',  'x': X_HALF_LEFT,   'y': Y_DEFENSIVE_LINE},
        {'slot': 5,  'position': 'LB',  'x': X_WIDE_LEFT,   'y': Y_FULLBACK_LINE},
        {'slot': 6,  'position': 'CM',  'x': 68,            'y': Y_CENTRAL_MID - 3},
        {'slot': 7,  'position': 'CM',  'x': X_CENTER,      'y': Y_CENTRAL_MID - 5},
        {'slot': 8,  'position': 'CM',  'x': 32,            'y': Y_CENTRAL_MID - 3},
        {'slot': 9,  'position': 'CAM', 'x': 62,            'y': Y_ATTACKING_MID},
        {'slot': 10, 'position': 'CAM', 'x': 38,            'y': Y_ATTACKING_MID},
        {'slot': 11, 'position': 'ST',  'x': X_CENTER,      'y': Y_STRIKER_LINE},
    ],

    '424': [
        {'slot': 1,  'position': 'GK',  'x': X_CENTER,      'y': Y_GOALKEEPER},
        {'slot': 2,  'position': 'RB',  'x': X_WIDE_RIGHT,  'y': Y_FULLBACK_LINE},
        {'slot': 3,  'position': 'CB',  'x': X_HALF_RIGHT,  'y': Y_DEFENSIVE_LINE},
        {'slot': 4,  'position': 'CB',  'x': X_HALF_LEFT,   'y': Y_DEFENSIVE_LINE},
        {'slot': 5,  'position': 'LB',  'x': X_WIDE_LEFT,   'y': Y_FULLBACK_LINE},
        {'slot': 6,  'position': 'RM',  'x': X_WIDE_RIGHT,  'y': Y_WIDE_MID + 2},
        {'slot': 7,  'position': 'CM',  'x': X_HALF_RIGHT,  'y': Y_CENTRAL_MID - 3},
        {'slot': 8,  'position': 'CM',  'x': X_HALF_LEFT,   'y': Y_CENTRAL_MID - 3},
        {'slot': 9,  'position': 'LM',  'x': X_WIDE_LEFT,   'y': Y_WIDE_MID + 2},
        {'slot': 10, 'position': 'RW',  'x': 78,            'y': 72},
        {'slot': 11, 'position': 'LW',  'x': 22,            'y': 72},       
    ],

    '4231': [
        {'slot': 1,  'position': 'GK',  'x': X_CENTER,      'y': Y_GOALKEEPER},
        {'slot': 2,  'position': 'RB',  'x': X_WIDE_RIGHT,  'y': Y_FULLBACK_LINE},
        {'slot': 3,  'position': 'CB',  'x': X_HALF_RIGHT,  'y': Y_DEFENSIVE_LINE},
        {'slot': 4,  'position': 'CB',  'x': X_HALF_LEFT,   'y': Y_DEFENSIVE_LINE},
        {'slot': 5,  'position': 'LB',  'x': X_WIDE_LEFT,   'y': Y_FULLBACK_LINE},
        {'slot': 6,  'position': 'CDM', 'x': X_HALF_RIGHT,  'y': Y_HOLDING_MID + 3},
        {'slot': 7,  'position': 'CDM', 'x': X_HALF_LEFT,   'y': Y_HOLDING_MID + 3},
        {'slot': 8,  'position': 'RM',  'x': 80,            'y': Y_ATTACKING_MID - 2},
        {'slot': 9,  'position': 'CAM', 'x': X_CENTER,      'y': Y_ATTACKING_MID},
        {'slot': 10, 'position': 'LM',  'x': 20,            'y': Y_ATTACKING_MID - 2},
        {'slot': 11, 'position': 'ST',  'x': X_CENTER,      'y': Y_STRIKER_LINE},
    ],

    '4222': [
        {'slot': 1,  'position': 'GK',  'x': X_CENTER,      'y': Y_GOALKEEPER},
        {'slot': 2,  'position': 'RB',  'x': X_WIDE_RIGHT,  'y': Y_FULLBACK_LINE},
        {'slot': 3,  'position': 'CB',  'x': X_HALF_RIGHT,  'y': Y_DEFENSIVE_LINE},
        {'slot': 4,  'position': 'CB',  'x': X_HALF_LEFT,   'y': Y_DEFENSIVE_LINE},
        {'slot': 5,  'position': 'LB',  'x': X_WIDE_LEFT,   'y': Y_FULLBACK_LINE},
        {'slot': 6,  'position': 'CDM', 'x': X_HALF_RIGHT,  'y': Y_HOLDING_MID + 3},
        {'slot': 7,  'position': 'CDM', 'x': X_HALF_LEFT,   'y': Y_HOLDING_MID + 3},
        {'slot': 8,  'position': 'RM',  'x': 80,            'y': Y_ATTACKING_MID - 2},
        {'slot': 9,  'position': 'CAM', 'x': X_CENTER,      'y': Y_ATTACKING_MID},
        {'slot': 10, 'position': 'LM',  'x': 20,            'y': Y_ATTACKING_MID - 2},
        {'slot': 11, 'position': 'ST',  'x': X_CENTER,      'y': Y_STRIKER_LINE},
    ],

    '4141': [
        {'slot': 1,  'position': 'GK',  'x': X_CENTER,      'y': Y_GOALKEEPER},
        {'slot': 2,  'position': 'RB',  'x': X_WIDE_RIGHT,  'y': Y_FULLBACK_LINE},
        {'slot': 3,  'position': 'CB',  'x': X_HALF_RIGHT,  'y': Y_DEFENSIVE_LINE},
        {'slot': 4,  'position': 'CB',  'x': X_HALF_LEFT,   'y': Y_DEFENSIVE_LINE},
        {'slot': 5,  'position': 'LB',  'x': X_WIDE_LEFT,   'y': Y_FULLBACK_LINE},
        {'slot': 6,  'position': 'CDM', 'x': X_CENTER,      'y': Y_HOLDING_MID},
        {'slot': 7,  'position': 'RM',  'x': X_WIDE_RIGHT,  'y': Y_WIDE_MID + 2},
        {'slot': 8,  'position': 'CM',  'x': X_HALF_RIGHT,  'y': Y_WIDE_MID - 2},
        {'slot': 9,  'position': 'CM',  'x': X_HALF_LEFT,   'y': Y_WIDE_MID - 2},
        {'slot': 10, 'position': 'LM',  'x': X_WIDE_LEFT,   'y': Y_WIDE_MID + 2},
        {'slot': 11, 'position': 'ST',  'x': X_CENTER,      'y': Y_STRIKER_LINE},
    ],

    '41212': [
        {'slot': 1,  'position': 'GK',  'x': X_CENTER,      'y': Y_GOALKEEPER},
        {'slot': 2,  'position': 'RB',  'x': X_WIDE_RIGHT,  'y': Y_FULLBACK_LINE},
        {'slot': 3,  'position': 'CB',  'x': X_HALF_RIGHT,  'y': Y_DEFENSIVE_LINE},
        {'slot': 4,  'position': 'CB',  'x': X_HALF_LEFT,   'y': Y_DEFENSIVE_LINE},
        {'slot': 5,  'position': 'LB',  'x': X_WIDE_LEFT,   'y': Y_FULLBACK_LINE},
        {'slot': 6,  'position': 'CDM', 'x': X_CENTER,      'y': Y_HOLDING_MID},
        {'slot': 7,  'position': 'CM',  'x': X_HALF_RIGHT,  'y': Y_WIDE_MID - 2},
        {'slot': 8,  'position': 'CM',  'x': X_HALF_LEFT,   'y': Y_WIDE_MID - 2},
        {'slot': 9,  'position': 'CAM', 'x': X_CENTER,      'y': Y_ATTACKING_MID},
        {'slot': 10, 'position': 'ST',  'x': X_HALF_RIGHT,  'y': Y_STRIKER_LINE},
        {'slot': 11, 'position': 'ST',  'x': X_HALF_LEFT,   'y': Y_STRIKER_LINE},
    ],

    # Five-back formations
    '532': [
        {'slot': 1,  'position': 'GK',  'x': X_CENTER,          'y': Y_GOALKEEPER},
        {'slot': 2,  'position': 'RWB', 'x': X_TOUCHLINE_RIGHT, 'y': Y_WINGBACK_LINE},
        {'slot': 3,  'position': 'CB',  'x': 68,                'y': Y_DEFENSIVE_LINE},
        {'slot': 4,  'position': 'CB',  'x': X_CENTER,          'y': Y_DEFENSIVE_LINE - 2},
        {'slot': 5,  'position': 'CB',  'x': 32,                'y': Y_DEFENSIVE_LINE},
        {'slot': 6,  'position': 'LWB', 'x': X_TOUCHLINE_LEFT,  'y': Y_WINGBACK_LINE},
        {'slot': 7,  'position': 'CM',  'x': X_HALF_RIGHT,      'y': Y_CENTRAL_MID},
        {'slot': 8,  'position': 'CM',  'x': X_CENTER,          'y': Y_CENTRAL_MID - 3},
        {'slot': 9,  'position': 'CM',  'x': X_HALF_LEFT,       'y': Y_CENTRAL_MID},
        {'slot': 10, 'position': 'ST',  'x': X_HALF_RIGHT,      'y': Y_FORWARD_LINE},
        {'slot': 11, 'position': 'ST',  'x': X_HALF_LEFT,       'y': Y_FORWARD_LINE},
    ],

    '523': [
        {'slot': 1,  'position': 'GK',  'x': X_CENTER,          'y': Y_GOALKEEPER},
        {'slot': 2,  'position': 'RWB', 'x': X_TOUCHLINE_RIGHT, 'y': Y_WINGBACK_LINE},
        {'slot': 3,  'position': 'CB',  'x': 68,                'y': Y_DEFENSIVE_LINE},
        {'slot': 4,  'position': 'CB',  'x': X_CENTER,          'y': Y_DEFENSIVE_LINE - 2},
        {'slot': 5,  'position': 'CB',  'x': 32,                'y': Y_DEFENSIVE_LINE},
        {'slot': 6,  'position': 'LWB', 'x': X_TOUCHLINE_LEFT,  'y': Y_WINGBACK_LINE},
        {'slot': 7,  'position': 'CM',  'x': X_HALF_RIGHT,      'y': Y_CENTRAL_MID},
        {'slot': 8,  'position': 'CM',  'x': X_CENTER,          'y': Y_CENTRAL_MID - 3},
        {'slot': 9,  'position': 'CM',  'x': X_HALF_LEFT,       'y': Y_CENTRAL_MID},
        {'slot': 10, 'position': 'ST',  'x': X_HALF_RIGHT,      'y': Y_FORWARD_LINE},
        {'slot': 11, 'position': 'ST',  'x': X_HALF_LEFT,       'y': Y_FORWARD_LINE},
    ],

    '5221': [
        {'slot': 1,  'position': 'GK',  'x': X_CENTER,          'y': Y_GOALKEEPER},
        {'slot': 2,  'position': 'RWB', 'x': X_TOUCHLINE_RIGHT, 'y': Y_WINGBACK_LINE},
        {'slot': 3,  'position': 'CB',  'x': 68,                'y': Y_DEFENSIVE_LINE},
        {'slot': 4,  'position': 'CB',  'x': X_CENTER,          'y': Y_DEFENSIVE_LINE - 2},
        {'slot': 5,  'position': 'CB',  'x': 32,                'y': Y_DEFENSIVE_LINE},
        {'slot': 6,  'position': 'LWB', 'x': X_TOUCHLINE_LEFT,  'y': Y_WINGBACK_LINE},
        {'slot': 7,  'position': 'CM',  'x': X_HALF_RIGHT,      'y': Y_CENTRAL_MID},
        {'slot': 8,  'position': 'CM',  'x': X_CENTER,          'y': Y_CENTRAL_MID - 3},
        {'slot': 9,  'position': 'CM',  'x': X_HALF_LEFT,       'y': Y_CENTRAL_MID},
        {'slot': 10, 'position': 'ST',  'x': X_HALF_RIGHT,      'y': Y_FORWARD_LINE},
        {'slot': 11, 'position': 'ST',  'x': X_HALF_LEFT,       'y': Y_FORWARD_LINE},
    ],

    '5212': [
        {'slot': 1,  'position': 'GK',  'x': X_CENTER,          'y': Y_GOALKEEPER},
        {'slot': 2,  'position': 'RWB', 'x': X_TOUCHLINE_RIGHT, 'y': Y_WINGBACK_LINE},
        {'slot': 3,  'position': 'CB',  'x': 68,                'y': Y_DEFENSIVE_LINE},
        {'slot': 4,  'position': 'CB',  'x': X_CENTER,          'y': Y_DEFENSIVE_LINE - 2},
        {'slot': 5,  'position': 'CB',  'x': 32,                'y': Y_DEFENSIVE_LINE},
        {'slot': 6,  'position': 'LWB', 'x': X_TOUCHLINE_LEFT,  'y': Y_WINGBACK_LINE},
        {'slot': 7,  'position': 'CM',  'x': X_HALF_RIGHT,      'y': Y_CENTRAL_MID},
        {'slot': 8,  'position': 'CM',  'x': X_CENTER,          'y': Y_CENTRAL_MID - 3},
        {'slot': 9,  'position': 'CM',  'x': X_HALF_LEFT,       'y': Y_CENTRAL_MID},
        {'slot': 10, 'position': 'ST',  'x': X_HALF_RIGHT,      'y': Y_FORWARD_LINE},
        {'slot': 11, 'position': 'ST',  'x': X_HALF_LEFT,       'y': Y_FORWARD_LINE},
    ],
}


# ---------------------------------------------------------------------------
# Formation helper functions
# ---------------------------------------------------------------------------

# Return the coordinate template for a formation code
def get_formation_template(formation_code: str) -> list[PositionSlot]:
    return FORMATION_TEMPLATES.get(formation_code, [])


# Return available formation codes with user-friendly labels
def get_available_formations() -> list[tuple[str, str]]:
    display_names = {
        '343': '3-4-3',
        '352': '3-5-2',

        '442': '4-4-2',
        '433': '4-3-3',
        '4321': '4-3-2-1',
        '424': '4-2-4',
        '4231': '4-2-3-1',
        '4222': '4-2-2-2',
        '4141': '4-1-4-1',
        '41212': '4-1-2-1-2 (Diamond)',

        '532': '5-3-2',
        '523': '5-2-3',
        '5221': '5-2-2-1',
        '5212': '5-2-1-2',        
    }
    return [(code, display_names.get(code, code)) for code in FORMATION_TEMPLATES.keys()]


# Validate a formation template for slot count, slot sequence, coordinates, and goalkeeper count
def validate_formation_template(template: list[PositionSlot]) -> list[str]:
    errors = []
    
    if len(template) != 11:
        errors.append(f"Formation must have exactly 11 slots, got {len(template)}")
    
    slots = [p['slot'] for p in template]
    if sorted(slots) != list(range(1, 12)):
        errors.append("Slot numbers must be 1-11 with no gaps or duplicates")
    
    for p in template:
        if not (0 <= p['x'] <= 100):
            errors.append(f"Slot {p['slot']}: x must be 0-100, got {p['x']}")
        if not (0 <= p['y'] <= 100):
            errors.append(f"Slot {p['slot']}: y must be 0-100, got {p['y']}")
    
    gk_count = sum(1 for p in template if p['position'] == 'GK')
    if gk_count != 1:
        errors.append(f"Formation must have exactly 1 GK, got {gk_count}")
    
    return errors