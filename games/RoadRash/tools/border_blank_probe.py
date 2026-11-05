import json,os,sys
from harness_a import *
s=Session(sys.argv[1]);rows=[]
try:
 route(s)
 for t in [100,300,600]:
  if t>100:advance(s,t)
  r=dict(field=field(s),top=hex(rd(s,0x1480,2)),bottom=hex(rd(s,0x1814,2)),bplcon0=hex(rd(s,0xdff100,2)),bplcon3=hex(rd(s,0xdff106,2)))
  expected=os.environ.get('EXPECT_BLANK','1')=='1'
  assert bool(int(r['top'],16)&1)==expected,r
  assert bool(int(r['bottom'],16)&1)==expected,r
  if expected:assert int(r['bplcon3'],16)&0x20,r
  rows.append(r)
 s.shot('race.png');(s.out/'result.json').write_text(json.dumps(rows,indent=2));print(rows,flush=True)
finally:s.quit()
