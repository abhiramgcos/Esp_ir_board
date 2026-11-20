"""ESP32 IR Blaster - "poor-man" edition: every part through-hole, the ESP32 is a plug-in DevKit.

Order only the bare PCB and solder everything yourself with a normal iron. All parts are common in Indian
hobby shops (SP Road, Lamington Road, Ritchie Street) and on Robu.in / Amazon.in.
Same GPIOs as the SMD board, so the firmware and the ESPHome package run unchanged.

Each component: ref, lib_id, value, footprint, pins{pin_number: net}, schematic pos (x, y, rot).
Pins not listed are marked no-connect.
"""
RES = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal'    # 1/4 W carbon/metal film
ECAP = 'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm'                         # electrolytic, 5 mm can
IRLED = 'LED_THT:LED_D5.0mm_Horizontal_O1.27mm_Z3.0mm_Clear'           # lies flat, lens over the board edge
LED5 = 'LED_THT:LED_D5.0mm'
HDR = 'Connector_PinHeader_2.54mm:PinHeader_1x{:02d}_P2.54mm_Vertical'
SOCK = 'Connector_PinSocket_2.54mm:PinSocket_1x15_P2.54mm_Vertical'
BTN = 'Button_Switch_THT:SW_PUSH_6mm_H5mm'

comps = []


def add(ref, lib, value, fp, pins, pos, rot=0, mpn='', dnp=False, desc=''):
    comps.append(dict(ref=ref, lib=lib, value=value, fp=fp, pins=pins, pos=pos, rot=rot,
                      mpn=mpn, lcsc='', dnp=dnp, desc=desc))


def R(ref, val, a, b, pos, **kw):
    add(ref, 'Device:R', val, RES, {'1': a, '2': b}, pos, mpn=f'{val} 1/4 W axial', **kw)


def CP(ref, val, plus, minus, pos, **kw):
    add(ref, 'Device:C_Polarized', val, ECAP, {'1': plus, '2': minus}, pos, **kw)


# ---------------------------------------------------------------- ESP32 DevKit V1 (30 pin, DOIT layout)
# Seen from the top, antenna up, USB down. Rows are 25.4 mm (1 inch) apart.
DEVKIT_L = ['EN', 'VP', 'VN', '34', '35', '32', '33', '25', '26', '27', '14', '12', '13', 'GND', 'VIN']
DEVKIT_R = ['23', '22', 'TX0', 'RX0', '21', '19', '18', '5', 'TX2', 'RX2', '4', '2', '15', 'GND', '3V3']
left = {'4': 'IO34', '5': 'IO35', '6': 'IO32', '7': 'IO33', '8': 'IO25', '9': 'IO26',
        '13': 'BTN_USER', '14': 'GND', '15': 'VIN'}
right = {'1': 'IO23', '2': 'SCL', '5': 'SDA', '6': 'IO19', '7': 'IO18',
         '10': 'IR_RX', '11': 'IR_TX', '12': 'LED_USER', '14': 'GND', '15': '+3V3'}
add('J1', 'Connector_Generic:Conn_01x15', 'DevKit left', SOCK, left, (60, 120),
    mpn='15-pin female header 2.54 mm', desc='ESP32 DevKit V1 30-pin, left row')
add('J2', 'Connector_Generic:Conn_01x15', 'DevKit right', SOCK, right, (120, 120),
    mpn='15-pin female header 2.54 mm', desc='ESP32 DevKit V1 30-pin, right row')

# ---------------------------------------------------------------- IR transmit: 2 LEDs in series, ~80 mA
R('R3', '22R', 'VIN', 'IR_A', (200, 45), desc='LED current: (5 - 2x1.3 - 0.2) V / 22 R = ~85 mA')
add('D1', 'Device:LED', 'IR 940nm', IRLED, {'2': 'IR_A', '1': 'IR_MID'}, (215, 55),
    mpn='5 mm 940 nm IR LED (TSAL6200 or any "IR transmitter LED")')
add('D2', 'Device:LED', 'IR 940nm', IRLED, {'2': 'IR_MID', '1': 'IR_K'}, (215, 72),
    mpn='5 mm 940 nm IR LED (TSAL6200 or any "IR transmitter LED")')
add('Q1', 'Transistor_BJT:S8050', 'S8050', 'Package_TO_SOT_THT:TO-92_Inline_Wide',
    {'1': 'GND', '2': 'IR_B', '3': 'IR_K'}, (215, 95), mpn='S8050 or 2N2222A (TO-92, E-B-C)')
R('R1', '470R', 'IR_TX', 'IR_B', (190, 95))
R('R2', '10k', 'IR_B', 'GND', (200, 110), desc='keeps the LEDs off while the ESP32 boots')
CP('C1', '100uF', 'VIN', 'GND', (235, 50), mpn='100 uF 16 V electrolytic', desc='reservoir for the LED pulses')

# ---------------------------------------------------------------- IR receive
add('U1', 'Interface_Optical:TSOP382xx', 'VS1838B', 'OptoDevice:Vishay_MOLD-3Pin',
    {'1': 'IR_RX', '2': 'GND', '3': 'IR_VS'}, (210, 150),
    mpn='VS1838B or TSOP38238 (pins OUT-GND-VCC). NOT TSOP1738: different pinout')
R('R4', '100R', '+3V3', 'IR_VS', (180, 140))
CP('C2', '10uF', 'IR_VS', 'GND', (190, 160), mpn='10 uF 16 V electrolytic')

# ---------------------------------------------------------------- user I/O
R('R5', '1k', 'LED_USER', 'LED_USER_A', (180, 200))
add('D3', 'Device:LED', 'BLUE', LED5, {'2': 'LED_USER_A', '1': 'GND'}, (180, 215),
    mpn='5 mm LED, any colour', desc='User LED on IO2')
R('R6', '10k', '+3V3', 'BTN_USER', (200, 200))
add('SW1', 'Switch:SW_Push', 'USER', BTN, {'1': 'BTN_USER', '2': 'GND'}, (215, 215), mpn='6x6 mm tactile switch')
R('R7', '4.7k', '+3V3', 'SDA', (235, 200))
R('R8', '4.7k', '+3V3', 'SCL', (245, 200))
exp = ['VIN', '+3V3', 'GND', 'SDA', 'SCL', 'IO18', 'IO19', 'IO23', 'IO25', 'IO26', 'IO32', 'IO33', 'IO34', 'IO35']
add('J3', 'Connector_Generic:Conn_01x14', 'EXPANSION', HDR.format(14),
    {str(i + 1): n for i, n in enumerate(exp)}, (265, 230), mpn='14-pin male header 2.54 mm')

for i, pos in enumerate([(260, 270), (270, 270), (280, 270), (290, 270)]):
    add(f'H{i+1}', 'Mechanical:MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, pos)

# nets that need a PWR_FLAG for ERC (fed through the DevKit sockets)
pwr_flags = {'GND': (25, 200), 'VIN': (25, 210), '+3V3': (25, 220), 'IR_VS': (170, 165)}

blocks = [
    ('ESP32 DEVKIT V1 (30-pin) in two 15-pin sockets', (40, 60)),
    ('IR TRANSMIT: 2x 940 nm LED @ ~85 mA, S8050 switch', (170, 25)),
    ('IR RECEIVE: VS1838B / TSOP38238', (170, 125)),
    ('USER I/O + EXPANSION (I2C pull-ups 4.7k)', (170, 185)),
]
