"""Small 2-layer grid maze router for KiCad boards (no external autorouter needed).

Model: 3-plane cost grid [F.Cu, via, B.Cu] at G mm resolution. A cell is free for net N on a layer if
its distance to foreign copper >= track_width/2 + clearance. Via plane cells are free where a via fits on
both layers. scikit-image's MCP (Dijkstra in C) finds the cheapest path from the routed tree of a net to its
next pad. Nets are routed Prim-style (nearest unconnected pad first); failures trigger rip-up and reorder.

Usage: python3 router.py in.kicad_pcb out.kicad_pcb
"""
import sys, os, math, time, random
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage.graph import MCP_Geometric
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from placement import BOARD, NETCLASS_POWER

G = 0.05                     # grid mm
CLR = 0.2                    # copper clearance
EDGE = 0.45                  # copper-to-edge
VIA_D, VIA_DRILL = 0.6, 0.3
VIA_COST = 60                # in grid steps (~3 mm of track): fewer vias
W_SIG, W_PWR, W_FINE = 0.4, 0.8, 0.2     # wide tracks: easy to repair by hand
FINE = set()
W_FINE = 0.15
SPECIAL = {}
MARGIN = 0.01                # raster is already ~G conservative; DRC verifies
mm = pcbnew.FromMM; ToMM = pcbnew.ToMM
V = lambda x, y: pcbnew.VECTOR2I(mm(float(x)), mm(float(y)))

X0, Y0, X1, Y1, RC = BOARD
NX, NY = int(round((X1 - X0) / G)), int(round((Y1 - Y0) / G))
LAYERS = [pcbnew.F_Cu, pcbnew.B_Cu]
OFFS = [(0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1), (0, 1, 1), (0, 1, -1), (0, -1, 1), (0, -1, -1),
        (1, 0, 0), (-1, 0, 0)]
FOREIGN = -2  # owner id for non-net copper / keepout / outside board

def to_px(x, y):
    return ((x - X0) / G, (y - Y0) / G)

def to_mm(ix, iy):
    return (X0 + ix * G, Y0 + iy * G)


