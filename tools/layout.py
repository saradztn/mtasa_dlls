"""PROJECT ROYAL FORTRESS - architectural master data (single source of truth).
Every room, door, stair and interactive element here drives BOTH the exported geometry
and data/rooms.json (validator + Lua). World axes: +x east, +y north, z up (GTA)."""
from __future__ import annotations
import math

BASE = 2500.0
W = BASE + 2.0           # global water plane (moat, river, sea) - createWater, not shallow
G = W + 14.0             # castle plateau / courtyards (2516)
L0 = G + 1.5             # palace ground floor (2517.5)
DIM = 779
PALACE_DY = 24.0         # palace-local y + 24 = world y (keeps the footprint on the 8 m grid)
APO_WALL = 165.0 * math.cos(math.radians(15))   # curtain wall centre-line apothem (159.38)
R_TOWER = 165.0          # wall tower centres (polygon vertices)
APO_REV = 172.0          # moat revetment outer face
APO_MOAT_OUT = 196.0
INT_T = 0.6              # interior partition thickness
SLAB = 0.35

BLOCKS = {  # exterior wall thickness, ground level for plinths, roof style, facade material
    'palace':    {'t': 1.2, 'plinth': 1.5, 'ground': G, 'roof': 'palace', 'facade': 'rf_stone', 'win': 'palace'},
    'keep':      {'t': 2.0, 'ground': G, 'roof': 'keep', 'facade': 'rf_stonedark', 'win': 'keep'},
    'link':      {'t': 1.2, 'ground': G, 'roof': 'flat', 'facade': 'rf_stone', 'win': 'none'},
    'barracks':  {'t': 0.9, 'ground': G, 'roof': 'gable_x', 'facade': 'rf_stonedark', 'win': 'small'},
    'gatehouse': {'t': 1.5, 'plinth': 0.0, 'ground': G + 10, 'roof': 'flat', 'facade': 'rf_stonedark', 'win': 'slit'},
    'chapel':    {'t': 1.0, 'ground': G, 'roof': 'gable_x', 'facade': 'rf_stone', 'win': 'chapel'},
}


def P(x0, y0, x1, y1):
    return (x0, y0 + PALACE_DY, x1, y1 + PALACE_DY)


ROOMS = []


def room(rid, name, block, rect, z0, h, kind='room', cat='', floor='rf_marble', wall='rf_plaster', ceil='rf_ceiling',
         light='warm', windows=True, special=None, level=''):
    ROOMS.append(dict(id=str(rid), name=name, block=block, rect=tuple(float(v) for v in rect), z0=float(z0), h=float(h),
                      kind=kind, category=cat, floor=floor, wall=wall, ceil=ceil, light=light, windows=windows,
                      special=special or {}, level=level, shape='rect'))


# ---------------------------------------------------------------- PALACE ground floor (L0)
R0, R1, RB1, RB2 = L0, L0 + 7.0, L0 - 5.0, L0 - 10.0
room(1, 'Entrance Vestibule', 'palace', P(-10, -40, 10, -30), R0, 7, cat='royal', floor='rf_marble', level='L0')
room('SW', 'West Grand Staircase', 'palace', P(-22, -40, -10, -30), R0, 12.5, kind='stair', cat='circulation', floor='rf_marble',
     special={'stair': 'U', 'entry': 'E', 'rise': 7.0}, level='L0-L1')
room('SE', 'East Grand Staircase', 'palace', P(10, -40, 22, -30), R0, 12.5, kind='stair', cat='circulation', floor='rf_marble',
     special={'stair': 'U', 'entry': 'W', 'rise': 7.0}, level='L0-L1')
room(2, 'Reception Hall', 'palace', P(-16, -30, 16, -14), R0, 7, cat='royal', level='L0')
room(3, 'Throne Hall', 'palace', P(-16, -14, 16, 40), R0, 12.5, cat='royal', wall='rf_stone', ceil='rf_ceiling', level='L0-L1',
     special={'hero': True})
