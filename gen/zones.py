"""zones.py keepout|pour <pcb>
keepout: rule area so the router keeps top tracks out from under the ESP32 body.
pour:    antenna copper keep-out, GND pours on both layers, GND stitching vias, refill."""
import sys, os, math
import numpy as np
from scipy import ndimage
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import router as R
from placement import BOARD, HOLES
BX0, BY0, BX1, BY1, _ = BOARD
from placement import SOCK_X
ANT = [(SOCK_X[0] - 2.0, 99.0), (SOCK_X[1] + 2.0, 99.0), (SOCK_X[1] + 2.0, 104.0), (SOCK_X[0] - 2.0, 104.0)]
mode, PCB = sys.argv[1], sys.argv[2]
mm = pcbnew.FromMM
b = pcbnew.LoadBoard(PCB)

def zone(pts, layers):
    z = pcbnew.ZONE(b); ls = pcbnew.LSET()
    for l in layers: ls.AddLayer(l)
    z.SetLayerSet(ls)
    o = z.Outline(); o.NewOutline()
    for x, y in pts: o.Append(mm(x), mm(y))
    b.Add(z); return z

if mode == 'keepout':
    # the DevKit antenna overhangs the top edge; keep the board strip under its base free of copper
    a = zone(ANT, [pcbnew.F_Cu, pcbnew.B_Cu])
    a.SetIsRuleArea(True); a.SetDoNotAllowTracks(True); a.SetDoNotAllowVias(True)
    a.SetDoNotAllowCopperPour(True); a.SetDoNotAllowPads(False); a.SetDoNotAllowFootprints(False)
    a.SetZoneName('no-copper-under-antenna')
    pcbnew.SaveBoard(PCB, b); print('keepout done'); sys.exit()

k = zone(ANT, [pcbnew.F_Cu, pcbnew.B_Cu])
k.SetIsRuleArea(True); k.SetDoNotAllowCopperPour(True); k.SetDoNotAllowTracks(True)
k.SetDoNotAllowVias(True); k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
k.SetZoneName('antenna-keepout')

gnd = b.GetNetInfo().GetNetItem('GND')
for lay in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = zone([(BX0, BY0), (BX1, BY0), (BX1, BY1), (BX0, BY1)], [lay])
    z.SetNet(gnd); z.SetMinThickness(mm(0.25)); z.SetLocalClearance(mm(0.3))
    z.SetThermalReliefGap(mm(0.4)); z.SetThermalReliefSpokeWidth(mm(0.5))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL); z.SetZoneName('GND')

# ---- stitching vias where both layers are clear of foreign copper
r = R.Router.__new__(R.Router)
r.b = b
r.netcodes = {str(n): ni.GetNetCode() for n, ni in b.GetNetInfo().NetsByName().items() if str(n)}
r.base = [r._blank() for _ in R.LAYERS]; r.pads = {}
r._draw_static()
r.tracks, r.vias = {}, {}
for t in b.GetTracks():
    net = t.GetNetname()
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition(); r.vias.setdefault(net, []).append((pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)))
    else:
        li = 0 if t.GetLayer() == pcbnew.F_Cu else 1
        r.tracks.setdefault(net, []).append((li, [(pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y)),
                                                   (pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y))]))
R.Router.width = lambda self, net: R.W_PWR if net in R.NETCLASS_POWER else R.W_SIG
own = r.owner()
code = r.netcodes['GND']
need = 0.3 + 0.3 + 0.1   # via radius + zone clearance + margin
ok = None
base = [np.array(im, dtype=np.int32) for im in r.base]
for o, bs in zip(own, base):
    d = ndimage.distance_transform_edt(~(((o != -1) & (o != code)) | (bs != -1))) * R.G
    ok = (d >= need) if ok is None else ok & (d >= need)
placed = []
existing = [(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)) for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
def blocked(x, y):
    if SOCK_X[0] - 3 <= x <= SOCK_X[1] + 3 and y <= 150:   # under the DevKit: pour only, no via clutter
        return True
    if x >= 168 and 107 <= y <= 146:                          # expansion header labels
        return True
    if any(math.hypot(x - hx, y - hy) < 3.5 for hx, hy in HOLES):
        return True
    if any(math.hypot(x - px, y - py) < 1.5 for px, py in existing):
        return True
    return any(math.hypot(x - px, y - py) < 5.0 for px, py in placed)
for y in np.arange(BY0 + 2.0, BY1 - 1.0, 0.5):
    for x in np.arange(BX0 + 2.0, BX1 - 1.0, 0.5):
        ix, iy = R.to_px(x, y)
        if ok[int(round(iy)), int(round(ix))] and not blocked(x, y):
            v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(float(x)), mm(float(y))))
            v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3)); v.SetNet(gnd); b.Add(v); placed.append((x, y))
stitch = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and
          (pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)) in set((float(a), float(c)) for a, c in placed)]
import re, tempfile
for it in range(4):
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    rpt = tempfile.mktemp(suffix='.rpt')
    pcbnew.WriteDRCReport(b, rpt, getattr(pcbnew, 'EDA_UNITS_MILLIMETRES', getattr(pcbnew, 'EDA_UNITS_MM', None)), False)
    bad = set()
    for blk in re.findall(r'\[(?:via_dangling|unconnected_items)\][^\n]*\n(?:\s+[^\n]*\n?)+', open(rpt).read()):
        for x, y in re.findall(r'Via \[GND\][^@]*?@\(([\d.]+) mm, ([\d.]+) mm\)|@\(([\d.]+) mm, ([\d.]+) mm\): Via \[GND\]', blk) and \
                re.findall(r'@\(([\d.]+) mm, ([\d.]+) mm\): Via \[GND\]', blk):
            bad.add((round(float(x), 2), round(float(y), 2)))
    rm = [v for v in stitch if (round(pcbnew.ToMM(v.GetPosition().x), 2), round(pcbnew.ToMM(v.GetPosition().y), 2)) in bad]
    if not rm:
        break
    for v in rm:
        b.Remove(v); stitch.remove(v)
    print('removed isolated stitching vias:', len(rm))
print('stitching vias', len(stitch))
pcbnew.SaveBoard(PCB, b)
print('pour done')
