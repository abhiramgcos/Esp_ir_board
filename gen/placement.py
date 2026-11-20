"""Footprint placement (KiCad mm, y down). ref: (x, y, rotation_deg, side).

v2.1 compact layout: 68 x 48 mm (was 76 x 56, -23 % area).
  top-left  : power (EXT 5V, diode-OR, fuse, LDO)     top-right : IR transmit (2x TSAL6200, lying flat, facing out of the right edge)
  mid-left  : USB-C + ESD, CH340C, auto-reset          mid-right : IR receive (TSOP38238)
  centre    : ESP32 (antenna overhangs top edge), buttons row, pull-ups / user LED row
  bottom    : UART header J3 + 14-pin expansion J4 along the edge
"""
BOARD = (100, 100, 168, 148, 2.0)   # x0, y0, x1, y1, corner radius
HOLES = [(103.2, 103.2), (164.8, 103.2), (103.2, 144.8), (164.8, 144.8)]

PLACE = {
    'H1': (*HOLES[0], 0, 'F'), 'H2': (*HOLES[1], 0, 'F'), 'H3': (*HOLES[2], 0, 'F'), 'H4': (*HOLES[3], 0, 'F'),
    # ESP32: antenna overhangs the top board edge (~5.5 mm)
    'U1': (138, 110.25, 0, 'F'),
    'C6': (126.0, 103.6, 0, 'F'), 'R3': (126.0, 106.5, 0, 'F'), 'C7': (126.0, 109.0, 0, 'F'),
    'C5': (125.5, 113.3, 90, 'F'),
    # power
    'J2': (107.5, 103.5, 90, 'F'),
    'D2': (116.5, 103.5, 180, 'F'), 'D1': (116.5, 108.0, 180, 'F'),
    'F1': (110.0, 108.5, 90, 'F'),
    'C1': (110.5, 113.6, 90, 'F'), 'C2': (113.5, 113.6, 90, 'F'),
    'U2': (117.5, 113.6, 0, 'F'), 'C3': (121.5, 113.6, 90, 'F'),
    'R12': (117.5, 119.0, 0, 'F'), 'D5': (121.5, 119.0, 0, 'F'),
    # USB-C + ESD
    'J1': (103.05, 122.5, 270, 'F'),
    'R1': (111.5, 118.6, 0, 'F'), 'U3': (112.0, 122.5, 0, 'F'), 'R2': (111.5, 126.4, 0, 'F'),
    # USB-UART + auto-reset
    'U4': (118.0, 133.0, 90, 'F'), 'C8': (110.2, 133.0, 90, 'F'), 'R5': (125.5, 133.0, 90, 'F'),
    'R6': (110.5, 139.6, 0, 'F'), 'Q1': (115.0, 139.8, 0, 'F'),
    'R7': (120.0, 139.6, 0, 'F'), 'Q2': (124.5, 139.8, 0, 'F'),
    'J3': (107.5, 145.0, 90, 'F'),
    # buttons + pull-ups / user LED row
    # buttons sit 2 mm below the ESP32 (3.5 mm pad gap) so its bottom pins stay reachable for rework
    'SW1': (128.0, 125.0, 0, 'F'), 'SW2': (138.2, 125.0, 0, 'F'), 'SW3': (148.4, 125.0, 0, 'F'),
    'R4': (131.0, 134.0, 0, 'F'), 'R15': (136.0, 134.0, 0, 'F'), 'R16': (141.0, 134.0, 0, 'F'),
    'R14': (146.0, 134.0, 0, 'F'), 'R13': (151.0, 134.0, 0, 'F'), 'D6': (155.5, 134.0, 0, 'F'),
    'J4': (124.5, 145.0, 90, 'F'),
    # IR transmit
    'R10': (152.0, 103.5, 0, 'F'), 'C10': (152.0, 107.5, 0, 'F'),
    # IR LEDs lie flat (leads bent 90 deg), lenses point out of the right edge
    'D3': (157.5, 111.0, 90, 'F'), 'D4': (157.5, 119.5, 90, 'F'),
    'Q3': (152.5, 113.0, 0, 'F'), 'R8': (152.5, 117.0, 0, 'F'), 'R9': (152.5, 119.5, 0, 'F'),
    # IR receive: dome faces out of the right edge, same direction as the IR LEDs
    'U5': (163.5, 130.0, 90, 'F'), 'R11': (160.0, 124.0, 90, 'F'), 'C11': (160.0, 129.0, 90, 'F'),
}

NETCLASS_POWER = ['GND', 'VBUS', 'VBUS_F', 'VIN', 'EXT5V', '+3V3', 'IR_A', 'IR_MID', 'IR_K']