room('CW', 'West Grand Gallery', 'palace', P(-22, -30, -16, 40), R0, 7, kind='corridor', cat='circulation', floor='rf_marble', level='L0')
room('CE', 'East Grand Gallery', 'palace', P(16, -30, 22, 40), R0, 7, kind='corridor', cat='circulation', floor='rf_marble', level='L0')
room(4, 'Audience Chamber', 'palace', P(-40, -40, -22, -24), R0, 7, cat='royal', level='L0')
room(5, 'Council Chamber', 'palace', P(-40, -24, -22, -8), R0, 7, cat='royal', floor='rf_woodlight', level='L0')
room(9, 'History Gallery', 'palace', P(-40, -8, -22, 8), R0, 7, cat='royal', level='L0')
room(7, 'Ballroom', 'palace', P(-40, 8, -22, 40), R0, 7, cat='royal', level='L0')
room('KW', 'West Wing Corridor', 'palace', P(-44, -40, -40, 40), R0, 7, kind='corridor', cat='circulation', floor='rf_woodlight', level='L0')
room(10, 'Reception Room', 'palace', P(-64, -40, -44, -28), R0, 7, cat='royal', floor='rf_woodlight', level='L0')
room(25, 'Scribe Office', 'palace', P(-64, -28, -44, -18), R0, 7, cat='knowledge', floor='rf_woodlight', level='L0')
room(23, 'Map Room', 'palace', P(-64, -18, -44, -6), R0, 7, cat='knowledge', floor='rf_woodlight', level='L0')
room(26, 'Royal Treasury', 'palace', P(-64, -6, -44, 4), R0, 7, cat='knowledge', floor='rf_marble', wall='rf_stone', windows=False, level='L0')
room('HS', 'Hidden Stair', 'palace', P(-64, 4, -44, 10), RB1, 12, kind='stair', cat='secret', floor='rf_dungeon', wall='rf_dungeon',
     ceil='rf_dungeon', light='dim', windows=False, special={'stair': 'I', 'top': 'E', 'rise': 5.0, 'secret': True}, level='L-1-L0')
room(21, 'Grand Library', 'palace', P(-64, 10, -44, 40), R0, 12.5, cat='knowledge', floor='rf_woodlight', wall='rf_wood', level='L0-L1',
     special={'gallery': True})
room(27, 'Artifact Gallery', 'palace', P(22, -40, 40, -24), R0, 7, cat='knowledge', level='L0')
room(8, 'Portrait Gallery', 'palace', P(22, -24, 40, 8), R0, 7, cat='royal', floor='rf_woodlight', level='L0')
room(6, 'Banquet Hall', 'palace', P(22, 8, 40, 40), R0, 7, cat='royal', floor='rf_woodlight', wall='rf_stone', level='L0')
room('KE', 'East Wing Corridor', 'palace', P(40, -40, 44, 40), R0, 7, kind='corridor', cat='circulation', floor='rf_woodlight', level='L0')
room('SH', 'Service Hall', 'palace', P(44, -40, 64, -30), R0, 7, kind='corridor', cat='service', floor='rf_cobble', wall='rf_stone', level='L0')
room(46, 'Laundry & Maintenance', 'palace', P(44, -30, 64, -20), R0, 7, cat='service', floor='rf_cobble', wall='rf_stone', light='work', level='L0')
room(44, "Servants' Dining", 'palace', P(44, -20, 64, -6), R0, 7, cat='service', floor='rf_woodlight', light='work', level='L0')
room('SS', 'Service Stair', 'palace', P(44, -6, 64, 2), RB1, 12, kind='stair', cat='service', floor='rf_cobble', wall='rf_stone', ceil='rf_plaster',
     light='work', special={'stair': 'I', 'top': 'E', 'rise': 5.0}, level='L-1-L0')
room(42, 'Food Preparation Room', 'palace', P(44, 2, 64, 14), R0, 7, cat='service', floor='rf_cobble', wall='rf_stone', light='work', level='L0')
room(41, 'Royal Kitchen', 'palace', P(44, 14, 64, 40), R0, 7, cat='service', floor='rf_cobble', wall='rf_stone', ceil='rf_plaster', light='work', level='L0')

