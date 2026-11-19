"""Write BOMs + JLCPCB CPL from circuit.py and KiCad's position export.
Usage: python3 bom.py <pos_raw.csv> <outdir>"""
import csv, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circuit import comps
pos, out = sys.argv[1], sys.argv[2]
THT = ('LED_THT', 'Button_Switch_THT', 'Connector_PinHeader', 'OptoDevice')
groups = collections.OrderedDict()
for c in comps:
    if c['lib'].startswith('Mechanical'):
        continue                                        # v1 issue #5: mounting holes are not parts
    key = (c['value'], c['fp'], c['mpn'], c['lcsc'])
    groups.setdefault(key, []).append(c['ref'])
srt = lambda refs: sorted(refs, key=lambda r: (r.rstrip('0123456789'), int(''.join(ch for ch in r if ch.isdigit()))))
with open(os.path.join(out, 'BOM_full.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Qty', 'Designators', 'Value', 'Footprint', 'MPN / description', 'LCSC', 'Assembly'])
    for (v, fp, mpn, lc), refs in groups.items():
        w.writerow([len(refs), ','.join(srt(refs)), v, fp.split(':')[1], mpn, lc,
                    'hand (THT)' if fp.startswith(THT) else 'SMT or hand'])
with open(os.path.join(out, 'BOM_JLCPCB.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
    for (v, fp, mpn, lc), refs in groups.items():
        if fp.startswith(THT):
            continue                                    # THT parts: hand solder (cheaper than JLC THT assembly)
        w.writerow([v, ','.join(srt(refs)), fp.split(':')[1], lc])
smd = {r for (v, fp, mpn, lc), refs in groups.items() if not fp.startswith(THT) for r in refs}
with open(pos) as fi, open(os.path.join(out, 'CPL_JLCPCB.csv'), 'w', newline='') as fo:
    w = csv.writer(fo); w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
    for row in csv.DictReader(fi):
        if row['Ref'] in smd:
            w.writerow([row['Ref'], f"{float(row['PosX']):.3f}mm", f"{float(row['PosY']):.3f}mm",
                        'Top' if row['Side'] == 'top' else 'Bottom', f"{float(row['Rot']):.0f}"])
print('BOM groups', len(groups), 'SMD placements', len(smd))
