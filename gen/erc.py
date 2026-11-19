"""Netlist-level ERC: compare the schematic's exported netlist with circuit.py, flag single-pin nets."""
import re, sys, collections
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circuit import comps
txt = open(sys.argv[1]).read()
got = {}
for m in re.finditer(r'\(net \(code "?\d+"?\) \(name "([^"]*)"\)(.*?)\)\s*(?=\(net |\)\s*\)\s*$)', txt, re.S):
    name = m.group(1).lstrip('/')
    nodes = re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"', m.group(2))
    for r, p in nodes:
        got[(r, p)] = name
want = {(c['ref'], p): n for c in comps for p, n in c['pins'].items()}
errs = 0
for k, n in want.items():
    if got.get(k) != n:
        print('MISMATCH', k, 'want', n, 'got', got.get(k)); errs += 1
nets = collections.defaultdict(list)
for k, n in got.items():
    nets[n].append(k)
for n, ks in nets.items():
    if len(ks) < 2 and not n.startswith('unconnected') and not n.startswith('Net-('):
        print('SINGLE-PIN NET', n, ks); errs += 1
extra = [k for k, n in got.items() if k not in want and not n.startswith('unconnected') and not k[0].startswith('#')]
for k in extra:
    print('UNEXPECTED CONNECTION', k, got[k]); errs += 1
print(f'{len(want)} pin assignments checked, {len(set(want.values()))} nets, {errs} problems')