# ---------------------------------------------------------------- PALACE upper floor (L1)
room(20, 'Guard Antechamber', 'palace', P(-10, -40, 10, -30), R1, 5.5, cat='private', floor='rf_woodlight', wall='rf_stone', level='L1')
room(24, 'War Room', 'palace', P(-16, -30, 16, -14), R1, 5.5, cat='knowledge', floor='rf_woodlight', wall='rf_wood', level='L1')
room('CW1', 'West Upper Gallery', 'palace', P(-22, -30, -16, 40), R1, 5.5, kind='corridor', cat='circulation', floor='rf_woodlight', level='L1')
room('CE1', 'East Upper Gallery', 'palace', P(16, -30, 22, 40), R1, 5.5, kind='corridor', cat='circulation', floor='rf_woodlight', level='L1')
room(11, 'Royal Bedroom', 'palace', P(-40, -40, -22, -22), R1, 5.5, cat='private', floor='rf_woodlight', level='L1')
room(12, 'Dressing Chamber', 'palace', P(-40, -22, -22, -12), R1, 5.5, cat='private', floor='rf_woodlight', level='L1')
room(14, 'Royal Bathroom', 'palace', P(-40, -12, -22, -2), R1, 5.5, cat='private', floor='rf_marble', wall='rf_stone', level='L1')
room(13, 'Private Sitting Room', 'palace', P(-40, -2, -22, 12), R1, 5.5, cat='private', floor='rf_woodlight', level='L1')
room(15, 'Royal Study', 'palace', P(-40, 12, -22, 24), R1, 5.5, cat='private', floor='rf_woodlight', wall='rf_wood', level='L1')
room(18, "Queen's Suite", 'palace', P(-40, 24, -22, 40), R1, 5.5, cat='private', floor='rf_woodlight', level='L1')
room('KW1', 'West Upper Corridor', 'palace', P(-44, -40, -40, 40), R1, 5.5, kind='corridor', cat='circulation', floor='rf_woodlight', level='L1')
room(17, 'Guest Bedroom', 'palace', P(-64, -40, -44, -26), R1, 5.5, cat='private', floor='rf_woodlight', level='L1')
room(19, 'Family Chamber', 'palace', P(-64, -26, -44, -10), R1, 5.5, cat='private', floor='rf_woodlight', level='L1')
room(22, 'Restricted Archive', 'palace', P(-64, -10, -44, 10), R1, 5.5, cat='knowledge', floor='rf_woodlight', wall='rf_wood', windows=False, light='dim', level='L1')
room(29, "Scholar's Study", 'palace', P(22, -40, 40, -26), R1, 5.5, cat='knowledge', floor='rf_woodlight', wall='rf_wood', level='L1')
room(30, 'Alchemy Laboratory', 'palace', P(22, -26, 40, -10), R1, 5.5, cat='knowledge', floor='rf_dungeon', wall='rf_stone', light='alchemy', level='L1')
room('EG', 'East Portrait Loft', 'palace', P(22, -10, 40, 40), R1, 5.5, kind='room', cat='extra', floor='rf_woodlight', level='L1')
room('KE1', 'East Upper Corridor', 'palace', P(40, -40, 44, 40), R1, 5.5, kind='corridor', cat='circulation', floor='rf_woodlight', level='L1')
room('ST', "Steward's Office", 'palace', P(44, -40, 64, -20), R1, 5.5, cat='extra', floor='rf_woodlight', level='L1')
room('WS', 'Wardrobe & Linen Store', 'palace', P(44, -20, 64, 0), R1, 5.5, cat='extra', floor='rf_woodlight', light='dim', level='L1')
room('GS', 'East Guest Suite', 'palace', P(44, 0, 64, 20), R1, 5.5, cat='extra', floor='rf_woodlight', level='L1')
room('MR', "Minstrels' Room", 'palace', P(44, 20, 64, 40), R1, 5.5, cat='extra', floor='rf_woodlight', level='L1')

# ---------------------------------------------------------------- BASEMENT (L-1) and DUNGEON (L-2)
room('LC', 'Cellar Corridor', 'palace', P(16, -6, 44, 2), RB1, 5, kind='corridor', cat='service', floor='rf_cobble', wall='rf_dungeon', ceil='rf_dungeon',
     light='cellar', windows=False, level='L-1')
room('WC', 'Wine Cellar', 'palace', P(22, 2, 44, 20), RB1, 5, cat='service', floor='rf_cobble', wall='rf_dungeon', ceil='rf_dungeon', light='cellar', windows=False, level='L-1')
room(43, 'Pantry & Cold Storage', 'palace', P(44, 2, 64, 20), RB1, 5, cat='service', floor='rf_cobble', wall='rf_dungeon', ceil='rf_dungeon', light='cellar', windows=False, level='L-1')
room(45, "Servants' Quarters", 'palace', P(44, -26, 64, -6), RB1, 5, cat='service', floor='rf_woodlight', wall='rf_plaster', ceil='rf_dungeon', light='cellar', windows=False, level='L-1')
room('DS', 'Dungeon Stair', 'palace', P(22, -16, 44, -6), RB2, 10, kind='stair', cat='underground', floor='rf_dungeon', wall='rf_dungeon', ceil='rf_dungeon',
     light='dungeon', windows=False, special={'stair': 'I', 'top': 'E', 'rise': 5.0}, level='L-2-L-1')
