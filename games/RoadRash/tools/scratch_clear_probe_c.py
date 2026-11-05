import json,os,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 base=rd(s,0x8b488)
 entry=base+0x8c8ae-0x8b486
 assert rd(s,entry,2)==0x4ef9
 target=rd(s,entry+2)
 assert target==entry+6
 assert rd(s,target,2)==0x42b9
 scratch=rd(s,target+2)
 assert scratch%4==0
 for call in [0x8c1b2,0x8c1de,0x8c2f8,0x8c352,0x8c610,0x8c638,0x8c6b4,0x8c724,0x8c7c4]:
  pc=base+call-0x8b486
  assert rd(s,pc,2)==0x6100
  disp=rd(s,pc+2,2);disp=disp-65536 if disp&32768 else disp
  assert pc+2+disp==target
 assert rd(s,0x89d60)==scratch+2
 assert rd(s,base+0x8ce6c-0x8b486)==scratch
 (s.out/'probe.json').write_text(json.dumps(dict(base=hex(base),entry=hex(entry),target=hex(target),scratch=hex(scratch),calls=9,provenance=provenance(os.environ['SLAVE'],s)),indent=2))
 print('Verified nine retargeted calls and aligned shared scratch',hex(scratch),flush=True)
finally:s.quit()
