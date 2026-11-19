import re,collections,sys
pads=collections.defaultdict(dict)
for f,side in [('board-F_Cu.gtl','F'),('board-B_Cu.gbl','B')]:
    attrs={}
    for line in open(f):
        line=line.strip()
        m=re.match(r'G04 #@! TO\.(\w),(.*)\*$',line)
        if m: attrs[m.group(1)]=m.group(2); continue
        if line.startswith('G04 #@! TD'):
            attrs={}; continue
        if line.endswith('D03*') and 'P' in attrs:
            p=attrs['P'].split(',')
            pads[(p[0],p[1])][side]=attrs.get('N','?')
nets=collections.defaultdict(set)
for (r,p),d in pads.items():
    for n in d.values(): nets[n].add(f"{r}.{p}")
for n in sorted(nets):
    if n.startswith('unconnected'): continue
    print(n, ':', ' '.join(sorted(nets[n])))
print('UNCONNECTED:',' '.join(sorted(x for n in nets if n.startswith('unconnected') for x in nets[n])))