room('SC', 'Secret Corridor', 'palace', P(-64, -24, -58, 4), RB1, 5, kind='corridor', cat='secret', floor='rf_dungeon', wall='rf_dungeon', ceil='rf_dungeon',
     light='dungeon', windows=False, level='L-1')
room('VS', 'Vault Stair', 'palace', P(-64, -34, -44, -24), RB2, 10, kind='stair', cat='secret', floor='rf_dungeon', wall='rf_dungeon', ceil='rf_dungeon',
     light='dungeon', windows=False, special={'stair': 'I', 'top': 'W', 'rise': 5.0, 'secret': True}, level='L-2-L-1')
room(47, 'Main Dungeon', 'palace', P(-8, -16, 22, 2), RB2, 5, cat='underground', floor='rf_dungeon', wall='rf_dungeon', ceil='rf_dungeon', light='dungeon', windows=False, level='L-2')
room(48, 'Prison Cells', 'palace', P(-8, -34, 22, -16), RB2, 5, cat='underground', floor='rf_dungeon', wall='rf_dungeon', ceil='rf_dungeon', light='dungeon', windows=False, level='L-2')
room(49, 'Interrogation Room', 'palace', P(-24, -16, -8, 2), RB2, 5, cat='underground', floor='rf_dungeon', wall='rf_dungeon', ceil='rf_dungeon', light='dungeon', windows=False, level='L-2')
room(50, 'Secret Vault', 'palace', P(-64, -24, -44, -4), RB2, 5, cat='underground', floor='rf_marble', wall='rf_dungeon', ceil='rf_dungeon', light='vault', windows=False, level='L-2')

# ---------------------------------------------------------------- KEEP + passage
room('KP', 'Keep Passage', 'link', P(-3, 40, 3, 46), R0, 5, kind='corridor', cat='circulation', floor='rf_marble', wall='rf_stone', windows=True, level='L0')
room('K0', 'Keep Guard Hall', 'keep', P(-14, 46, 14, 70), R0, 7, cat='extra', floor='rf_cobble', wall='rf_stone', special={'spiral': 'keep'}, level='K0')
room('K1', 'Royal Research Lab', 'keep', P(-14, 46, 14, 70), R0 + 7, 7, cat='extra', floor='rf_woodlight', wall='rf_stone', light='alchemy', special={'spiral': 'keep'}, level='K1')
room('K2', 'Keep Lookout Chamber', 'keep', P(-14, 46, 14, 70), R0 + 14, 7, cat='extra', floor='rf_woodlight', wall='rf_stone', special={'spiral': 'keep'}, level='K2')

# ---------------------------------------------------------------- tower link passages (palace <-> round towers)
TOWERS = {  # palace corner towers: centre (world), levels (floor z), room ids per level
    'NW': {'c': (-74.0, 56.0), 'door': 0.0, 'rooms': ['TNW0', 'TNW1', '16']},
    'SW': {'c': (-74.0, -8.0), 'door': 0.0, 'rooms': ['TSW0', 'TSW1', 'TSW2']},
    'NE': {'c': (74.0, 56.0), 'door': 180.0, 'rooms': ['TNE0', 'TNE1', '28']},
    'SE': {'c': (74.0, -8.0), 'door': 180.0, 'rooms': ['TSE0', 'TSE1', 'TSE2']},
}
TOWER_LEVELS = [(R0, 7.0), (R0 + 7.0, 5.5), (R0 + 12.5, 6.0)]
TOWER_APO = 7.4          # wall centre-line apothem (24-gon), thickness 1.2
for key, t in TOWERS.items():
    cx, cy = t['c']; sgn = 1 if cx > 0 else -1
    x_in, x_out = (64.0, 66.6) if sgn > 0 else (-66.6, -64.0)
    for li, (z, h) in enumerate(TOWER_LEVELS[:2]):
        room('L' + key + str(li), key + ' Tower Link ' + ('ground' if li == 0 else 'upper'), 'link', (x_in, cy - 1.8, x_out, cy + 1.8), z, h,
             kind='corridor', cat='circulation', floor='rf_marble', wall='rf_stone', windows=False, level='L%d' % li,
             special={'open_edges': ('E',) if sgn > 0 else ('W',), 'tower': key})
