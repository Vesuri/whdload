import json,os,re,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 if os.environ.get('RR_LANE_SELECTED','1')=='0':
  assert read_bytes(s,0x8d966,10)==bytes.fromhex('1e29007153414dfaf6a4')
  (s.out/'probe.json').write_text(json.dumps(dict(native_entry_unchanged=True,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n')
  print('native scan retained',flush=True)
  sys.exit(0)
 listing=Path(os.environ['RR_LISTING']).read_text(encoding='latin1')
 def symbol(n):return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
 base=rd(s,0x87480)-symbol('step_main');target=base+symbol('aux_lane_scan');body=base+symbol('aux_lane_scan_body')
 assert rd(s,0x8d966,2)==0x4ef9 and rd(s,0x8d968)==target
 assert read_bytes(s,target,12)==bytes.fromhex('1e29007153414df90008d012')
 assert body==target+12 and read_bytes(s,body,0x72)==read_bytes(s,0x8d970,0x72)
 assert 0x200000<=target<0xa00000 or target>=0x1000000
 r=dict(target=hex(target),body_bytes_equal=0x72,mutable_table=hex(0x8d012),provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'probe.json').write_text(json.dumps(r,indent=2)+'\n');print(r,flush=True)
finally:s.quit()
