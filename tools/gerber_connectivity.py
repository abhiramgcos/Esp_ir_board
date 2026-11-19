import re,collections,numpy as np
from PIL import Image
from scipy import ndimage
D=40
bounds={'F':('board-F_Cu.gtl',96.95,-100.8),'B':('board-B_Cu.gbl',95.3755,-100.3755)}
X0,Y0=94.0,-99.0; W,H=int(62*D),int(41*D)
lab={};
for s,(f,mx,my) in bounds.items():
    a=np.array(Image.open(f+'.png'))[:,:,3]>127
    c=np.zeros((H,W),bool)
    ox=round((mx-X0)*D); oy=round((Y0-my)*D)
    c[oy:oy+a.shape[0],ox:ox+a.shape[1]]=a
    l,n=ndimage.label(c); lab[s]=(l,n); print(s,'islands',n)
def px(x,y): return int(round((Y0-y)*D)), int(round((x-X0)*D))
# union-find over (side,label)
par={}
def find(a):
    par.setdefault(a,a)
    while par[a]!=a: par[a]=par[par[a]]; a=par[a]
    return a
def uni(a,b): par[find(a)]=find(b)
def comp(s,x,y):
    r,c=px(x,y); v=lab[s][0][r,c]
    if v==0:
        # search small neighborhood
        w=lab[s][0][r-3:r+4,c-3:c+4]; nz=w[w>0]
        v=nz[0] if len(nz) else 0
    return (s,v)
holes=[]
for f in ['board-PTH.drl']:
    t=None
    for line in open(f):
        m=re.match(r'X(-?[\d.]+)Y(-?[\d.]+)',line)
        if m: holes.append((float(m[1]),float(m[2])))
for x,y in holes:
    a,b=comp('F',x,y),comp('B',x,y)
    if a[1] and b[1]: uni(a,b)
# flashes with nets
items=[]
for f,s in [('board-F_Cu.gtl','F'),('board-B_Cu.gbl','B')]:
    at={}
    for line in open(f):
        line=line.strip()
        m=re.match(r'G04 #@! TO\.(\w),(.*)\*$',line)
        if m: at[m[1]]=m[2];continue
        if line.startswith('G04 #@! TD'): at={};continue
        m=re.match(r'X(-?\d+)Y(-?\d+)D03\*',line)
        if m and 'N' in at and at['N']:
            x,y=int(m[1])/1e6,int(m[2])/1e6
            items.append((at['N'],at.get('P','via'),s,x,y))
netcomps=collections.defaultdict(set); compnets=collections.defaultdict(set)
for n,p,s,x,y in items:
    c=comp(s,x,y)
    if not c[1]: print('NO COPPER at',n,p,s,x,y); continue
    r=find(c); netcomps[n].add((r,p)); compnets[r].add(n)
print('--- shorts')
for r,ns in compnets.items():
    if len(ns)>1: print(r,ns)
print('--- opens')
for n,cs in netcomps.items():
    roots=collections.defaultdict(list)
    for r,p in cs: roots[r].append(p)
    if len(roots)>1 and not n.startswith('unconnected'):
        print(n); [print('   ',sorted(set(v))) for v in roots.values()]
print('nets',len([n for n in netcomps if not n.startswith('unconnected')]),'distinct roots used',len(compnets))
# sanity: deliberately probe a point between U1 pins (should be no copper / different)
print(comp('F',116.25,-101.885), comp('F',116.25,-101.25), comp('F',116.25,-102.52))