TOWER_NAMES = {'TNW0': 'NW Tower Library Turret', 'TNW1': 'NW Tower Upper Landing', '16': 'Balcony Chamber',
               'TSW0': 'SW Tower Ground Landing', 'TSW1': 'SW Tower Upper Landing', 'TSW2': 'West Lookout',
               'TNE0': 'NE Tower Kitchen Store', 'TNE1': 'NE Tower Upper Landing', '28': 'Observatory',
               'TSE0': 'SE Tower Ground Landing', 'TSE1': 'SE Tower Upper Landing', 'TSE2': 'Bell Chamber'}

# ---------------------------------------------------------------- BARRACKS (military ward)
BX, BY = -112.0, -40.0
def B(x0, y0, x1, y1):
    return (x0 + BX, y0 + BY, x1 + BX, y1 + BY)
BG = G + 0.6
room(31, 'Guard Barracks', 'barracks', B(-24, -12, -4, 2), BG, 5, cat='military', floor='rf_woodlight', wall='rf_stone', light='work', level='B0')
room('BH', 'Barracks Stair Hall', 'barracks', B(-24, 2, -12, 12), BG, 10, kind='stair', cat='circulation', floor='rf_cobble', wall='rf_stone',
     ceil='rf_plaster', light='work', special={'stair': 'U', 'entry': 'E', 'rise': 5.0}, level='B0-B1')
room(38, 'Equipment Storage', 'barracks', B(-12, 2, -4, 12), BG, 5, cat='military', floor='rf_cobble', wall='rf_stone', light='work', level='B0')
room(40, 'Military Supply', 'barracks', B(-4, -12, 4, 12), BG, 5, cat='military', floor='rf_cobble', wall='rf_stone', light='work', level='B0')
room(37, 'Training Hall', 'barracks', B(4, -12, 24, 12), BG, 10, cat='military', floor='rf_woodlight', wall='rf_stone', ceil='rf_plaster', light='work', level='B0-B1')
room(32, "Officers' Quarters", 'barracks', B(-24, -12, -12, 2), BG + 5, 4.6, cat='military', floor='rf_woodlight', wall='rf_plaster', level='B1')
room(35, 'Command Room', 'barracks', B(-12, -12, 4, 2), BG + 5, 4.6, cat='military', floor='rf_woodlight', wall='rf_wood', level='B1')
room(33, 'Armory', 'barracks', B(-12, 2, -4, 12), BG + 5, 4.6, cat='military', floor='rf_cobble', wall='rf_stone', light='work', level='B1')
room(34, 'Weapon Room', 'barracks', B(-4, 2, 4, 12), BG + 5, 4.6, cat='military', floor='rf_cobble', wall='rf_stone', light='work', level='B1')

# ---------------------------------------------------------------- GATEHOUSE upper room + CHAPEL
room(39, 'Gatehouse Storage', 'gatehouse', (-9.0, -APO_WALL - 6.0, 9.0, -APO_WALL + 3.4), G + 10, 5, cat='military', floor='rf_woodlight', wall='rf_stone',
     ceil='rf_plaster', light='work', level='G+10')
CX, CY = 96.0, 100.0
room('CH', 'Grand Chapel', 'chapel', (CX - 16, CY - 8, CX + 16, CY + 8), G + 0.6, 11, cat='extra', floor='rf_marble', wall='rf_stone', ceil='rf_ceiling',
     light='chapel', level='G')

# Wall towers: 12 at the polygon vertices; walk-level rooms. V7 (135 deg) is room 36 Watchtower.
WALL_TOWERS = []
for k in range(12):
    a = -75 + 30 * k
    WALL_TOWERS.append({'k': k, 'angle': float(a), 'c': (R_TOWER * math.cos(math.radians(a)), R_TOWER * math.sin(math.radians(a))),
                        'id': '36' if k == 7 else 'WT%d' % k, 'name': 'Watchtower' if k == 7 else 'Wall Tower %d Guard Post' % (k + 1)})
WALK_Z = G + 10.0

# ---------------------------------------------------------------- DOORS / CONNECTIONS
# (a, b, at, width, height, kind, interactive_id). b == 'EXT' -> exterior (side inferred).
# z base = max floor of the two rooms at that position (validator checks both floors match).
DOORS = []
def door(a, b, at=None, w=1.8, h=3.2, kind='arch', iid=None, z=None, side=None, sill=0.0):
    DOORS.append(dict(a=str(a), b=str(b), at=at, w=w, h=h, kind=kind, iid=iid, z=z, side=side, sill=sill))

