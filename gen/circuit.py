"""ESP32 IR Blaster/Receiver board v2 - single source of truth for schematic + PCB.

Each component: ref, lib_id, value, footprint, pins{pin_number: net}, fields, schematic pos (x, y, rot).
Pins not listed are marked no-connect.
"""
R805 = 'Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder'
R1206 = 'Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder'
C805 = 'Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder'
C1206 = 'Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder'
LED805 = 'LED_SMD:LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder'
SOT23 = 'Package_TO_SOT_SMD:SOT-23'
HDR = 'Connector_PinHeader_2.54mm:PinHeader_1x{:02d}_P2.54mm_Vertical'
BTN = 'Button_Switch_THT:SW_PUSH_6mm_H5mm'

# Well-known LCSC numbers (verify stock before ordering)
LCSC = {
    '10k': 'C17414', '5.1k': 'C27834', '1k': 'C17513', '100R': 'C17408', '4.7k': 'C17673',
    '100k': 'C149504', '100nF': 'C49678', '10uF': 'C15850', '1uF': 'C28323',
}

comps = []


def add(ref, lib, value, fp, pins, pos, rot=0, mpn='', lcsc=None, dnp=False, desc=''):
    if lcsc is None:
        lcsc = LCSC.get(value, '')
    comps.append(dict(ref=ref, lib=lib, value=value, fp=fp, pins=pins, pos=pos, rot=rot,
                      mpn=mpn, lcsc=lcsc, dnp=dnp, desc=desc))


def R(ref, val, a, b, pos, fp=R805, **kw):
    add(ref, 'Device:R', val, fp, {'1': a, '2': b}, pos, **kw)


def C(ref, val, a, b, pos, fp=C805, **kw):
    add(ref, 'Device:C', val, fp, {'1': a, '2': b}, pos, **kw)


# ---------------------------------------------------------------- power / USB
usb = {p: 'VBUS' for p in ('A4', 'A9', 'B4', 'B9')}
usb.update({p: 'GND' for p in ('A1', 'A12', 'B1', 'B12', 'S1')})
usb.update({'A5': 'CC1', 'B5': 'CC2', 'A6': 'USB_DP', 'B6': 'USB_DP', 'A7': 'USB_DN', 'B7': 'USB_DN'})
add('J1', 'Connector:USB_C_Receptacle_USB2.0_16P', 'USB-C',
    'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12', usb, (45, 75),
    mpn='HRO TYPE-C-31-M-12', lcsc='C165948')
R('R1', '5.1k', 'CC1', 'GND', (80, 45))
R('R2', '5.1k', 'CC2', 'GND', (92, 45))
add('U3', 'Power_Protection:USBLC6-2SC6', 'USBLC6-2SC6', 'Package_TO_SOT_SMD:SOT-23-6',
    {'1': 'USB_DP', '6': 'USB_DP', '3': 'USB_DN', '4': 'USB_DN', '2': 'GND', '5': 'VBUS'},
    (45, 135), mpn='USBLC6-2SC6', lcsc='C7519')
add('F1', 'Device:Polyfuse', '0.75A hold', 'Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder',
    {'1': 'VBUS', '2': 'VBUS_F'}, (115, 45), mpn='1206 PTC resettable fuse, 0.75 A hold, 6 V+')
add('D1', 'Device:D_Schottky', 'SS14', 'Diode_SMD:D_SMA_Handsoldering',
    {'1': 'VIN', '2': 'VBUS_F'}, (135, 45), rot=0, mpn='SS14', lcsc='C2480')
add('D2', 'Device:D_Schottky', 'SS14', 'Diode_SMD:D_SMA_Handsoldering',
    {'1': 'VIN', '2': 'EXT5V'}, (135, 65), rot=0, mpn='SS14', lcsc='C2480')
add('J2', 'Connector_Generic:Conn_01x02', 'EXT 5V', HDR.format(2),
    {'1': 'EXT5V', '2': 'GND'}, (110, 70), mpn='2.54 mm header 1x2')
