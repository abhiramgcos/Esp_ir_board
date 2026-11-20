import pcbnew, sys, re, collections
b = pcbnew.LoadBoard(sys.argv[1])
if len(sys.argv) > 3 and sys.argv[3] == 'fill':
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.WriteDRCReport(b, sys.argv[2], getattr(pcbnew, 'EDA_UNITS_MILLIMETRES', getattr(pcbnew, 'EDA_UNITS_MM', None)), True)
t = open(sys.argv[2]).read()
c = collections.Counter(re.findall(r'^\[(\w+)\]', t, re.M))
print(dict(c))
