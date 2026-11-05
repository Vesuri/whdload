import sys,json,os
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 for name,lo,hi in [('motion',0x8b486,0x8b610),('acceleration',0x8e166,0x8e2d6),('gear',0x8dd66,0x8de84)]:
  (s.out/(name+'.txt')).write_text(s.cmd(f'disassemble {lo:#x},{hi:#x}'))
 bike=rd(s,0xa5d76,2)
 table=rd(s,0x9434c+4*bike)
 data=read_bytes(s,table,40)
 (s.out/'bike-table.json').write_text(json.dumps(dict(bike=bike,address=hex(table),words=list(struct.unpack('>20H',data))),indent=2))
 (s.out/'provenance.json').write_text(json.dumps(provenance(os.environ['SLAVE'],s),indent=2))
finally:s.quit()
