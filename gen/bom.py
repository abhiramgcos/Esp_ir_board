"""Write the shopping list (BOM.csv) from circuit.py. Every part is through-hole and hand-soldered, so
there is no pick-and-place file. Usage: python3 bom.py <pos_raw.csv (unused)> <outdir>"""
import csv, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circuit import comps
out = sys.argv[2]
groups = collections.OrderedDict()
for c in comps:
    if c['lib'].startswith('Mechanical'):
        continue
    groups.setdefault((c['value'], c['fp'], c['mpn']), []).append(c['ref'])
srt = lambda refs: sorted(refs, key=lambda r: (r.rstrip('0123456789'), int(''.join(ch for ch in r if ch.isdigit()))))
with open(os.path.join(out, 'BOM.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Qty', 'Designators', 'Value', 'What to buy', 'Footprint'])
    for (v, fp, mpn), refs in groups.items():
        w.writerow([len(refs), ','.join(srt(refs)), v, mpn, fp.split(':')[1]])
    w.writerow([1, '(plugs into J1/J2)', 'ESP32 DevKit V1', 'ESP32 DevKit V1, 30-pin (DOIT layout), rows 25.4 mm apart', '-'])
print('BOM lines', len(groups) + 1)