C('C1', '22uF', 'VIN', 'GND', (150, 85), fp=C1206, mpn='22uF 16V X5R 1206')
C('C2', '1uF', 'VIN', 'GND', (162, 85))
add('U2', 'Regulator_Linear:AP2112K-3.3', 'AP2112K-3.3', 'Package_TO_SOT_SMD:SOT-23-5',
    {'1': 'VIN', '2': 'GND', '3': 'VIN', '5': '+3V3'}, (185, 50),
    mpn='AP2112K-3.3TRG1', lcsc='C51118')
C('C3', '10uF', '+3V3', 'GND', (210, 50))
add('D5', 'Device:LED', 'GREEN', LED805, {'2': '+3V3_LED', '1': 'GND'}, (232, 60), rot=0,
    mpn='0805 green LED', desc='Power LED')
R('R12', '1k', '+3V3', '+3V3_LED', (232, 45))

# ---------------------------------------------------------------- USB-UART + auto program
add('U4', 'Interface_USB:CH340C', 'CH340C', 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
    {'16': '+3V3', '4': '+3V3', '1': 'GND', '5': 'USB_DP', '6': 'USB_DN',
     '2': 'CH_TX', '3': 'ESP_TX', '13': 'DTR', '14': 'RTS'}, (60, 215),
    mpn='CH340C', lcsc='C84681')
C('C8', '100nF', '+3V3', 'GND', (25, 215))
R('R5', '1k', 'CH_TX', 'ESP_RX', (100, 190), desc='Lets an external UART on J3 override CH340')
add('Q1', 'Transistor_BJT:MMBT3904', 'MMBT3904', SOT23,
    {'1': 'Q1_B', '2': 'RTS', '3': 'EN'}, (130, 215), mpn='MMBT3904', lcsc='C20526')
add('Q2', 'Transistor_BJT:MMBT3904', 'MMBT3904', SOT23,
    {'1': 'Q2_B', '2': 'DTR', '3': 'IO0'}, (130, 250), mpn='MMBT3904', lcsc='C20526')
R('R6', '10k', 'DTR', 'Q1_B', (110, 215))
R('R7', '10k', 'RTS', 'Q2_B', (110, 250))

# ---------------------------------------------------------------- ESP32
esp = {'1': 'GND', '15': 'GND', '38': 'GND', '39': 'GND', '2': '+3V3', '3': 'EN',
       '25': 'IO0', '34': 'ESP_RX', '35': 'ESP_TX', '26': 'IR_TX', '27': 'IR_RX', '24': 'LED_USER',
       '16': 'BTN_USER', '33': 'SDA', '36': 'SCL', '30': 'IO18', '31': 'IO19', '37': 'IO23',
       '10': 'IO25', '11': 'IO26', '8': 'IO32', '9': 'IO33', '6': 'IO34', '7': 'IO35'}
add('U1', 'RF_Module:ESP32-WROOM-32E', 'ESP32-WROOM-32E', 'RF_Module:ESP32-WROOM-32D', esp,
    (215, 160), mpn='ESP32-WROOM-32E-N4')
C('C5', '22uF', '+3V3', 'GND', (175, 120), fp=C1206, mpn='22uF 16V X5R 1206')
C('C6', '100nF', '+3V3', 'GND', (187, 120))
R('R3', '10k', '+3V3', 'EN', (165, 160))
C('C7', '1uF', 'EN', 'GND', (165, 180))
add('SW1', 'Switch:SW_Push', 'RESET', BTN, {'1': 'EN', '2': 'GND'}, (160, 200), mpn='6x6 mm tactile THT')
R('R4', '10k', '+3V3', 'IO0', (180, 200))
add('SW2', 'Switch:SW_Push', 'BOOT', BTN, {'1': 'IO0', '2': 'GND'}, (175, 225), mpn='6x6 mm tactile THT')
add('J3', 'Connector_Generic:Conn_01x06', 'UART', HDR.format(6),
    {'1': 'GND', '2': 'ESP_TX', '3': 'ESP_RX', '4': 'EN', '5': 'IO0', '6': '+3V3'}, (175, 260),
    mpn='2.54 mm header 1x6')

