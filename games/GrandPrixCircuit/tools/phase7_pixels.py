#!/usr/bin/env python3
"""Compare fetched bitplane words, independent of relocation or display borders."""
import sys,struct,json,collections,hashlib
from pathlib import Path
import _amigaxdev
from amigaxdev import barto

def planes(p):
 t=barto.load(p/'trace.bin');frames=[]
 for f in t.fields:
  words=collections.defaultdict(bytearray)
  for o in range(0,len(f.dma),f.dma_size):
   reg=struct.unpack_from('<H',f.dma,o)[0]
   if f.dma[o+29]==6 and 0x110<=reg<0x11a:
    v=struct.unpack_from('<I',f.dma,o+2)[0]&65535
    words[reg]+=v.to_bytes(2,'big')
  frames.append({r:bytes(w) for r,w in words.items()})
 assert all(set(w)==set(range(0x110,0x11a,2)) for w in frames)
 assert all(len(w)==8000 for f in frames for w in f.values()),[(k,len(w)) for k,w in frames[0].items()]
 return frames
pa,pb=map(Path,sys.argv[1:3]);a,b=planes(pa),planes(pb)
# Every stable field must contain the same full five-plane frame. No crop,
# colour tolerance, wheel mask, or "closest frame" selection is permitted.
def equal(frames,reference):
 return all(f==reference for f in frames)
assert equal(a+b,a[0]),'unstable or unequal fetched bitmap'
bad=dict(a[0]);plane=bytearray(bad[0x112]);plane[4000]^=1;bad[0x112]=bytes(plane)
assert not equal([bad],a[0]),'negative control escaped the exact comparator'
v=b''.join(a[0][k] for k in sorted(a[0]))
result=dict(native=pa.name,enhanced=pb.name,fields=[len(a),len(b)],bytes_per_frame=len(v),sha256=hashlib.sha256(v).hexdigest(),negative_control='one changed plane byte rejected',result='byte-identical')
print(json.dumps(result,indent=2));(pb/'zero-oracle.json').write_text(json.dumps(result,indent=2)+'\n')
