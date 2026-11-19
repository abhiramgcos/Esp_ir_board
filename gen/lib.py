import copy, os
from kiutils.symbol import SymbolLib
SYMDIR='/usr/share/kicad/symbols'
_cache={}
def _lib(name):
    if name not in _cache: _cache[name]=SymbolLib.from_file(f'{SYMDIR}/{name}.kicad_sym')
    return _cache[name]
def get_symbol(lib_id):
    lib,name=lib_id.split(':')
    L=_lib(lib)
    s=next(x for x in L.symbols if x.entryName==name)
    if s.extends:
        parent=copy.deepcopy(get_symbol(f'{lib}:{s.extends}'))
        # override properties
        pmap={p.key:p for p in parent.properties}
        for p in s.properties:
            if p.key in pmap:
                pmap[p.key].value=p.value
            else:
                parent.properties.append(copy.deepcopy(p))
        parent.entryName=name
        for u in parent.units:
            u.entryName=name
        parent.extends=None
        s=parent
    else:
        s=copy.deepcopy(s)
    s.libraryNickname=lib
    return s
def pins(sym):
    out=[]
    for u in sym.units:
        for p in u.pins:
            out.append(dict(num=p.number,name=p.name,x=p.position.X,y=p.position.Y,a=p.position.angle or 0,len=p.length,etype=p.electricalType,unit=u.unitId,hidden=p.hide))
    return out
