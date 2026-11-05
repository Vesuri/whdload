import json,struct,subprocess
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'tmp/prof'
def read(n,k):
 p=P/n;m=json.loads((p/'metadata.json').read_text());sz=m['snapshot_size'];b=subprocess.check_output(['zstd','-qdc',str(p/(k+'.bin.zst'))]);return m,[b[i:i+sz] for i in range(0,len(b),sz)]
def norm(b,m):
 b=bytearray(b);o=0x7ffe+0x9940-65536;p=struct.unpack_from('>I',b,o)[0];struct.pack_into('>I',b,o,p-m['layout']['data_base']);return bytes(b)
def part(b,lo,hi):return b[lo-0x8002:hi-0x8002]
r={}
for pre,k in [('s3-coupling-','physics_out'),('s3-stepinput-','physics')]:
 ma,a=read(pre+'a500',k);a=[norm(b,ma) for b in a];r[pre]={}
 for n in ['a500-slow','020','040']:
  mb,b=read(pre+n,k);b=[norm(x,mb) for x in b];rr={}
  for label,lo,hi in [('car',0x98f6,0x9952),('pose',0x98f6,0x9908),('dynamics',0x9908,0x9940),('angles',0x9944,0x9950),('clocks',0x9790,0x979c),('rng',0x903c,0x9040)]:
   diff=next((i for i,(x,y) in enumerate(zip(a,b)) if part(x,lo,hi)!=part(y,lo,hi)),None);rr[label]=dict(first_difference=diff,compared=min(len(a),len(b)))
   if diff is not None:rr[label]['bytes']=[hex(j+lo) for j,(x,y) in enumerate(zip(part(a[diff],lo,hi),part(b[diff],lo,hi))) if x!=y]
  r[pre][n]=rr
(P/'step3-comparison.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