Y = PALACE_DY
# ground floor
door(1, 'EXT', 0, 3.4, 4.6, 'interactive', 'palace_doors', side='S')
door(1, 'SW', -35 + Y, 2.4, 4.0); door(1, 'SE', -35 + Y, 2.4, 4.0)
door(1, 2, 0, 3.4, 4.6)
door(2, 3, 0, 4.0, 5.6, 'interactive', 'throne_doors')
door(2, 'CW', -22 + Y, 2.4, 4.0); door(2, 'CE', -22 + Y, 2.4, 4.0)
door(3, 'CW', 0 + Y, 2.4, 4.0); door(3, 'CW', 26 + Y, 2.4, 4.0)
door(3, 'CE', 0 + Y, 2.4, 4.0); door(3, 'CE', 26 + Y, 2.4, 4.0)
door(3, 'KP', 0, 2.6, 4.0)
door('CW', 4, -27 + Y, 2.0, 3.4); door('CW', 5, -16 + Y, 2.0, 3.4); door('CW', 9, 0 + Y, 2.0, 3.4)
door('CW', 7, 16 + Y, 2.4, 3.6); door('CW', 7, 32 + Y, 2.4, 3.6)
door('KW', 4, -37 + Y); door('KW', 5, -16 + Y); door('KW', 9, 0 + Y); door('KW', 7, 24 + Y, 2.4, 3.6)
door('KW', 'EXT', -42, 2.2, 3.4, side='S'); door('KW', 'EXT', -42, 2.2, 3.4, side='N')
door('KW', 10, -34 + Y); door('KW', 25, -23 + Y); door('KW', 23, -12 + Y)
door('KW', 26, -1 + Y, 1.8, 3.2, 'interactive', 'treasury_door')
door('KW', 21, 25 + Y, 2.4, 3.6)
door(21, 'HS', -46, 1.6, 2.9, 'secret', 'library_bookcase')
door(23, 25, -54); door(25, 10, -54)
door('CE', 27, -27 + Y, 2.0, 3.4); door('CE', 8, -16 + Y, 2.0, 3.4); door('CE', 8, 0 + Y, 2.0, 3.4)
door('CE', 6, 16 + Y, 2.4, 3.6); door('CE', 6, 32 + Y, 2.4, 3.6)
door('KE', 27, -32 + Y); door('KE', 8, -8 + Y); door('KE', 6, 24 + Y, 2.4, 3.6)
door('KE', 'EXT', 42, 2.2, 3.4, side='S'); door('KE', 'EXT', 42, 2.2, 3.4, side='N')
door('KE', 'SH', -35 + Y); door('KE', 46, -25 + Y); door('KE', 44, -13 + Y); door('KE', 42, 8 + Y); door('KE', 41, 27 + Y, 2.4, 3.6)
door('SH', 'EXT', 54, 2.4, 3.4, 'interactive', 'service_door', side='S')
door('SH', 46, 54); door(44, 'SS', 61.7, 1.6, 3.0); door(42, 'SS', 61.7, 1.6, 3.0); door(42, 41, 54)
door(10, 'LSW0', -32 + Y); door('LSW0', 'TSW0', -32 + Y)
door(21, 'LNW0', 32 + Y); door('LNW0', 'TNW0', 32 + Y)
door('SH', 'LSE0', -32 + Y); door('LSE0', 'TSE0', -32 + Y)
door(41, 'LNE0', 32 + Y); door('LNE0', 'TNE0', 32 + Y)
# upper floor
door('SW', 20, -35 + Y, 2.0, 3.2, z=R1); door('SW', 24, -12, 1.8, 3.2, z=R1)
door('SE', 20, -35 + Y, 2.0, 3.2, z=R1); door('SE', 24, 12, 1.8, 3.2, z=R1)
door(20, 24, 0, 2.0, 3.2)
door(24, 'CW1', -22 + Y); door(24, 'CE1', -22 + Y)
door(24, 3, 0, 8.0, 3.0, 'window', sill=1.0)
for yy in (-4, 8, 20, 32):
    door(3, 'CW1', yy + Y, 3.0, 3.0, 'window', z=R1, sill=0.9); door(3, 'CE1', yy + Y, 3.0, 3.0, 'window', z=R1, sill=0.9)
