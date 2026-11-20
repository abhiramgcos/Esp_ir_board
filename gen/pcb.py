"""Stage 1 of PCB build: create board, place footprints, assign nets, outline, design rules.
Usage: python3 pcb.py <schematic> <out.kicad_pcb>
"""
import os, sys, json, math
import pcbnew
from kiutils.schematic import Schematic
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from circuit import comps
from placement import PLACE, BOARD, HOLES, NETCLASS_POWER

SCH, OUT = sys.argv[1], sys.argv[2]
# 3D models for footprints whose stock model is missing or not the real part (used by kicad-cli pcb render)
MODEL_OVERRIDE = {}
def set_model(fp, spec):
    path, off = spec if isinstance(spec, tuple) else (spec, (0, 0, 0))
    ms = fp.Models()
    m = ms[0] if len(ms) else pcbnew.FP_3DMODEL()
    m.m_Filename = path
    m.m_Offset = pcbnew.VECTOR3D(*off)
    if not len(ms):
        ms.append(m)

FPDIR = '/usr/share/kicad/footprints'
mm = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))

sch = Schematic.from_file(SCH)
sym_uuid = {}
for s in sch.schematicSymbols:
    ref = next(p.value for p in s.properties if p.key == 'Reference')
    sym_uuid[ref] = s.uuid

board = pcbnew.NewBoard(OUT)
ds = board.GetDesignSettings()
ds.SetCopperLayerCount(2)
ds.SetBoardThickness(mm(1.6))

# nets
nets = {}
for c in comps:
    for n in c['pins'].values():
        if n not in nets:
            ni = pcbnew.NETINFO_ITEM(board, n)
            board.Add(ni)
            nets[n] = ni

# footprints
for c in comps:
    lib, name = c['fp'].split(':')
    fp = pcbnew.FootprintLoad(f'{FPDIR}/{lib}.pretty', name)
    assert fp, c['fp']
    fp.SetFPID(pcbnew.LIB_ID(lib, name))     # keep the library nickname (schematic parity)
    fp.SetReference(c['ref'])
    fp.SetValue(c['value'])
    fp.SetPath(pcbnew.KIID_PATH('/' + sym_uuid[c['ref']]))
    x, y, r, side = PLACE[c['ref']]
    board.Add(fp)
    if side == 'B':
        fp.Flip(fp.GetPosition(), False)
    fp.SetPosition(V(x, y))
    fp.SetOrientationDegrees(r)
    if c['ref'] in MODEL_OVERRIDE:
        set_model(fp, MODEL_OVERRIDE[c['ref']])
    for k, v in (('MPN', c['mpn']), ('LCSC', c['lcsc'])):
        if v:
            if hasattr(fp, 'SetProperty'):          # KiCad 7
                fp.SetProperty(k, v)
            else:                                   # KiCad 8+: hidden footprint field
                f = pcbnew.PCB_FIELD(fp, fp.GetNextFieldId(), k)
                f.SetText(v); f.SetVisible(False); f.SetLayer(pcbnew.F_Fab)
                fp.AddField(f)
    if c['lib'].startswith('Mechanical'):
        fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    for pad in fp.Pads():
        n = c['pins'].get(pad.GetNumber())
        if n:
            pad.SetNet(nets[n])
        # v1 issue #7: 0.2 mm thermal vias -> 0.3 mm (JLCPCB 2-layer minimum)
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and pad.GetDrillSize().x < mm(0.3):
            pad.SetDrillSize(V(0.3, 0.3))
            pad.SetSize(V(0.6, 0.6))

# outline with rounded corners
x0, y0, x1, y1, rc = BOARD
def seg(a, b):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(*a)); s.SetEnd(V(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); board.Add(s)
def arc(c, start, ang):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetCenter(V(*c)); s.SetStart(V(*start)); s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))
    s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); board.Add(s)
seg((x0 + rc, y0), (x1 - rc, y0)); seg((x1, y0 + rc), (x1, y1 - rc))
seg((x1 - rc, y1), (x0 + rc, y1)); seg((x0, y1 - rc), (x0, y0 + rc))
arc((x1 - rc, y0 + rc), (x1 - rc, y0), 90); arc((x1 - rc, y1 - rc), (x1, y1 - rc), 90)
arc((x0 + rc, y1 - rc), (x0 + rc, y1), 90); arc((x0 + rc, y0 + rc), (x0, y0 + rc), 90)

pcbnew.SaveBoard(OUT, board)

# Physical stackup: 1.6 mm FR-4, black solder mask, white silkscreen (used by renders and the fab notes)
STACKUP = '''		(stackup
			(layer "F.SilkS" (type "Top Silk Screen") (color "White"))
			(layer "F.Paste" (type "Top Solder Paste"))
			(layer "F.Mask" (type "Top Solder Mask") (color "Black") (thickness 0.01))
			(layer "F.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness 0.035))
			(layer "B.Mask" (type "Bottom Solder Mask") (color "Black") (thickness 0.01))
			(layer "B.Paste" (type "Bottom Solder Paste"))
			(layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
			(copper_finish "HAL lead-free")
			(dielectric_constraints no)
		)
'''
def add_stackup(path):
    t = open(path).read()
    if '(stackup' not in t:
        open(path, 'w').write(t.replace('\t(setup\n', '\t(setup\n' + STACKUP, 1))
add_stackup(OUT)

# design rules + net classes live in the project file
pro = os.path.splitext(OUT)[0] + '.kicad_pro'
pj = json.load(open(pro)) if os.path.exists(pro) else {}
bd = pj.setdefault('board', {}).setdefault('design_settings', {})
bd.setdefault('rules', {}).update({
    'min_clearance': 0.2, 'min_track_width': 0.15, 'min_via_diameter': 0.6, 'min_via_annular_width': 0.13,
    'min_through_hole_diameter': 0.3, 'min_hole_clearance': 0.25, 'min_hole_to_hole': 0.25,
    'min_copper_edge_clearance': 0.4, 'min_silk_clearance': 0.0, 'min_text_height': 0.8,
    'min_text_thickness': 0.12})
bd['track_widths'] = [0.0, 0.25, 0.4, 0.5, 0.8]
bd['via_dimensions'] = [{'diameter': 0.0, 'drill': 0.0}, {'diameter': 0.6, 'drill': 0.3}, {'diameter': 0.8, 'drill': 0.4}]
base = {'bus_width': 12, 'diff_pair_gap': 0.25, 'diff_pair_via_gap': 0.25, 'diff_pair_width': 0.2,
        'line_style': 0, 'microvia_diameter': 0.3, 'microvia_drill': 0.1, 'pcb_color': 'rgba(0, 0, 0, 0.000)',
        'schematic_color': 'rgba(0, 0, 0, 0.000)', 'wire_width': 6}
pj['net_settings'] = {
    'classes': [dict(base, name='Default', clearance=0.2, track_width=0.25, via_diameter=0.6, via_drill=0.3),
                dict(base, name='Power', clearance=0.2, track_width=0.5, via_diameter=0.8, via_drill=0.4)],
    'meta': {'version': 3},
    'net_colors': None,
    'netclass_assignments': None,
    'netclass_patterns': [{'netclass': 'Power', 'pattern': n} for n in NETCLASS_POWER],
}
pj.setdefault('meta', {'filename': os.path.basename(pro), 'version': 1})
json.dump(pj, open(pro, 'w'), indent=2)
print('placed', len(comps), 'footprints,', len(nets), 'nets ->', OUT)
