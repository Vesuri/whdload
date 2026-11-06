import map_symbols as m,json,sys,bisect
name=sys.argv[1];hs=m.load(m.GAME/name);h=int(sys.argv[2],0);o=int(sys.argv[3],0);n=int(sys.argv[4],0) if len(sys.argv)>4 else 100
ss=sorted(hs[h]['symbols']);oo=[x[0] for x in ss];i=bisect.bisect_right(oo,o)-1
print('symbols',ss[max(0,i-2):i+10])
from amigaxdev.disasm import records
for a,raw,t in records(str(m.OUT/f'{name}-{h}.bin'),0,0,max(0,o-16),o+n,'68040'):print(f'{a:06x} {raw:22} {t}')