door('CW1', 11, -26 + Y, 1.8, 3.2, 'interactive', 'royal_bedroom_door')
door('CW1', 12, -17 + Y); door('CW1', 13, 5 + Y); door('CW1', 15, 18 + Y); door('CW1', 18, 32 + Y)
door(11, 12, -31); door(12, 14, -31); door(13, 15, -31); door(18, 15, -31)
door('KW1', 11, -31 + Y); door('KW1', 13, 5 + Y); door('KW1', 18, 32 + Y)
door('KW1', 17, -33 + Y); door('KW1', 19, -18 + Y)
door('KW1', 22, 0 + Y, 1.8, 3.2, 'interactive', 'archive_door')
door('KW1', 21, 25 + Y, 2.0, 3.2, z=R1)
door(17, 'LSW1', -32 + Y); door('LSW1', 'TSW1', -32 + Y)
door(21, 'LNW1', 32 + Y, z=R1); door('LNW1', 'TNW1', 32 + Y)
door('CE1', 29, -28 + Y); door('CE1', 30, -18 + Y, 1.8, 3.2, 'interactive', 'alchemy_door'); door('CE1', 'EG', 0 + Y); door('CE1', 'EG', 26 + Y)
door('KE1', 29, -33 + Y); door('KE1', 30, -14 + Y); door('KE1', 'EG', 15 + Y)
door('KE1', 'ST', -30 + Y); door('KE1', 'WS', -10 + Y); door('KE1', 'GS', 10 + Y); door('KE1', 'MR', 30 + Y)
door('ST', 'LSE1', -32 + Y); door('LSE1', 'TSE1', -32 + Y)
door('MR', 'LNE1', 32 + Y); door('LNE1', 'TNE1', 32 + Y)
# basement / dungeon
door('SS', 'LC', -2 + Y, 2.0, 3.0, z=RB1); door('SS', 43, 48, 2.0, 3.0, z=RB1); door('SS', 45, 48, 2.0, 3.0, z=RB1)
door('LC', 'WC', 33, 2.0, 3.0); door('LC', 'DS', 42, 1.6, 3.0, z=RB1)
door('HS', 'SC', -61, 1.6, 2.8, z=RB1); door('SC', 'VS', -62, 1.6, 2.8, z=RB1)
door('DS', 47, -11 + Y, 2.4, 3.2, 'interactive', 'dungeon_gate', z=RB2)
door(47, 48, 7, 2.4, 3.2)
door(47, 'TN', 0, 2.4, 3.0, 'interactive', 'tunnel_gate', side='N')
door(47, 49, -7 + Y, 1.8, 3.0, 'interactive', 'interrogation_door')
door('VS', 50, -48, 2.0, 3.0, 'interactive', 'vault_door', z=RB2)
# keep
door('KP', 'K0', 0, 2.4, 3.8)
door('K0', 'EXT', 0, 2.6, 4.0, 'interactive', 'keep_door', side='N')
# barracks
door(31, 'EXT', -14 + BX, 2.0, 3.0, side='S'); door(40, 'EXT', 0 + BX, 2.4, 3.2, side='S'); door(37, 'EXT', 14 + BX, 3.0, 3.6, side='S')
door(31, 'BH', -14 + BX, 1.8, 3.0); door(38, 'BH', 7 + BY, 1.8, 3.0); door(38, 40, 7 + BY); door(40, 37, 0 + BY, 2.4, 3.2)
door('BH', 33, 7 + BY, 1.8, 3.0, 'interactive', 'armory_door', z=BG + 5); door('BH', 32, -14 + BX, 1.8, 3.0, z=BG + 5)
door(32, 35, -5 + BY); door(35, 33, -8 + BX); door(33, 34, 7 + BY)
door(35, 37, -5 + BY, 4.0, 2.4, 'window', z=BG + 5, sill=1.0); door(34, 37, 7 + BY, 3.0, 2.4, 'window', z=BG + 5, sill=1.0)
# gatehouse room <-> wall walk; chapel
door(39, 'EXT', -APO_WALL + 0.1, 1.6, 2.8, side='W'); door(39, 'EXT', -APO_WALL + 0.1, 1.6, 2.8, side='E')
door('CH', 'EXT', CY, 3.0, 4.6, 'interactive', 'chapel_doors', side='W')

