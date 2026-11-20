"""Generate a KiCad 7 schematic from circuit.py (net labels on every pin)."""
import math, uuid, sys
from kiutils.schematic import Schematic
from kiutils.items.schitems import (SchematicSymbol, LocalLabel, NoConnect, Text,
                                    SymbolProjectInstance, SymbolProjectPath)
from kiutils.items.common import Position, Property, Effects, Font, Justify, PageSettings, TitleBlock
from lib import get_symbol, pins
from circuit import comps, pwr_flags, blocks

PROJECT = 'esp_ir_board'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'esp_ir_board.kicad_sch'
uid = lambda: str(uuid.uuid4())


def eff(size=1.27, hide=False, just=None, bold=False):
    e = Effects(font=Font(height=size, width=size, bold=bold), hide=hide)
    if just:
        e.justify = Justify(horizontally=just)
    return e


sch = Schematic.create_new()
sch.version = 20230121
sch.generator = 'eeschema'
sch.uuid = uid()
sch.paper = PageSettings(paperSize='A3')
sch.titleBlock = TitleBlock(title='ESP32 IR Blaster / Receiver', date='2026-11-20', revision='2.1.1',
                            company='abhiramgcos',
                            comments={1: 'USB-C, CH340C auto-program, 2x IR LED @100 mA, TSOP38238',
                                      2: 'Generated from gen/circuit.py - edit there and regenerate'})

libs = {}


def lib_sym(lib_id):
    if lib_id not in libs:
        s = get_symbol(lib_id)
        if lib_id == 'Interface_USB:CH340C':
            for u in s.units:
                for p in u.pins:
                    if p.name == 'V3':
                        p.electricalType = 'power_in'  # V3 tied to VCC at 3.3 V operation
        libs[lib_id] = s
    return libs[lib_id]


def rot(x, y, r):
    t = math.radians(r)
    return (x * math.cos(t) + y * math.sin(t), -x * math.sin(t) + y * math.cos(t))


def label_at(net, x, y, outward):
    ang = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}[outward]
    just = 'left' if ang in (0, 90) else 'right'
    sch.labels.append(LocalLabel(text=net, position=Position(round(x, 2), round(y, 2), ang),
                                 effects=eff(just=just), uuid=uid()))


def place(ref, lib_id, value, pos, r, fields, pinmap, in_bom=True, on_board=True, dnp=False):
    s = lib_sym(lib_id)
    X, Y = pos
    lib, name = lib_id.split(':')
    sym = SchematicSymbol(libraryNickname=lib, entryName=name, position=Position(X, Y, r), unit=1,
                          inBom=in_bom, onBoard=on_board, dnp=dnp, uuid=uid())
    sym.properties = [
        Property(key='Reference', value=ref, id=0, position=Position(X + 3, Y - 4, 0), effects=eff(just='left')),
        Property(key='Value', value=value, id=1, position=Position(X + 3, Y + 4, 0), effects=eff(just='left')),
        Property(key='Footprint', value=fields.get('fp', ''), id=2, position=Position(X, Y, 0), effects=eff(hide=True)),
        Property(key='Datasheet', value='~', id=3, position=Position(X, Y, 0), effects=eff(hide=True)),
    ]
    i = 4
    for k in ('MPN', 'LCSC', 'Description'):
        if fields.get(k):
            sym.properties.append(Property(key=k, value=fields[k], id=i, position=Position(X, Y, 0), effects=eff(hide=True)))
            i += 1
    plist = pins(s)
    sym.pins = {p['num']: uid() for p in plist}
    sym.instances = [SymbolProjectInstance(name=PROJECT, paths=[
        SymbolProjectPath(sheetInstancePath='/' + sch.uuid, reference=ref, unit=1)])]
    sch.schematicSymbols.append(sym)
    seen = set()
    for p in plist:
        ox, oy = rot(p['x'], -p['y'], r)
        px, py = round(X + ox, 2), round(Y + oy, 2)
        if (px, py) in seen:
            continue
        seen.add((px, py))
        bx, by = rot(math.cos(math.radians(p['a'])), -math.sin(math.radians(p['a'])), r)
        outward = (-round(bx), -round(by))
        net = pinmap.get(p['num'])
        if net:
            label_at(net, px, py, outward)
        else:
            sch.noConnects.append(NoConnect(position=Position(px, py), uuid=uid()))
    return sym


for c in comps:
    holes = c['lib'].startswith('Mechanical')
    place(c['ref'], c['lib'], c['value'], c['pos'], c['rot'],
          dict(fp=c['fp'], MPN=c['mpn'], LCSC=c['lcsc'], Description=c['desc']), c['pins'],
          in_bom=not holes, dnp=c['dnp'])

for i, (net, pos) in enumerate(pwr_flags.items()):
    place(f'#FLG0{i+1}', 'power:PWR_FLAG', 'PWR_FLAG', pos, 0, {}, {'1': net}, in_bom=False, on_board=False)

for title, (x, y) in blocks:
    sch.texts.append(Text(text=title, position=Position(x, y, 0), effects=eff(2.0, just='left', bold=True), uuid=uid()))

sch.libSymbols = list(libs.values())
sch.to_file(OUT)
print('wrote', OUT, len(sch.schematicSymbols), 'symbols', len(sch.labels), 'labels')
