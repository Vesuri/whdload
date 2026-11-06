import json,struct,sys
from pathlib import Path
from compare_flight import TIMERS
from map_symbols import load,GAME
A,B=map(Path,sys.argv[1:3]);bases=[json.loads((p/'segments.json').read_text()) for p in (A,B)];hs=load(GAME/'tfx.020');sizes=[len(h['data']) for h in hs]
meta=json.loads((Path(__file__).resolve().parents[1]/'tmp/step9/fpu-sites.json').read_text());patches=[x['offset'] for x in meta['sites']]+[0x50f82,0x5169e,0x516b6,0x517a4,0x517f2,0x5183c]
report={}
for h in range(3):
 raw=[(p/f'end-hunk{h}.bin').read_bytes() for p in (A,B)];norm=[bytearray(x) for x in raw]
 # Normalize only pointers into the three known game hunks, scanning word alignment.
 for n,bb in zip(norm,bases):
  for o in range(0,len(n)-3,2):
   v=struct.unpack_from('>I',n,o)[0]
   for i,(b,size) in enumerate(zip(bb,sizes)):
    if b<=v<b+size:struct.pack_into('>I',n,o,0x10000000+i*0x100000+v-b);break
  if h==0:
   for o in patches:n[o:o+4]=bytes(4)
  clock=struct.unpack_from('>I',( (A if bb==bases[0] else B)/'entry-hunk0.bin').read_bytes(),0x4d884)[0]
  for o in TIMERS['fpu'].get(h,[]):struct.pack_into('>I',n,o,(struct.unpack_from('>I',n,o)[0]-clock)&0xffffffff)
 diff=[i for i,(a,b) in enumerate(zip(*norm)) if a!=b]
 ranges=[]
 for d in diff:
  if ranges and d==ranges[-1][1]:ranges[-1][1]+=1
  else:ranges.append([d,d+1])
 report[h]=dict(raw_differences=sum(a!=b for a,b in zip(*raw)),normalized_differences=len(diff),ranges=[[hex(a),hex(b)] for a,b in ranges],values=[dict(offset=hex(a),a=raw[0][a:b].hex(),b=raw[1][a:b].hex()) for a,b in ranges])
print(json.dumps(report,indent=2))