# ---------------------------------------------------------------- INTERACTIVE ELEMENTS (server state + client animation)
# kind: swing (rotate about hinge), slide (translate), lift (portcullis), bridge (rotate about x)
INTERACTIVE = {
    'drawbridge':        {'name': 'Drawbridge', 'kind': 'bridge', 'acl': 'gate', 'default': 'open', 'model': 'it_drawbridge'},
    'main_portcullis':   {'name': 'Main Gate Portcullis', 'kind': 'lift', 'acl': 'gate', 'default': 'open', 'model': 'it_portcullis'},
    'gate_doors':        {'name': 'Gatehouse Inner Doors', 'kind': 'swing2', 'acl': None, 'default': 'open', 'model': 'it_gateleaf'},
    'service_gate':      {'name': 'Service Gate', 'kind': 'swing2', 'acl': None, 'default': 'closed', 'model': 'it_gateleaf_s'},
    'palace_doors':      {'name': 'Palace Great Doors', 'kind': 'swing2', 'acl': None, 'default': 'closed', 'model': None},
    'throne_doors':      {'name': 'Throne Hall Doors', 'kind': 'swing2', 'acl': None, 'default': 'closed', 'model': None},
    'treasury_door':     {'name': 'Treasury Door', 'kind': 'swing', 'acl': 'vault', 'default': 'closed', 'model': 'it_irondoor'},
    'library_bookcase':  {'name': 'Secret Bookcase', 'kind': 'slide', 'acl': None, 'default': 'closed', 'model': 'it_bookcase', 'needs': 'book_lever'},
    'book_lever':        {'name': 'Loose Red Book', 'kind': 'lever', 'acl': None, 'default': 'closed', 'model': 'it_booklever'},
    'archive_door':      {'name': 'Restricted Archive Door', 'kind': 'swing', 'acl': 'archive', 'default': 'closed', 'model': None},
    'royal_bedroom_door': {'name': 'Royal Bedroom Door', 'kind': 'swing', 'acl': None, 'default': 'closed', 'model': None},
    'alchemy_door':      {'name': 'Alchemy Laboratory Door', 'kind': 'swing', 'acl': None, 'default': 'closed', 'model': None},
    'dungeon_gate':      {'name': 'Dungeon Gate', 'kind': 'swing', 'acl': None, 'default': 'closed', 'model': 'it_bardoor'},
    'interrogation_door': {'name': 'Interrogation Room Door', 'kind': 'swing', 'acl': None, 'default': 'closed', 'model': 'it_irondoor'},
    'vault_door':        {'name': 'Secret Vault Door', 'kind': 'vault', 'acl': 'vault', 'default': 'closed', 'model': 'it_vaultdoor'},
    'tunnel_gate':       {'name': 'Escape Tunnel Gate', 'kind': 'swing', 'acl': None, 'default': 'closed', 'model': 'it_bardoor'},
    'dock_gate':         {'name': 'Secret Exit Water Gate', 'kind': 'lift', 'acl': None, 'default': 'closed', 'model': 'it_watergate'},
    'keep_door':         {'name': 'Keep Garden Door', 'kind': 'swing', 'acl': None, 'default': 'closed', 'model': None},
    'armory_door':       {'name': 'Armory Door', 'kind': 'swing', 'acl': None, 'default': 'closed', 'model': 'it_irondoor'},
    'chapel_doors':      {'name': 'Chapel Doors', 'kind': 'swing2', 'acl': None, 'default': 'open', 'model': None},
    'service_door':      {'name': 'Palace Service Door', 'kind': 'swing', 'acl': None, 'default': 'closed', 'model': None},
}
for i in range(6):
    INTERACTIVE['cell_%d' % (i + 1)] = {'name': 'Prison Cell %d' % (i + 1), 'kind': 'slide', 'acl': None, 'default': 'closed' if i % 2 == 0 else 'open', 'model': 'it_celldoor'}

PUBLIC_TELEPORTS = {  # id: (label, x, y, z, rot)
    'gate':      ('Main Gate (outside the drawbridge)', 0.0, -212.0, None, 0.0),
    'interior':  ('Throne Hall', 0.0, 4.0 + PALACE_DY, L0, 0.0),
    'showp':     ('Scenic overlook (Belvedere Hill)', -315.2, -235.9, None, 315.0),
    'keeproof':  ('Great Keep roof', 6.0, 58.0 + PALACE_DY, L0 + 21.0, 180.0),
}