# ---------------------------------------------------------------- IR transmit (2 LEDs in series)
add('Q3', 'Transistor_FET:AO3400A', 'AO3400A', SOT23,
    {'1': 'IR_G', '2': 'GND', '3': 'IR_K'}, (320, 95), mpn='AO3400A', lcsc='C20917')
R('R8', '100R', 'IR_TX', 'IR_G', (295, 95))
R('R9', '100k', 'IR_G', 'GND', (305, 110))
R('R10', '18R', 'VIN', 'IR_A', (325, 40), fp=R1206, mpn='18 ohm 1206 1%', desc='~100 mA LED current')
add('D3', 'Device:LED', 'TSAL6200', 'LED_THT:LED_D5.0mm', {'2': 'IR_A', '1': 'IR_MID'}, (325, 55),
    rot=0, mpn='Vishay TSAL6200')
add('D4', 'Device:LED', 'TSAL6200', 'LED_THT:LED_D5.0mm', {'2': 'IR_MID', '1': 'IR_K'}, (325, 72),
    rot=0, mpn='Vishay TSAL6200')
C('C10', '22uF', 'VIN', 'GND', (345, 45), fp=C1206, mpn='22uF 16V X5R 1206')

# ---------------------------------------------------------------- IR receive
add('U5', 'Interface_Optical:TSOP382xx', 'TSOP38238', 'OptoDevice:Vishay_MOLD-3Pin',
    {'1': 'IR_RX', '2': 'GND', '3': 'IR_VS'}, (320, 150), mpn='Vishay TSOP38238')
R('R11', '100R', '+3V3', 'IR_VS', (290, 140))
C('C11', '10uF', 'IR_VS', 'GND', (300, 160))

# ---------------------------------------------------------------- user I/O
R('R13', '1k', 'LED_USER', 'LED_USER_A', (285, 200))
add('D6', 'Device:LED', 'BLUE', LED805, {'2': 'LED_USER_A', '1': 'GND'}, (285, 215), rot=0,
    mpn='0805 blue LED', desc='User LED on IO2')
R('R14', '10k', '+3V3', 'BTN_USER', (305, 200))
add('SW3', 'Switch:SW_Push', 'USER', BTN, {'1': 'BTN_USER', '2': 'GND'}, (320, 215), mpn='6x6 mm tactile THT')
R('R15', '4.7k', '+3V3', 'SDA', (345, 200))
R('R16', '4.7k', '+3V3', 'SCL', (355, 200))
exp = ['VIN', '+3V3', 'GND', 'SDA', 'SCL', 'IO18', 'IO19', 'IO23', 'IO25', 'IO26', 'IO32', 'IO33', 'IO34', 'IO35']
add('J4', 'Connector_Generic:Conn_01x14', 'EXPANSION', HDR.format(14),
    {str(i + 1): n for i, n in enumerate(exp)}, (370, 240), mpn='2.54 mm header 1x14')

for i, pos in enumerate([(260, 270), (270, 270), (280, 270), (290, 270)]):
    add(f'H{i+1}', 'Mechanical:MountingHole', 'M2', 'MountingHole:MountingHole_2.2mm_M2', {}, pos)

# nets that need a PWR_FLAG for ERC (passive-driven power nets)
pwr_flags = {'GND': (25, 260), 'VIN': (150, 65), 'IR_VS': (280, 165), 'VBUS': (80, 100)}

blocks = [
    ('POWER: USB-C, ESD, fuse, diode-OR, 3.3 V LDO', (20, 25)),
    ('USB-UART + AUTO-PROGRAM', (20, 180)),
    ('ESP32-WROOM-32E', (160, 100)),
    ('IR TRANSMIT: 2x TSAL6200 @ ~100 mA', (280, 25)),
    ('IR RECEIVE: TSOP38238 38 kHz', (280, 125)),
    ('USER I/O + EXPANSION (I2C pull-ups 4.7k)', (280, 185)),
]
