#!/usr/bin/env python3
"""Compare equal primitive streams and used render-table entries across W1 A/B.
Report initial-plane equality separately: whole output equality remains checked.
"""
import argparse,json,struct,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('off',type=Path);p.add_argument('on',type=Path);a=p.parse_args()
meta=[json.loads((c/'anchor.json').read_text()) for c in (a.off,a.on)]
assert meta[0]['slave_sha256']==meta[1]['slave_sha256'],'Use the same slave build'
assert meta[0]['settings']['WHD_ARGS']=='CUSTOM2=0' and meta[1]['settings']['WHD_ARGS']=='CUSTOM2=1'
assert {k:v for k,v in meta[0]['settings'].items() if k!='WHD_ARGS'}=={k:v for k,v in meta[1]['settings'].items() if k!='WHD_ARGS'}
def normalized(cap,entry):
 b=(cap/f"draw-pixels/{entry['call']:03}-input.bin").read_bytes();pos=0;colors=set()
 for _ in range(entry['primitives']):
  size=struct.unpack_from('>I',b,pos)[0];rec=b[pos+4:pos+4+size]
  # $AB82 reads the selected color's tables. Style 2 ($AE16) also reads
  # color+1 and color+2 from the first table; retaining all three is conservative.
  colors.update(range(rec[2],rec[2]+(3 if rec[4]==2 else 1)));pos+=4+size
 tables=b[pos:pos+2560];rest=b[pos+2560:];assert len(rest)==32000+19
 selected=b''.join(tables[k*512+2*c:k*512+2*c+2] for k in range(3) for c in sorted(colors))
 patterns=[tables[1536+4*c:1536+4*c+4] for c in sorted(colors)]
 # These are packed pattern bits, not pointers: e.g. $FFFFFFFF/$FFFFDDDD.
 # $2A934 stores the D3 value itself in a4-$3A38 for patterned drawing.
 return b[:pos]+selected+b''.join(patterns)+rest[:-32000],rest[-32000:]
off=json.loads((a.off/'draw-pixels/results.json').read_text());on=json.loads((a.on/'draw-pixels/results.json').read_text());pairs=[];exact=[]
left=[(x,*normalized(a.off,x)) for x in off];right=[(y,*normalized(a.on,y)) for y in on]
for x,xi,xb in left:
 for y,yi,yb in right:
  if xi==yi:
   assert x['output_sha256']==y['output_sha256'],('Pixel mismatch',x,y)
   assert x['changed_bytes']>0,'Empty draw is not useful validation'
   pairs.append([x['call'],y['call']])
   if xb==yb:exact.append([x['call'],y['call']])
assert pairs,'No matched primitive inputs'
result={'off_capture':str(a.off),'on_capture':str(a.on),'slave_sha256':meta[0]['slave_sha256'],'matching_primitive_pairs':pairs,'identical_initial_bitmap_pairs':exact,'all_output_bytes_equal':True,'compared_plane_bytes':32000,'scope':'Stationary scene: equal primitive streams, used color tables, clipping and detail produce identical four-plane output. Initial bitmaps are compared separately; this is not a full native renderer twin.'}
(a.on/'pixel-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(f'{len(pairs)} matched primitive pairs; {len(exact)} identical initial bitmaps; all 32000 output bytes equal')
