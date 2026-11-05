import json,os,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 expected=bytes.fromhex('42680012b3fc000a5de0')
 actual=read_bytes(s,0x89de8,len(expected))
 assert actual==expected,actual.hex()
 result=dict(native_pose_entry=actual.hex(),provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'probe.json').write_text(json.dumps(result,indent=2)+'\n')
 print(result,flush=True)
finally:s.quit()
