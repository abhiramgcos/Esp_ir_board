"""Independent Gerber check: rebuild the netlist from KiCad X2 net attributes, render both copper layers,
join them through plated holes, and report opens/shorts. Optionally compare with gen/circuit.py.
Usage: python3 tools/gerber_connectivity.py <gerber_dir> [--circuit gen]"""
import re, sys, glob, os, collections
import numpy as np
from PIL import Image
from scipy import ndimage
from pygerber.gerberx3.api.v2 import GerberFile, ColorScheme, PixelFormatEnum

D = 40  # px per mm
d = sys.argv[1]
fcu = glob.glob(os.path.join(d, '*F_Cu.gtl'))[0]; bcu = glob.glob(os.path.join(d, '*B_Cu.gbl'))[0]
pth = glob.glob(os.path.join(d, '*PTH.drl')); pth = [p for p in pth if 'NPTH' not in p][0]

def flashes(f):
    at, out = {}, []
    for line in open(f):
        line = line.strip()
        m = re.match(r'(?:G04 #@! |%)TO\.(\w),(.*?)\*%?$', line)
        if m: at[m[1]] = m[2]; continue
        if 'TD' in line and line.startswith(('G04 #@! TD', '%TD')): at = {}; continue
        m = re.match(r'X(-?\d+)Y(-?\d+)D03\*', line)
        if m and at.get('N'):
            out.append((at['N'], at.get('P', 'via'), int(m[1]) / 1e6, int(m[2]) / 1e6))
    return out

layers, info = {}, {}
for s, f in (('F', fcu), ('B', bcu)):
    p = GerberFile.from_file(f).parse(); i = p.get_info()
    png = f'/tmp/_{s}.png'
    p.render_raster(png, dpmm=D, color_scheme=ColorScheme.COPPER_ALPHA, pixel_format=PixelFormatEnum.RGBA)
    layers[s] = (np.array(Image.open(png))[:, :, 3] > 127, float(i.min_x_mm), float(i.max_y_mm))
X0 = min(v[1] for v in layers.values()) - 1; Y0 = max(v[2] for v in layers.values()) + 1
H = max(v[0].shape[0] for v in layers.values()) + 4 * D; W = max(v[0].shape[1] for v in layers.values()) + 4 * D
lab = {}
for s, (a, mx, my) in layers.items():
    c = np.zeros((H, W), bool); ox = round((mx - X0) * D); oy = round((Y0 - my) * D)
    c[oy:oy + a.shape[0], ox:ox + a.shape[1]] = a
    lab[s] = ndimage.label(c)[0]
px = lambda x, y: (int(round((Y0 - y) * D)), int(round((x - X0) * D)))
def comp(s, x, y):
    r, c = px(x, y); v = lab[s][r, c]
    if v == 0:
        w = lab[s][r - 3:r + 4, c - 3:c + 4]; nz = w[w > 0]; v = nz[0] if len(nz) else 0
    return (s, int(v))
par = {}
def find(a):
    par.setdefault(a, a)
    while par[a] != a: par[a] = par[par[a]]; a = par[a]
    return a
for line in open(pth):
    m = re.match(r'X(-?[\d.]+)Y(-?[\d.]+)', line)
    if m:
        a, b = comp('F', float(m[1]), float(m[2])), comp('B', float(m[1]), float(m[2]))
        if a[1] and b[1]: par[find(a)] = find(b)
netcomps = collections.defaultdict(lambda: collections.defaultdict(list)); compnets = collections.defaultdict(set)
pins = {}
for s, f in (('F', fcu), ('B', bcu)):
    for n, p, x, y in flashes(f):
        c = comp(s, x, y)
        if not c[1]: continue
        r = find(c); netcomps[n][r].append(p); compnets[r].add(n)
        if p != 'via': pins[tuple(p.split(',')[:2])] = n
shorts = {r: ns for r, ns in compnets.items() if len(ns) > 1}
opens = {n: cs for n, cs in netcomps.items() if len(cs) > 1 and not n.startswith('unconnected') and n != 'N/C'}
nets = [n for n in netcomps if not n.startswith('unconnected') and n != 'N/C']
print(f'nets: {len(nets)}  shorts: {len(shorts)}  opens: {len(opens)}')
for r, ns in shorts.items(): print('  SHORT', ns)
for n, cs in opens.items(): print('  OPEN', n, [sorted(set(v))[:6] for v in cs.values()])
if '--circuit' in sys.argv:
    sys.path.insert(0, sys.argv[sys.argv.index('--circuit') + 1]); from circuit import comps
    want = {(c['ref'], p): n for c in comps for p, n in c['pins'].items()}
    bad = [(k, n, pins.get(k)) for k, n in want.items() if pins.get(k) != n]
    print(f'schematic pins checked: {len(want)}  mismatches: {len(bad)}')
    for b in bad[:20]: print('  MISMATCH', b)
