import sys,json
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);rows=[]
 for site,orig in [(0xb0520,0x19a7e),(0xb032c,0x38c84),(0xafe94,0x5c2cc)]:
  ptr=rd(s,site+2);assert ptr==orig;rows.append(dict(site=hex(site),pointer=hex(ptr)))
 assert all(rd(s,c)>=0x200000 for c in range(0x432,0x462,4))
 s.input('JOY2_UP',1);advance(s,600);s.shot('race.png');(s.out/'result.json').write_text(json.dumps(dict(readers=rows,state=snapshot(s)),indent=2)+'\n');print('Fixed metadata fallback after publication passed',flush=True)
finally:s.quit()