class Router:
    def __init__(self, pcb):
        self.b = pcbnew.LoadBoard(pcb)
        self.netcodes = {}
        for name, ni in self.b.GetNetInfo().NetsByName().items():
            n = str(name)
            if n:
                self.netcodes[n] = ni.GetNetCode()
        self.base = [self._blank() for _ in LAYERS]   # static copper (pads, keepout, edge)
        self.pads = {}                                  # net -> list of pad dicts
        self._draw_static()
        # cells within 1.0 mm of a USB-C signal pad: the only place the tight margin is allowed
        fz = Image.new('L', (NX, NY), 0); dz = ImageDraw.Draw(fz)
        for fp in self.b.GetFootprints():
            if fp.GetReference() == 'J1':
                for pad in fp.Pads():
                    if pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                        p = to_px(ToMM(pad.GetPosition().x), ToMM(pad.GetPosition().y)); r = 1.0 / G
                        dz.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=1)
        self.fine_zone = np.array(fz, dtype=bool)
        # via drill must keep >= 0.25 mm hole-to-hole from every drilled hole, whatever its net
        hz = Image.new('L', (NX, NY), 0); dh = ImageDraw.Draw(hz)
        for fp in self.b.GetFootprints():
            for pad in fp.Pads():
                if pad.GetDrillSize().x > 0:
                    p = to_px(ToMM(pad.GetPosition().x), ToMM(pad.GetPosition().y))
                    r = (ToMM(max(pad.GetDrillSize().x, pad.GetDrillSize().y)) / 2 + 0.25 + VIA_DRILL / 2 + 0.03) / G
                    dh.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=1)
        self.hole_ok = ~np.array(hz, dtype=bool)
        self.tracks = {}   # net -> list of (layer_idx, [(x,y)...]) polylines in mm
        self.vias = {}     # net -> list of (x,y)

    def _blank(self):
        return Image.new('I', (NX, NY), -1)

    def _draw_static(self):
        # outside board + edge clearance band
        for L in self.base:
            d = ImageDraw.Draw(L)
            ins = EDGE - CLR   # distance check later adds CLR
            d.rectangle([0, 0, NX, NY], fill=FOREIGN)
            a = to_px(X0 + ins, Y0 + ins); c = to_px(X1 - ins, Y1 - ins)
            r = (RC) / G
            d.rounded_rectangle([a[0], a[1], c[0], c[1]], radius=r, fill=-1)
        # keepout rule areas on F.Cu
        for z in self.b.Zones():
            if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
                o = z.Outline().Outline(0)
                pts = [to_px(ToMM(o.CPoint(i).x), ToMM(o.CPoint(i).y)) for i in range(o.PointCount())]
                for li, lay in enumerate(LAYERS):
                    if z.IsOnLayer(lay):
                        ImageDraw.Draw(self.base[li]).polygon(pts, fill=FOREIGN)
        # pads
        for fp in self.b.GetFootprints():
            for pad in fp.Pads():
                net = pad.GetNetname()
                code = self.netcodes.get(net, FOREIGN) if net else FOREIGN
                c = pad.GetPosition()
                bb = pad.GetBoundingBox()
                rec = dict(ref=fp.GetReference(), num=pad.GetNumber(), x=ToMM(c.x), y=ToMM(c.y), layers=[],
                           bbox=(ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom())))
                for li, lay in enumerate(LAYERS):
                    if not pad.IsOnLayer(lay):
                        continue
                    ps = pcbnew.SHAPE_POLY_SET()
                    pad.TransformShapeToPolygon(ps, lay, 0, mm(0.005))
                    for oi in range(ps.OutlineCount()):
                        o = ps.Outline(oi)
                        pts = [to_px(ToMM(o.CPoint(i).x), ToMM(o.CPoint(i).y)) for i in range(o.PointCount())]
                        if len(pts) >= 3:
                            ImageDraw.Draw(self.base[li]).polygon(pts, fill=code)
                    rec['layers'].append(li)
                # holes (plated or not) block both layers for other nets
                if pad.GetDrillSize().x > 0:
                    r = ToMM(pad.GetDrillSize().x) / 2 + 0.1   # hole clearance 0.25 > copper 0.2
                    for li in range(2):
                        p = to_px(rec['x'], rec['y'])
                        ImageDraw.Draw(self.base[li]).ellipse(
                            [p[0] - r / G, p[1] - r / G, p[0] + r / G, p[1] + r / G],
                            fill=code if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else FOREIGN)
                    if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                        rec['layers'] = [0, 1]
                if net:
                    self.pads.setdefault(net, []).append(rec)

    # ---------------------------------------------------------------- dynamic state
    def owner(self):
        imgs = [L.copy() for L in self.base]
        for net, polys in self.tracks.items():
            code = self.netcodes[net]
            w = self.width(net)
            for li, pts in polys:
                d = ImageDraw.Draw(imgs[li])
                px = [to_px(*p) for p in pts]
                d.line(px, fill=code, width=int(round(w / G)) + 2)
                rr = w / 2 / G + 1
                for p in px:
                    d.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr], fill=code)
        for net, vs in self.vias.items():
            code = self.netcodes[net]
            rr = VIA_D / 2 / G + 1
            for (x, y) in vs:
                p = to_px(x, y)
                for im in imgs:
                    ImageDraw.Draw(im).ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr], fill=code)
        return [np.array(im, dtype=np.int32) for im in imgs]

    def width(self, net):
        if net in SPECIAL:
            return SPECIAL[net]
        return W_PWR if net in NETCLASS_POWER else (W_FINE if net in FINE else W_SIG)

    def route_net(self, net, own):
        code = self.netcodes[net]
        w = self.width(net)
        dist = []
        for o in own:
            foreign = (o != -1) & (o != code)
            dist.append(ndimage.distance_transform_edt(~foreign) * G)
        # tight margin only right at the 0.5 mm-pitch USB-C pins; normal margin everywhere else
        free = [d >= w / 2 + CLR + 0.06 for d in dist]
        if net in FINE:      # VBUS (SPECIAL) keeps the normal margin: it can exit its pad straight
            free = [f | ((d >= w / 2 + CLR + 0.025) & self.fine_zone) for f, d in zip(free, dist)]
        via_ok = (dist[0] >= VIA_D / 2 + CLR + 0.06) & (dist[1] >= VIA_D / 2 + CLR + 0.06) & self.hole_ok
        pads = self.pads[net]
        # pad cells (own copper) per layer
        tree = set()
        def pad_cells(p):
            cells = []
            l, t, r_, bt = p['bbox']
            ax0, ay0 = to_px(l, t); ax1, ay1 = to_px(r_, bt)
            ax0, ay0 = int(math.ceil(ax0)), int(math.ceil(ay0)); ax1, ay1 = int(ax1), int(ay1)
            for li in p['layers']:
                sub = own[li][ay0:ay1 + 1, ax0:ax1 + 1] == code
                fr = free[li][ay0:ay1 + 1, ax0:ax1 + 1]
                ys, xs = np.nonzero(sub & fr)
                cells += [(2 * li, y + ay0, x + ax0) for y, x in zip(ys, xs)]
            return cells
        connected = [pads[0]]
        tree.update(pad_cells(pads[0]))
        todo = pads[1:]
        new_polys, new_vias = [], []
        while todo:
            # nearest pad to the connected set
            todo.sort(key=lambda p: min(math.hypot(p['x'] - q['x'], p['y'] - q['y']) for q in connected))
            tgt = todo.pop(0)
            ends = pad_cells(tgt)
            if not ends or not tree:
                return False, (new_polys, new_vias)
            # window around target + nearest part of the tree; grow on failure
            ey = int(np.mean([c[1] for c in ends])); ex = int(np.mean([c[2] for c in ends]))
            near = min(tree, key=lambda c: (c[1] - ey) ** 2 + (c[2] - ex) ** 2)
            path = None
            for marg in (4, 12, 200):
                m = int(marg / G)
                wy0, wy1 = max(0, min(ey, near[1]) - m), min(NY, max(ey, near[1]) + m + 1)
                wx0, wx1 = max(0, min(ex, near[2]) - m), min(NX, max(ex, near[2]) + m + 1)
                cost = np.full((3, wy1 - wy0, wx1 - wx0), np.inf)
                cost[0][free[0][wy0:wy1, wx0:wx1]] = 1.0
                cost[2][free[1][wy0:wy1, wx0:wx1]] = 1.0
                cost[1][via_ok[wy0:wy1, wx0:wx1]] = VIA_COST / 2
                starts = [(l, y - wy0, x - wx0) for (l, y, x) in tree if wy0 <= y < wy1 and wx0 <= x < wx1]
                endsw = [(l, y - wy0, x - wx0) for (l, y, x) in ends if wy0 <= y < wy1 and wx0 <= x < wx1]
                if not starts or not endsw:
                    continue
                mcp = MCP_Geometric(cost, offsets=OFFS)
                costs, _ = mcp.find_costs(starts, endsw, find_all_ends=False)
                best = min(endsw, key=lambda e: costs[e])
                if np.isfinite(costs[best]):
                    path = [(l, y + wy0, x + wx0) for (l, y, x) in mcp.traceback(best)]
                    break
                if wy0 == 0 and wx0 == 0 and wy1 == NY and wx1 == NX:
                    break
            if path is None:
                todo.append(tgt)
                print('   fail', net, '->', tgt['ref'], tgt['num'], flush=True)
                return False, (new_polys, new_vias)
            polys, vias = self._path_to_geom(path, free)
            new_polys += polys; new_vias += vias
            # update tree with path centreline cells + target pad cells
            # tree grows along the *smoothed* centrelines so later branches start on real copper
            for li, pts in polys:
                for p, q in zip(pts, pts[1:]):
                    a = to_px(*p); c = to_px(*q)
                    n = int(max(abs(c[0] - a[0]), abs(c[1] - a[1]))) + 1
                    for k in range(n + 1):
                        x = int(round(a[0] + (c[0] - a[0]) * k / n)); y = int(round(a[1] + (c[1] - a[1]) * k / n))
                        if abs(a[0] + (c[0] - a[0]) * k / n - x) < 0.01 and abs(a[1] + (c[1] - a[1]) * k / n - y) < 0.01:
                            tree.add((2 * li, y, x))
                    for pt in (a, c):
                        tree.add((2 * li, int(round(pt[1])), int(round(pt[0]))))
            for (vx, vy) in vias:
                ix, iy = to_px(vx, vy)
                tree.add((0, int(round(iy)), int(round(ix)))); tree.add((2, int(round(iy)), int(round(ix))))
            tree.update(ends)
            connected.append(tgt)
            # mark new copper in 'own' so later segments of this net see it (same net -> not foreign anyway)
        return True, (new_polys, new_vias)

    def _path_to_geom(self, path, free=None):
        polys, vias = [], []
        cur_layer, cur = None, []
        for (l, y, x) in path:
            if l == 1:
                vias.append(to_mm(x, y))
                if cur:
                    polys.append((cur_layer, cur)); cur = []
                cur_layer = None
                continue
            li = l // 2
            if cur_layer is not None and li != cur_layer:
                polys.append((cur_layer, cur)); cur = []
            cur_layer = li
            cur.append(to_mm(x, y))
        if cur:
            polys.append((cur_layer, cur))
        out = []
        for li, pts in polys:
            if len(pts) < 2:
                continue
            out.append((li, self._pull(pts, free[li]) if free is not None else pts))
        # dedupe consecutive vias at same spot
        vv = []
        for v in vias:
            if not vv or math.hypot(v[0] - vv[-1][0], v[1] - vv[-1][1]) > 0.01:
                vv.append(v)
        return out, vv

    @staticmethod
    def _clear(a, b, fm):
        ax, ay = to_px(*a); bx, by = to_px(*b)
        dx, dy = round(bx - ax), round(by - ay)
        if not (dx == 0 or dy == 0 or abs(dx) == abs(dy)):
            return False          # octilinear only: 0/45/90 degree segments
        n = int(max(abs(bx - ax), abs(by - ay)) * 2) + 1
        xs = np.rint(np.linspace(ax, bx, n + 1)).astype(int); ys = np.rint(np.linspace(ay, by, n + 1)).astype(int)
        return bool(fm[ys, xs].all())

    def _pull(self, pts, fm):
        """String pulling: replace runs of grid steps with the longest straight segment that stays in free space."""
        out = [pts[0]]; i = 0; n = len(pts)
        while i < n - 1:
            j = min(n - 1, i + 400)
            while j > i + 1 and not self._clear(pts[i], pts[j], fm):
                j -= 1
            out.append(pts[j]); i = j
        return out

    @staticmethod
    def _extend_to_pads(b):
        """Route ends land on the pad's raster boundary; add a short stub into the pad centre."""
        pads = [p for fp in b.GetFootprints() for p in fp.Pads()]
        tracks = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T]
        added = 0
        for t in tracks:
            for pt in (t.GetStart(), t.GetEnd()):
                same = [p for p in pads if p.GetNetCode() == t.GetNetCode() and p.IsOnLayer(t.GetLayer())]
                if any(p.HitTest(pt, 0) for p in same):
                    continue
                near = [p for p in same if p.HitTest(pt, mm(0.12))]
                if near:
                    p = min(near, key=lambda p: (p.GetPosition() - pt).EuclideanNorm())
                    n = pcbnew.PCB_TRACK(b); n.SetStart(pt); n.SetEnd(p.GetPosition()); n.SetWidth(t.GetWidth())
                    n.SetLayer(t.GetLayer()); n.SetNet(t.GetNet()); b.Add(n); added += 1
        print('pad stubs added', added, flush=True)

    @staticmethod
    def _cleanup(b):
        """Remove dangling track stubs left by tree branching (endpoint touching nothing)."""
        tol = mm(0.02)
        while True:
            tracks = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T]
            vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
            pads = [p for fp in b.GetFootprints() for p in fp.Pads()]
            removed = 0
            for t in tracks:
                for pt in (t.GetStart(), t.GetEnd()):
                    ok = False
                    for p in pads:
                        if p.GetNetCode() == t.GetNetCode() and p.IsOnLayer(t.GetLayer()) and p.HitTest(pt, 0):
                            ok = True; break
                    if not ok:
                        ok = any(v.GetNetCode() == t.GetNetCode() and (v.GetPosition() - pt).EuclideanNorm() < mm(VIA_D / 2) for v in vias)
                    if not ok:
                        for o in tracks:
                            if o is t or o.GetNetCode() != t.GetNetCode() or o.GetLayer() != t.GetLayer():
                                continue
                            a, c = o.GetStart(), o.GetEnd()
                            dx, dy = c.x - a.x, c.y - a.y; L2 = dx * dx + dy * dy
                            tt = 0 if L2 == 0 else max(0, min(1, ((pt.x - a.x) * dx + (pt.y - a.y) * dy) / L2))
                            if math.hypot(a.x + tt * dx - pt.x, a.y + tt * dy - pt.y) < tol:
                                ok = True; break
                    if not ok:
                        b.Remove(t); removed += 1; break
            # vias with no tracks and no pad
            for v in vias:
                if not any(t.GetNetCode() == v.GetNetCode() and ((t.GetStart() - v.GetPosition()).EuclideanNorm() < mm(VIA_D / 2) or (t.GetEnd() - v.GetPosition()).EuclideanNorm() < mm(VIA_D / 2)) for t in tracks if t.Type() == pcbnew.PCB_TRACE_T and t.GetParent()):
                    pass
            if not removed:
                break
            print('cleanup removed', removed, flush=True)

    def run(self, order, max_rounds=int(os.environ.get('ROUTER_ROUNDS', 40))):
        order = list(order)
        for rnd in range(max_rounds):
            self.tracks, self.vias = {}, {}
            failed = []
            t0 = time.time()
            for net in order:
                own = self.owner()
                t1 = time.time()
                ok, (polys, vias) = self.route_net(net, own)
                print(f'  {net}: {"ok" if ok else "FAIL"} {time.time() - t1:.1f}s', flush=True)
                self.tracks[net] = polys
                self.vias[net] = vias
                if not ok:
                    failed.append(net)
            print(f'round {rnd}: failed {failed} ({time.time() - t0:.0f}s)', flush=True)
            if not failed:
                return True
            # rip-up: move failures to the front; after a few rounds, also jitter the rest
            rest = [n for n in order if n not in failed]
            if rnd >= 4:
                rng = random.Random(rnd)
                for k in range(len(rest) - 1):
                    if rng.random() < 0.25:
                        rest[k], rest[k + 1] = rest[k + 1], rest[k]
            order = failed + rest
        return False

    def commit(self, out):
        b = self.b
        ni = b.GetNetInfo()
        for net, polys in self.tracks.items():
            n = ni.GetNetItem(net)
            w = self.width(net)
            vs = self.vias.get(net, [])
            for li, pts in polys:
                # insert via points lying on a segment so tracks end at every via
                pts2 = [pts[0]]
                for p, q in zip(pts, pts[1:]):
                    L = math.hypot(q[0] - p[0], q[1] - p[1])
                    ins = []
                    for v in vs:
                        if L < 1e-6: break
                        t = ((v[0] - p[0]) * (q[0] - p[0]) + (v[1] - p[1]) * (q[1] - p[1])) / L / L
                        if 0 < t < 1:
                            dx = p[0] + t * (q[0] - p[0]) - v[0]; dy = p[1] + t * (q[1] - p[1]) - v[1]
                            if math.hypot(dx, dy) < VIA_D / 2:
                                ins.append((t, v))
                    for t, v in sorted(ins):
                        pts2.append(v)
                    pts2.append(q)
                pts = pts2
                for p, q in zip(pts, pts[1:]):
                    if math.hypot(q[0] - p[0], q[1] - p[1]) < 1e-4:
                        continue
                    t = pcbnew.PCB_TRACK(b); t.SetStart(V(*p)); t.SetEnd(V(*q)); t.SetWidth(mm(w))
                    t.SetLayer(LAYERS[li]); t.SetNet(n); b.Add(t)
        for net, vs in self.vias.items():
            n = ni.GetNetItem(net)
            merged = []
            for v in vs:
                if all(math.hypot(v[0] - m[0], v[1] - m[1]) > VIA_D for m in merged):
                    merged.append(v)
            for (x, y) in merged:
                v = pcbnew.PCB_VIA(b); v.SetPosition(V(x, y)); v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DRILL))
                v.SetNet(n); b.Add(v)
        self._extend_to_pads(b)
        if os.environ.get("NOCLEAN") is None:
            self._cleanup(b)
        for z in list(b.Zones()):
            if z.GetIsRuleArea():
                b.Remove(z)   # routing aid only; the router already kept tracks out
        pcbnew.SaveBoard(out, b)


if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    r = Router(src)
    nets = [n for n in r.pads if len(r.pads[n]) > 1]
    def span(n):
        ps = r.pads[n]
        return max(p['x'] for p in ps) - min(p['x'] for p in ps) + max(p['y'] for p in ps) - min(p['y'] for p in ps)
    # power first (short, wide, direct), then signals shortest-first, GND last (pours finish it)
    order = sorted([n for n in nets if n in NETCLASS_POWER and n != 'GND'], key=span) + \
            sorted([n for n in nets if n not in NETCLASS_POWER], key=span) + ['GND']
    ok = r.run(order)
    r.commit(out)
    print('ROUTED' if ok else 'PARTIAL', out)
