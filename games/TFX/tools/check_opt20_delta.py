"""Verify retained native copy results and reject corrupted evidence."""
import json,struct,sys
from pathlib import Path
p=Path(sys.argv[1]);n=80

def check(data,results,pointers,addr):
 assert len(data)==320256
 assert len(results)==n*4 and not any(struct.unpack('>'+str(n)+'I',results))
 ptrs=struct.unpack('>'+str(n*2)+'I',pointers)
 assert all(ptrs[i*2]==addr+64096+(i%2)*64064+64000 and ptrs[i*2+1]==addr+64032 for i in range(n))
 for x,y in [(0,32),(64032,64096),(128096,128160),(192160,192224),(320224,320256)]:
  assert data[x:y]==bytes.fromhex('a55a6996')*((y-x)//4)
 # Last copy is page 1. Its full destination and shadow must equal source.
 assert data[32:64032]==data[128160:192160]==data[256224:320224]

data=(p/'outputs.bin').read_bytes();results=(p/'results.bin').read_bytes();pointers=(p/'pointers.bin').read_bytes();addr=int.from_bytes((p/'allocation.bin').read_bytes(),'big')
check(data,results,pointers,addr)
controls=[]
for which in range(4):
 values=[bytearray(data),bytearray(results),bytearray(pointers)]
 target,off=[(0,0),(1,0),(2,0),(0,128160)][which];values[target][off]^=1
 try:check(*values,addr)
 except AssertionError:controls.append(True)
 else:controls.append(False)
assert all(controls)
(p/'checker.json').write_text(json.dumps(dict(passed=True,cases=n,negative_controls=controls),indent=2));print('80 native copy cases; four corruptions rejected')
