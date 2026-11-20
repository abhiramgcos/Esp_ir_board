"""Footprint placement (KiCad mm, y down). ref: (x, y, rotation_deg, side).

poor-man edition: 76 x 52 mm, all through-hole, one component side.
  left      : ESP32 DevKit V1 in two 15-pin sockets. Antenna sticks out over the top edge, USB at the bottom.
  top-right : 2 IR LEDs + IR receiver lying flat, all facing up out of the top edge (away from the USB)
  right     : LED driver, receiver filter, USER button + LED, I2C pull-ups
  far right : 14-pin expansion header
"""
BOARD = (100, 100, 176, 152, 2.0)   # x0, y0, x1, y1, corner radius
HOLES = [(103.5, 103.5), (172.5, 103.5), (103.5, 149.0), (172.5, 149.0)]
# DevKit socket rows: 25.4 mm apart, pin 1 (EN / IO23) at the antenna end
SOCK_X = (108.5, 133.9)
SOCK_Y = 108.0

PLACE = {
    'H1': (*HOLES[0], 0, 'F'), 'H2': (*HOLES[1], 0, 'F'), 'H3': (*HOLES[2], 0, 'F'), 'H4': (*HOLES[3], 0, 'F'),
    'J1': (SOCK_X[0], SOCK_Y, 0, 'F'), 'J2': (SOCK_X[1], SOCK_Y, 0, 'F'),
    # IR LEDs and receiver lie flat, legs bent 90 deg, lenses/dome over the top edge
    'D1': (146.0, 110.0, 180, 'F'), 'D2': (154.0, 110.0, 180, 'F'),
    'U1': (165.5, 104.3, 180, 'F'),
    # LED driver
    'R3': (140.0, 114.5, 0, 'F'), 'C1': (151.5, 114.5, 0, 'F'),
    'Q1': (138.5, 120.0, 0, 'F'), 'R1': (148.0, 120.0, 0, 'F'), 'R2': (148.0, 124.0, 0, 'F'),
    # receiver filter
    'R4': (159.0, 124.0, 90, 'F'), 'C2': (162.8, 113.0, 0, 'F'),
    # user I/O
    'SW1': (140.0, 128.5, 0, 'F'), 'D3': (151.0, 130.75, 0, 'F'),
    'R6': (140.0, 138.5, 0, 'F'), 'R5': (150.0, 138.5, 0, 'F'),
    'R7': (140.0, 142.5, 0, 'F'), 'R8': (150.0, 142.5, 0, 'F'),
    'J3': (169.0, 110.5, 0, 'F'),
}

NETCLASS_POWER = ['GND', 'VIN', '+3V3', 'IR_A', 'IR_MID', 'IR_K']
