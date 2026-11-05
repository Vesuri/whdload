#!/usr/bin/env python3
"""Compare fresh-boot traces, retaining raw JPEG-edge failures explicitly."""
import argparse,hashlib,io,json,struct,collections
from pathlib import Path
from PIL import Image,ImageChops
from td_report import barto
p=argparse.ArgumentParser();p.add_argument('left',type=Path);p.add_argument('right',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
x=barto.load(str(a.left/'trace.bin'));y=barto.load(str(a.right/'trace.bin'))
assert len(x.fields)==len(y.fields)
lm=json.loads((a.left/'capture.json').read_text());rm=json.loads((a.right/'capture.json').read_text())
assert lm['slave_sha256']==rm['slave_sha256'], 'different slaves are not fresh-boot repetitions'
result={};result['fields']=len(x.fields)
result['instruction_records_available']=any(pc not in (None,0x7fffffff) for f in x.fields for pc,c,r in x.instructions(f))
flow=[];unexpected_regs=[];rbf_regs=0;unexpected_dma=[];rbf_dma=0;other_dma=collections.Counter()
for f,g in zip(x.fields,y.fields):
 left=list(x.instructions(f));right=list(y.instructions(g))
 if len(left)!=len(right):flow.append(f.index);continue
 for u,v in zip(left,right):
  if u[:2]!=v[:2]:flow.append(f.index)
  if u[2]!=v[2]:
   allowed=u[0]==lm['regions']['td']+0x2630 and v[0]==rm['regions']['td']+0x2630 and u[2][1:]==v[2][1:] and (u[2][0]^v[2][0])==0x800
   if allowed:rbf_regs+=1
   else:unexpected_regs.append(f.index)
 for j in range(0,len(f.dma),f.dma_size):
  u=f.dma[j:j+f.dma_size];v=g.dma[j:j+g.dma_size]
  if u==v:continue
  allowed=u[:2]==v[:2] and u[10:]==v[10:] and (struct.unpack_from('<I',u,12)[0]&~1)==0xdff01e and struct.unpack_from('<h',u,29)[0]==2 and (struct.unpack_from('<Q',u,2)[0]^struct.unpack_from('<Q',v,2)[0])==0x800
  if allowed:rbf_dma+=1
  else:
   unexpected_dma.append(f.index);other_dma[hex(struct.unpack_from('<I',u,12)[0])]+=1
# The exception is exact: RBF bit 11 is discarded by the sound reader's
# following AND.W #$0780. It changes neither control flow nor cycle costs.
raw=(a.left/'code.bin').read_bytes();off=lm['regions']['td']-lm['base']+0x2630
assert raw[off:off+8]==bytes.fromhex('c06e001cc07c0780')
result.update(pc_or_cost_different_fields=sorted(set(flow)),unexpected_register_different_fields=sorted(set(unexpected_regs)),masked_rbf_register_samples=rbf_regs,unexpected_dma_different_fields=sorted(set(unexpected_dma)),masked_rbf_dma_samples=rbf_dma,other_dma_addresses=dict(other_dma))
for name,fn in [('instructions',lambda t,f: t.data[f.insn_off:f.insn_end]),('dma',lambda t,f:f.dma),('raw_shot',lambda t,f:f.shot)]:
 result[name+'_different_fields']=[i for i,(f,g) in enumerate(zip(x.fields,y.fields)) if fn(x,f)!=fn(y,g)]
boxes=[];game=[];safe=[]
for i,(f,g) in enumerate(zip(x.fields,y.fields)):
 l=Image.open(io.BytesIO(f.shot)).convert('RGB');r=Image.open(io.BytesIO(g.shot)).convert('RGB');box=ImageChops.difference(l,r).getbbox()
 if box:boxes.append([i,list(box)])
 if l.crop((74,36,714,436)).tobytes()!=r.crop((74,36,714,436)).tobytes():game.append(i)
 if l.crop((0,0,750,l.height)).tobytes()!=r.crop((0,0,750,r.height)).tobytes():safe.append(i)
result.update(pixel_difference_bounds=boxes,game_display_different_fields=game,excluding_right_edge_different_fields=safe)
for name in ('start-state','end-state'):
 result[name+'_equal']=json.loads((a.left/(name+'.json')).read_text())==json.loads((a.right/(name+'.json')).read_text())
for name in ('start','end'):
 ld=a.left/('code.bin' if name=='start' else 'end/code.bin');rd=a.right/('code.bin' if name=='start' else 'end/code.bin')
 lm=json.loads((a.left/'capture.json').read_text());rm=json.loads((a.right/'capture.json').read_text());lo=lm['regions']['td-data']-lm['base'];ro=rm['regions']['td-data']-rm['base']
 lb=ld.read_bytes()[lo:lo+0x32a4];rb=rd.read_bytes()[ro:ro+0x32a4]
 result[name+'_data_different_offsets']=[i for i,(u,v) in enumerate(zip(lb,rb)) if u!=v]
result['measurement_repeatable']=not any(result[k] for k in ('pc_or_cost_different_fields','unexpected_register_different_fields','game_display_different_fields','excluding_right_edge_different_fields','start_data_different_offsets','end_data_different_offsets')) and result['start-state_equal'] and result['end-state_equal']
if result['instruction_records_available']:
 result['measurement_repeatable'] &= not result['unexpected_dma_different_fields']
 result['repeatability_scope']='PCs/costs, game data, game pixels and DMA except discarded RBF read bit'
else:
 result['repeatability_scope']='game data and game pixels only; this backend has no instruction trace or validated CPU/blitter timing'
a.out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in result.items()},indent=2))
