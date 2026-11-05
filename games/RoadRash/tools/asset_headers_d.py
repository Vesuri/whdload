import sys,json
from harness_a import *
s=Session(sys.argv[1]);rows=[]
try:
 route(s)
 for cell in range(0x432,0x462,4):
  a=rd(s,cell);raw=read_bytes(s,a,32)
  rows.append(dict(cell=hex(cell),address=hex(a),count=int.from_bytes(raw[:2],'big'),header=raw.hex()))
 (s.out/'headers.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows,flush=True)
finally:s.quit()
