import sys,json,struct
from harness_a import *
s=Session(sys.argv[1]);rows=[]
try:
 route(s);s.input('JOY2_UP',1);s.cmd('break *0xb076e')
 for i in range(160):
  s.cmd('continue',timeout=60)
  words=struct.unpack('>64I',read_bytes(s,0xa5a04,256));keys=[]
  for v in words:
   if v&65535==65535:break
   keys.append(v)
  rows.append(dict(field=field(s),keys=keys))
 (s.out/'sort.json').write_text(json.dumps(rows))
finally:s.quit()
