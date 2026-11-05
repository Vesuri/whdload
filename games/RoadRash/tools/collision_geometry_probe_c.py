import sys,json,re,os
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 listing=Path(os.environ['RR_LISTING']).read_text(encoding='latin1')
 def symbol(name):return int(re.search(r'^'+name+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
 base=rd(s,0x87480)-symbol('step_main')
 address=base+symbol('step_collision_geometry_code')
 expected=bytearray(read_bytes(s,0x8970e,0x140)+read_bytes(s,0x8989e,0x44))
 expected[0x898ca-0x8970e-0x50:0x898cc-0x8970e-0x50]=bytes.fromhex('ff64')
 actual=read_bytes(s,address,len(expected));assert actual==expected
 assert read_bytes(s,0x8970e,6)==bytes.fromhex('41f9000a6f3c')
 assert 0x200000<=address<0xa00000 or address>=0x1000000
 result=dict(address=hex(address),bytes_equal=len(expected),native_entry_unchanged=True,provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'probe.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
finally:s.quit()
