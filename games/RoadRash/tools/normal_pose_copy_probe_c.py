import json,os,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 assert rd(s,0x8a8aa,2)==0x4ef9
 target=rd(s,0x8a8ac)
 expected=bytes.fromhex('08a8000f000a')+read_bytes(s,0x8a8b0,128)
 actual=read_bytes(s,target,134)
 assert expected==actual,(hex(target),expected.hex(),actual.hex())
 assert actual[-4:]==bytes.fromhex('361f4e75')
 (s.out/'copy.json').write_text(json.dumps(dict(target=hex(target),size=len(actual),expected=expected.hex(),actual=actual.hex(),provenance=provenance(os.environ['SLAVE'],s)),indent=2))
 print('Verified 134-byte copy including patched prediction and native epilogue',hex(target),flush=True)
finally:s.quit()
