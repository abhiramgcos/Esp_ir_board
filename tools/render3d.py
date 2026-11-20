#!/usr/bin/env python3
"""Offscreen 3D renderer for KiCad boards (README images without KiCad 9's `kicad-cli pcb render`).

    python3 tools/render3d.py <board.kicad_pcb> <outdir> [--size 1600x1100] [--mask black|green|blue]
                              [--models DIR] [--views top_iso,bottom_iso,top]

Writes <outdir>/3d_top_iso.png, 3d_bottom_iso.png and 3d_top.png (orthographic, straight down).

* Board: Edge.Cuts outline extruded 1.6 mm with real drill holes; top/bottom textures rasterised from
  pcbnew's own layer polygons (copper, mask openings, silkscreen) -> black/green/blue mask, ENIG pads.
* Parts: KiCad's VRML (.wrl) models, parsed here (KiCad StepUp VRML2 subset, 1 unit = 2.54 mm), placed
  with KiCad's model transform convention. Models are searched in $KICAD{6..9}_3DMODEL_DIR,
  /usr/share/kicad/3dmodels, then --models. Missing models fall back to simple coloured boxes.
* Rendering: pyrender offscreen (OSMesa if available, else EGL), 2x supersampled.
Needs: KiCad's pcbnew python module (system python), numpy, pillow, trimesh, shapely, mapbox_earcut,
pyrender, PyOpenGL>=3.1.7 and libOSMesa (apt: libosmesa6 / pacman: mesa) for headless use.
"""
import argparse, ctypes.util, math, os, re, time

if 'PYOPENGL_PLATFORM' not in os.environ:
    os.environ['PYOPENGL_PLATFORM'] = 'osmesa' if ctypes.util.find_library('OSMesa') else 'egl'

import numpy as np
if not hasattr(np, 'infty'):          # pyrender 0.1.45 still uses np.infty (removed in NumPy 2)
    np.infty = np.inf
from PIL import Image, ImageDraw
import trimesh
import shapely.geometry as sg
import pyrender
import pcbnew

ToMM = pcbnew.ToMM
BOARD_T = 1.6
PX = 24.0                                    # texture px per mm
VRML_UNIT = 2.54                             # KiCad VRML: 1 unit = 0.1 inch

MASKS = {  # (mask, mask over copper)
    'black': ((16, 16, 18), (34, 34, 38)),
    'green': ((18, 88, 42), (34, 122, 60)),
    'blue':  ((14, 44, 118), (30, 72, 152)),
}
GOLD, SILK, FR4 = (214, 176, 98), (236, 236, 230), (176, 160, 110)
ALIASES = {'ESP32-WROOM-32D': 'ESP32-WROOM-32', 'ESP32-WROOM-32E': 'ESP32-WROOM-32',
           'ESP32-WROOM-32UE': 'ESP32-WROOM-32U'}


# ------------------------------------------------------------------ VRML
_vrml_cache = {}

