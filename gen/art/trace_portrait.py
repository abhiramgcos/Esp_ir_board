"""Trace a black-on-white line drawing into filled polygons for the silkscreen.

Usage: python3 trace_portrait.py input.png output.json [target_mm] [min_stroke_mm]
Output: {"w": .., "h": .., "polys": [[outer, hole, hole, ...], ...]} with points in mm, origin top-left, y down.
Strokes are thickened so nothing prints thinner than min_stroke_mm at target_mm height.
"""
import sys, json
import numpy as np
import cv2

src, out = sys.argv[1], sys.argv[2]
target = float(sys.argv[3]) if len(sys.argv) > 3 else 17.0      # printed height, mm
min_stroke = float(sys.argv[4]) if len(sys.argv) > 4 else 0.15  # JLCPCB silkscreen minimum line width

img = cv2.imread(src, cv2.IMREAD_GRAYSCALE)
ink = (img < 128).astype(np.uint8)
ys, xs = np.nonzero(ink)
ink = ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1]           # crop to the drawing
ink = np.pad(ink, 8)
mm_px = target / ink.shape[0]

# thicken: grow every stroke by about half the shortfall to the minimum (typical strokes are ~0.7 x min)
grow = max(1, int(round(min_stroke * 0.25 / mm_px)))
ink = cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1)))
# drop specks too small to print
n, lab, stats, _ = cv2.connectedComponentsWithStats(ink, 8)
min_area = (min_stroke / mm_px) ** 2 * 2
min_hole = (0.10 / mm_px) ** 2          # white gaps (eye whites, highlights) as small as ~0.1 mm still print
for i in range(1, n):
    if stats[i, cv2.CC_STAT_AREA] < min_area:
        ink[lab == i] = 0

# Full tree: even depth = ink outline, odd depth = hole. Ink nested inside a hole (pupils inside eyes inside
# glasses) is just another even-depth contour, so every level of detail is kept.
contours, hier = cv2.findContours(ink, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
eps = 0.6                                                           # px; keeps curves smooth
depth = [0] * len(contours)
for i in range(len(contours)):
    d, p = 0, hier[0][i][3]
    while p != -1:
        d, p = d + 1, hier[0][p][3]
    depth[i] = d
polys = []
for i, c in enumerate(contours):
    if depth[i] % 2:                                                # holes are attached to their parent below
        continue
    outer = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
    if len(outer) < 3 or cv2.contourArea(c) < min_area:
        continue
    rings = [outer]
    j = hier[0][i][2]                                               # children of an ink contour are its holes
    while j != -1:
        h = cv2.approxPolyDP(contours[j], eps, True).reshape(-1, 2)
        if len(h) >= 3 and cv2.contourArea(contours[j]) > min_hole:
            rings.append(h)
        j = hier[0][j][0]
    polys.append([[[round(float(x) * mm_px, 4), round(float(y) * mm_px, 4)] for x, y in r] for r in rings])

json.dump({'w': round(ink.shape[1] * mm_px, 3), 'h': round(ink.shape[0] * mm_px, 3), 'polys': polys}, open(out, 'w'))
print(f'{len(polys)} polygons, {sum(len(r) for p in polys for r in p)} points, '
      f'{ink.shape[1] * mm_px:.1f} x {ink.shape[0] * mm_px:.1f} mm, stroke growth {grow} px ({grow * mm_px:.3f} mm)')