def parse_vrml(path):
    """Return list of (vertices[N,3] mm, faces[M,3], material dict) for a KiCad StepUp .wrl."""
    if path in _vrml_cache:
        return _vrml_cache[path]
    txt = open(path, errors='ignore').read()
    txt = re.sub(r'#[^\n]*', '', txt)
    mats, out = {}, []
    # split into Shape blocks (they are not nested in KiCad files)
    starts = [m.start() for m in re.finditer(r'\bShape\s*\{', txt)] + [len(txt)]
    for a, b in zip(starts, starts[1:]):
        blk = txt[a:b]
        mat = None
        md = re.search(r'material\s+DEF\s+(\S+)\s+Material\s*\{([^}]*)\}', blk)
        if md:
            mats[md.group(1)] = mat = _material(md.group(2))
        else:
            mu = re.search(r'material\s+USE\s+(\S+)', blk)
            if mu:
                mat = mats.get(mu.group(1))
            else:
                mi = re.search(r'Material\s*\{([^}]*)\}', blk)
                if mi:
                    mat = _material(mi.group(1))
        ci = re.search(r'coordIndex\s*\[([^\]]*)\]', blk)
        pt = re.search(r'point\s*\[([^\]]*)\]', blk)
        if not (ci and pt):
            continue
        pts = np.array([float(v) for v in re.split(r'[\s,]+', pt.group(1).strip()) if v], float)
        pts = pts[: len(pts) // 3 * 3].reshape(-1, 3) * VRML_UNIT
        idx = [int(v) for v in re.split(r'[\s,]+', ci.group(1).strip()) if v]
        faces, poly = [], []
        for i in idx:
            if i < 0:
                for k in range(1, len(poly) - 1):
                    faces.append((poly[0], poly[k], poly[k + 1]))
                poly = []
            else:
                poly.append(i)
        for k in range(1, len(poly) - 1):
            faces.append((poly[0], poly[k], poly[k + 1]))
        if faces:
            out.append((pts, np.array(faces, int), mat or _material('diffuseColor 0.4 0.4 0.4')))
    _vrml_cache[path] = out
    return out


def _material(body):
    def vec(name, d):
        m = re.search(name + r'\s+([-\d.eE]+)\s+([-\d.eE]+)\s+([-\d.eE]+)', body)
        return np.array([float(m.group(i)) for i in (1, 2, 3)]) if m else np.array(d, float)
    def num(name, d):
        m = re.search(name + r'\s+([-\d.eE]+)', body)
        return float(m.group(1)) if m else d
    diff = vec('diffuseColor', (0.5, 0.5, 0.5)); spec = vec('specularColor', (0.1, 0.1, 0.1))
    shin = num('shininess', 0.3); tr = num('transparency', 0.0)
    metallic = float(np.clip((spec.mean() - 0.08) * 3.2, 0, 1))
    if diff.mean() > 0.55 and spec.mean() > 0.2:
        metallic = max(metallic, 0.75)
    return dict(color=diff, metallic=metallic, roughness=float(np.clip(1.0 - shin * 0.8, 0.15, 0.95)),
                alpha=float(1.0 - tr))


# ------------------------------------------------------------------ transforms
def rot(axis, deg):
    return trimesh.transformations.rotation_matrix(math.radians(deg), axis)

def trans(x, y, z):
    m = np.eye(4); m[:3, 3] = (x, y, z); return m

def scale(sx, sy, sz):
    return np.diag([sx, sy, sz, 1.0])


def model_matrix(m3d):
    """KiCad 3D-viewer convention: T(offset) * Rz(-rz) * Ry(-ry) * Rx(-rx) * S(scale)."""
    o, r, s = m3d.m_Offset, m3d.m_Rotation, m3d.m_Scale
    return (trans(o.x, o.y, o.z) @ rot([0, 0, 1], -r.z) @ rot([0, 1, 0], -r.y) @ rot([1, 0, 0], -r.x)
            @ scale(s.x, s.y, s.z))


def footprint_matrix(fp):
    p = fp.GetPosition()
    m = trans(ToMM(p.x), -ToMM(p.y), BOARD_T if not fp.IsFlipped() else 0.0)
    m = m @ rot([0, 0, 1], fp.GetOrientationDegrees())
    if fp.IsFlipped():
        m = m @ rot([0, 1, 0], 180)
    return m


# ------------------------------------------------------------------ model lookup
def model_dirs(extra):
    dirs = []
    for v in ('KICAD9_3DMODEL_DIR', 'KICAD8_3DMODEL_DIR', 'KICAD7_3DMODEL_DIR', 'KICAD6_3DMODEL_DIR'):
        if os.environ.get(v):
            dirs.append(os.environ[v])
    dirs += ['/usr/share/kicad/3dmodels', '/usr/local/share/kicad/3dmodels']
    if extra:
        dirs.append(extra)
    return [d for d in dirs if os.path.isdir(d)]


def find_model(fname, dirs):
    rel = re.sub(r'^\$\{?KICAD\d*_3DMODEL_DIR\}?/?', '', fname)
    rel = re.sub(r'\.(step|stp|STEP)$', '.wrl', rel)
    if not rel.endswith('.wrl'):
        rel = os.path.splitext(rel)[0] + '.wrl'
    cands = [rel]
    base = os.path.splitext(os.path.basename(rel))[0]
    if base in ALIASES:
        cands.append(os.path.join(os.path.dirname(rel), ALIASES[base] + '.wrl'))
    for c in cands:
        if os.path.isabs(c) and os.path.exists(c):
            return c
        for d in dirs:
            p = os.path.join(d, c)
            if os.path.exists(p):
                return p
    return None


# ------------------------------------------------------------------ procedural fallbacks
def box_mesh(x0, y0, z0, x1, y1, z1):
    return trimesh.creation.box(extents=(x1 - x0, y1 - y0, z1 - z0),
                                transform=trans((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def usb_c_parts():
    """HRO TYPE-C-31-M-12-ish receptacle in model frame (mm, y up = board north, mouth at -y)."""
    metal = dict(color=np.array([0.80, 0.80, 0.82]), metallic=0.9, roughness=0.3, alpha=1.0)
    dark = dict(color=np.array([0.05, 0.05, 0.05]), metallic=0.0, roughness=0.8, alpha=1.0)
    shell = trimesh.Trimesh(*_round_box(8.94, 7.35, 3.16, 1.2, 0.0, 0.0, 1.58))
    mouth = _round_box(8.2, 0.12, 2.4, 1.0, 0.0, -3.70, 1.58)
    tongue = box_mesh(-3.3, -3.74, 1.45, 3.3, -3.2, 1.75)
    return [(shell.vertices, shell.faces, metal), (mouth[0], mouth[1], dark),
            (tongue.vertices, tongue.faces, dict(dark, color=np.array([0.15, 0.15, 0.16])))]


def _round_box(w, d, h, r, cx, cy, cz):
    """Box of width w (x), depth d (y), height h (z) with edges along y rounded by r (USB-C profile)."""
    r = min(r, h / 2 - 1e-3, w / 2 - 1e-3)
    rect = sg.box(-w / 2 + r, -h / 2 + r, w / 2 - r, h / 2 - r).buffer(r, resolution=8)
    m = trimesh.creation.extrude_polygon(rect, d)           # profile in x/z plane, extruded along +z
    m.apply_transform(rot([1, 0, 0], 90))                   # extrusion axis -> -y
    m.apply_translation((cx, cy + d / 2, cz))
    return m.vertices, m.faces


def fallback_parts(fp):
    name = fp.GetFPID().GetLibItemName().wx_str() if hasattr(fp.GetFPID().GetLibItemName(), 'wx_str') \
        else str(fp.GetFPID().GetLibItemName())
    if 'USB_C' in name:
        return usb_c_parts(), name
    fp.BuildCourtyardCaches()
    cy = fp.GetCourtyard(pcbnew.F_CrtYd if not fp.IsFlipped() else pcbnew.B_CrtYd)
    if cy.OutlineCount() == 0:
        return [], name
    bb = cy.BBox()
    p = fp.GetPosition(); th = math.radians(fp.GetOrientationDegrees())
    # courtyard bbox corners (board coords, y down) -> world (y up) -> footprint-local model frame
    loc = []
    for x, y in ((bb.GetLeft(), bb.GetTop()), (bb.GetRight(), bb.GetBottom()),
                 (bb.GetLeft(), bb.GetBottom()), (bb.GetRight(), bb.GetTop())):
        wx, wy = ToMM(x) - ToMM(p.x), -(ToMM(y) - ToMM(p.y))
        loc.append((wx * math.cos(th) + wy * math.sin(th), -wx * math.sin(th) + wy * math.cos(th)))
    xs = [min(v[0] for v in loc), max(v[0] for v in loc)]; ys = [min(v[1] for v in loc), max(v[1] for v in loc)]
    h = 1.0
    b = box_mesh(xs[0] + 0.4, ys[0] + 0.4, 0, xs[1] - 0.4, ys[1] - 0.4, h)
    return [(b.vertices, b.faces, dict(color=np.array([0.2, 0.2, 0.22]), metallic=0.0, roughness=0.7,
                                       alpha=1.0))], name


# ------------------------------------------------------------------ board + textures
def poly_set_to_px(ps, x0, y0, img, value=255):
    d = ImageDraw.Draw(img)
    f = lambda pt: ((ToMM(pt.x) - x0) * PX, (ToMM(pt.y) - y0) * PX)
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        d.polygon([f(o.CPoint(k)) for k in range(o.PointCount())], fill=value)
        for j in range(ps.HoleCount(i)):
            h = ps.Hole(i, j)
            d.polygon([f(h.CPoint(k)) for k in range(h.PointCount())], fill=0)


def layer_mask(board, layer, x0, y0, W, H):
    img = Image.new('L', (W, H), 0)
    ps = pcbnew.SHAPE_POLY_SET()
    board.ConvertBrdLayerToPolygonalContours(layer, ps)
    poly_set_to_px(ps, x0, y0, img)
    return np.array(img) > 127


def board_textures(board, side, x0, y0, W, H, mask_name):
    cu = layer_mask(board, pcbnew.F_Cu if side == 'F' else pcbnew.B_Cu, x0, y0, W, H)
    op = layer_mask(board, pcbnew.F_Mask if side == 'F' else pcbnew.B_Mask, x0, y0, W, H)
    sk = layer_mask(board, pcbnew.F_SilkS if side == 'F' else pcbnew.B_SilkS, x0, y0, W, H)
    mbase, mcu = MASKS[mask_name]
    rgb = np.zeros((H, W, 3), np.float32); rgb[:] = mbase
    rgb[cu] = mcu
    rgb[op & cu] = GOLD
    rgb[op & ~cu] = FR4
    rgb[sk & ~op] = SILK
    # subtle mask sheen / noise so it does not look like flat paint
    rng = np.random.default_rng(1)
    rgb += rng.normal(0, 2.0, rgb.shape[:2])[..., None]
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    # metallic-roughness texture: G = roughness, B = metallic
    mr = np.zeros((H, W, 3), np.uint8)
    mr[..., 1] = 185; mr[..., 2] = 0                    # mask: matte dielectric
    mr[sk & ~op, 1] = 200
    mr[op & cu, 1] = 80; mr[op & cu, 2] = 255           # ENIG
    return Image.fromarray(rgb), Image.fromarray(mr)


def board_polygon(board):
    ps = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(ps)
    o = ps.Outline(0)
    shell = [(ToMM(o.CPoint(i).x), -ToMM(o.CPoint(i).y)) for i in range(o.PointCount())]
    holes = []
    def circ(x, y, r):
        n = max(10, int(r * 40))
        return [(x + r * math.cos(2 * math.pi * k / n), -y + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            ds = pad.GetDrillSize()
            if ds.x > 0:
                c = pad.GetPosition()
                if ds.x == ds.y:
                    holes.append(circ(ToMM(c.x), ToMM(c.y), ToMM(ds.x) / 2))
                else:  # oval slot -> approximate with its bounding stadium
                    r = ToMM(min(ds.x, ds.y)) / 2; L = ToMM(max(ds.x, ds.y)) / 2 - r
                    a = math.radians(pad.GetOrientationDegrees()) + (0 if ds.x > ds.y else math.pi / 2)
                    line = sg.LineString([(ToMM(c.x) - L * math.cos(a), -ToMM(c.y) - L * math.sin(a)),
                                          (ToMM(c.x) + L * math.cos(a), -ToMM(c.y) + L * math.sin(a))])
                    holes.append(list(line.buffer(r, resolution=6).exterior.coords)[:-1])
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            c = t.GetPosition(); holes.append(circ(ToMM(c.x), ToMM(c.y), ToMM(t.GetDrillValue()) / 2))
    poly = sg.Polygon(shell)
    hp = [sg.Polygon(h) for h in holes]
    hp = [h for h in hp if h.is_valid and poly.contains(h)]
    from shapely.ops import unary_union
    return poly.difference(unary_union(hp)) if hp else poly


def board_meshes(board, mask_name):
    bb = board.GetBoardEdgesBoundingBox()
    x0, y0 = ToMM(bb.GetLeft()), ToMM(bb.GetTop())
    W, H = int(ToMM(bb.GetWidth()) * PX) + 2, int(ToMM(bb.GetHeight()) * PX) + 2
    poly = board_polygon(board)
    if poly.geom_type == 'MultiPolygon':
        poly = max(poly.geoms, key=lambda g: g.area)
    body = trimesh.creation.extrude_polygon(poly, BOARD_T - 0.02)
    body.apply_translation((0, 0, 0.01))
    mbase, _ = MASKS[mask_name]
    edge_col = np.array([120, 112, 80]) / 255.0           # FR4 edge
    meshes = [(body, pyrender.MetallicRoughnessMaterial(baseColorFactor=[*edge_col, 1.0],
                                                         metallicFactor=0.0, roughnessFactor=0.85))]
    v2, f2 = trimesh.creation.triangulate_polygon(poly, engine='earcut')
    for side, z in (('F', BOARD_T), ('B', 0.0)):
        col, mr = board_textures(board, side, x0, y0, W, H, mask_name)
        verts = np.column_stack([v2, np.full(len(v2), z)])
        u = (v2[:, 0] - x0) * PX / W
        v = (-v2[:, 1] - y0) * PX / H                       # board y = -world y
        faces = f2 if side == 'F' else f2[:, ::-1]
        uv = np.column_stack([u, 1 - v])
        tm = trimesh.Trimesh(verts, faces, process=False)
        tm.visual = trimesh.visual.TextureVisuals(uv=uv)
        mat = pyrender.MetallicRoughnessMaterial(
            baseColorTexture=pyrender.Texture(source=np.array(col), source_channels='RGB'),
            metallicRoughnessTexture=pyrender.Texture(source=np.array(mr), source_channels='RGB'),
            metallicFactor=1.0, roughnessFactor=1.0)
        meshes.append((tm, mat))
    return meshes


# ------------------------------------------------------------------ scene
def part_meshes(board, extra_dir, verbose=True):
    dirs = model_dirs(extra_dir)
    groups = []      # (trimesh, material dict)
    fallbacks, used = [], 0
    for fp in board.GetFootprints():
        F = footprint_matrix(fp)
        parts, any_model = [], False
        for m3d in fp.Models():
            if not m3d.m_Show:
                continue
            path = find_model(m3d.m_Filename, dirs)
            if not path:
                continue
            any_model = True
            M = F @ model_matrix(m3d)
            ir = 'TSAL' in fp.GetValue() or 'IR' in fp.GetValue().upper()
            for v, f, mat in parse_vrml(path):
                if ir and mat['alpha'] < 0.99 or (ir and mat['color'][0] > 0.6 and mat['color'][1] < 0.45):
                    mat = dict(mat, color=np.array([0.30, 0.34, 0.50]), alpha=0.82, roughness=0.15)
                parts.append((v, f, mat, M))
        if not any_model and len(fp.Models()) == 0 and 'USB_C' not in str(fp.GetFPID().GetLibItemName()):
            continue                                   # e.g. mounting holes: nothing to draw
        if not any_model:
            fb, name = fallback_parts(fp)
            if fb:
                fallbacks.append(f'{fp.GetReference()} ({name})')
            for v, f, mat in fb:
                parts.append((v, f, mat, F))
        else:
            used += 1
        # merge per material within the footprint
        bymat = {}
        for v, f, mat, M in parts:
            key = (tuple(np.round(mat['color'], 3)), round(mat['metallic'], 2), round(mat['roughness'], 2),
                   round(mat['alpha'], 2))
            vv = trimesh.transform_points(np.asarray(v, float), M)
            bymat.setdefault(key, [mat, []])[1].append((vv, np.asarray(f)))
        for key, (mat, lst) in bymat.items():
            off, V, Fc = 0, [], []
            for vv, ff in lst:
                V.append(vv); Fc.append(ff + off); off += len(vv)
            groups.append((trimesh.Trimesh(np.vstack(V), np.vstack(Fc), process=False), mat))
    if verbose:
        print(f'  models: {used} footprints with VRML models; fallbacks: {", ".join(fallbacks) or "none"}')
    return groups, fallbacks


def look_at(eye, target, up=(0, 0, 1)):
    eye, target, up = map(lambda a: np.asarray(a, float), (eye, target, up))
    z = eye - target; z /= np.linalg.norm(z)
    x = np.cross(up, z)
    if np.linalg.norm(x) < 1e-6:
        x = np.cross((0, 1, 0), z)
    x /= np.linalg.norm(x); y = np.cross(z, x)
    m = np.eye(4); m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, z, eye
    return m


def build_scene(board_ms, parts, bg):
    sc = pyrender.Scene(bg_color=[*bg, 1.0], ambient_light=[0.22, 0.22, 0.24])
    for tm, mat in board_ms:
        sc.add(pyrender.Mesh.from_trimesh(tm, material=mat, smooth=False))
    for tm, m in parts:
        mat = pyrender.MetallicRoughnessMaterial(
            baseColorFactor=[*np.clip(m['color'] * 1.08, 0, 1), m['alpha']], metallicFactor=m['metallic'],
            roughnessFactor=m['roughness'], doubleSided=True,
            alphaMode='BLEND' if m['alpha'] < 0.99 else 'OPAQUE')
        sc.add(pyrender.Mesh.from_trimesh(tm, material=mat, smooth=False))
    return sc


def add_lights(sc, target, span, view):
    t = np.asarray(target, float)
    up = 1 if view != 'bottom_iso' else -1
    lights = [((-0.6, -0.9, 1.3 * up), 3.0), ((0.9, -0.3, 0.7 * up), 1.3), ((0.2, 1.0, 0.8 * up), 1.8)]
    if view != 'top':                       # a straight-down light glares in the orthographic top view
        lights.append(((0.0, 0.0, 1.0 * up), 0.9))
    for d, inten in lights:
        eye = t + np.asarray(d) * span
        sc.add(pyrender.DirectionalLight(color=[1.0, 0.98, 0.95], intensity=inten), pose=look_at(eye, t))


def render_view(sc_parts, view, size, bounds, out):
    board_ms, parts, bg = sc_parts
    sc = build_scene(board_ms, parts, bg)
    lo, hi = bounds
    c = (lo + hi) / 2; c[2] = BOARD_T / 2
    span = float(np.linalg.norm(hi[:2] - lo[:2]))
    W, H = size
    aspect = W / H
    if view == 'top':
        ext = hi - lo
        mag_y = max(ext[1], ext[0] / aspect) / 2 * 1.06
        cam = pyrender.OrthographicCamera(xmag=mag_y * aspect, ymag=mag_y, znear=0.1, zfar=1000)
        pose = look_at(c + np.array([0, 0, 300.0]), c, up=(0, 1, 0))
    else:
        yfov = math.radians(24)
        d = (-0.42, -1.0, 0.95) if view == 'top_iso' else (0.42, -1.0, -0.95)
        d = np.asarray(d) / np.linalg.norm(d)
        corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
        def fits(dist, margin=0.92):
            P = look_at(c + d * dist, c, up=(0, 0, 1) if view == 'top_iso' else (0, 0, -1)); inv = np.linalg.inv(P)
            q = (inv[:3, :3] @ corners.T).T + inv[:3, 3]
            ty = math.tan(yfov / 2); tx = ty * aspect
            return np.all(np.abs(q[:, 0] / -q[:, 2]) <= tx * margin) and np.all(np.abs(q[:, 1] / -q[:, 2]) <= ty * margin)
        lo_d, hi_d = span * 0.3, span * 10
        for _ in range(40):
            mid = (lo_d + hi_d) / 2
            lo_d, hi_d = (lo_d, mid) if fits(mid) else (mid, hi_d)
        dist = hi_d
        # re-centre on the projected bbox so the board sits in the middle of the frame
        cam = pyrender.PerspectiveCamera(yfov=yfov, aspectRatio=aspect, znear=1.0, zfar=dist * 4)
        # bottom view = board flipped over like turning a page (rotate 180 deg about the board's y axis)
        pose = look_at(c + d * dist, c, up=(0, 0, 1) if view == 'top_iso' else (0, 0, -1))
    sc.add(cam, pose=pose)
    add_lights(sc, c, span, view)
    ss = 2
    r = pyrender.OffscreenRenderer(W * ss, H * ss)
    col, _ = r.render(sc, flags=pyrender.RenderFlags.RGBA | pyrender.RenderFlags.SHADOWS_DIRECTIONAL)
    r.delete()
    img = Image.fromarray(col).convert('RGB').resize((W, H), Image.LANCZOS)
    img.save(out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('board'); ap.add_argument('outdir')
    ap.add_argument('--size', default='1600x1100')
    ap.add_argument('--mask', default='black', choices=sorted(MASKS))
    ap.add_argument('--models', default=None, help='extra 3D model root (…/3dmodels)')
    ap.add_argument('--views', default='top_iso,bottom_iso,top')
    ap.add_argument('--bg', default='0.965,0.965,0.97')
    a = ap.parse_args()
    W, H = map(int, a.size.lower().split('x'))
    os.makedirs(a.outdir, exist_ok=True)
    t0 = time.time()
    board = pcbnew.LoadBoard(a.board)
    print(f'render3d: {a.board}  (GL: {os.environ["PYOPENGL_PLATFORM"]})')
    board_ms = board_meshes(board, a.mask)
    parts, _ = part_meshes(board, a.models)
    allv = np.vstack([board_ms[0][0].vertices] + [tm.vertices for tm, _ in parts])
    bounds = (allv.min(0), allv.max(0))
    bg = tuple(float(v) for v in a.bg.split(','))
    for view in a.views.split(','):
        out = os.path.join(a.outdir, f'3d_{view}.png')
        render_view((board_ms, parts, bg), view, (W, H), bounds, out)
        print('  wrote', out)
    print(f'  done in {time.time() - t0:.1f}s')


if __name__ == '__main__':
    main()
