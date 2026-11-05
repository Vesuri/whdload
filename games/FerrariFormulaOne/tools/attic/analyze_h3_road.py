from pathlib import Path
import sys,json,bisect,collections,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());sy=r['symbols'];base=int(r['probe'],16);rows=sorted(json.loads((p/'addresses.json').read_text()),key=lambda x:x['actual']);keys=[x['actual'] for x in rows]
def canon(pc):
 if pc is None:return -1
 i=bisect.bisect_right(keys,pc)-1
 return rows[i]['old']+pc-rows[i]['actual'] if i>=0 and pc<rows[i]['actual']+rows[i]['size'] else pc
trace=barto.load(p/'detail.bin');draw=None;draws=[];prepare=None;vpos=None;trans=[];counts=collections.Counter();display=[];bad=[]
for f in trace.fields:
 reads=set();writes=set();first=[0]*3;changed=set();hazards=[];pixels=bytearray()
 for at in range(0,len(f.dma),f.dma_size):
  typ=struct.unpack_from('<h',f.dma,at+29)[0];addr=struct.unpack_from('<I',f.dma,at+12)[0];reg=struct.unpack_from('<H',f.dma,at)[0];extra=struct.unpack_from('<H',f.dma,at+31)[0]
  if typ in range(3,9) and addr!=0xffffffff:assert addr<0x200000,(f.index,typ,hex(addr))
  if typ==6:
   reads.add(addr)
   pixels+=bytes(f.dma[at:at+16])
   if addr in changed:hazards.append(addr)
   if 0x110<=reg<=0x114 and not first[(reg-0x110)//2]:first[(reg-0x110)//2]=addr
  if typ==5 and extra&7 in (3,4,6):writes.add(addr);changed.add(addr)
 display.append(dict(field=f.index,pixel_dma_sha256=hashlib.sha256(pixels).hexdigest(),planes=first,read_words=len(reads),write_words=len(writes),write_then_display_words=len(set(hazards)),same_field_words=len(reads&writes)))
 for pc,cost,regs in trace.instructions(f):
  if (regs[16]>>8)&7:continue
  n=canon(pc)
  if pc==base+sy['B8Draw']:draw={'road_regs':[],'planes':[],'clip_shift':[],'clear_dest':[]}
  if pc==base+sy['FF1RenderPrepareRoad']:prepare=f.index;vpos=None
  if pc==base+sy['B8_6572e']:vpos=regs[0]&65535
  if pc==base+sy['B8_65734'] and prepare is not None:
   trans.append(dict(prepare_field=prepare,clear_field=f.index,last_vpos=vpos,safe=f.index>prepare or (vpos is not None and vpos&1!=0)));prepare=None
  if draw is not None:
   if n==0x6b372:draw['road_regs'].append(list(regs[:15])+[regs[16]&31])
   if n==0x6b0d0:draw['clear_dest'].append(regs[0])
   if n==0x32e34:draw['planes'].append(regs[0]&65535);draw['clip_shift'].append([regs[x]&65535 for x in [3,4,5]])
   if pc==base+sy['B8Frames']-2:draws.append(draw);draw=None
assert trans and all(t['safe'] for t in trans),trans
out=dict(status='passed',draws=draws,transitions=trans,display_fields=display,dma_chip=True,display_banks=sorted(set(tuple(x['planes']) for x in display)))
(p/'road-analysis.json').write_text(json.dumps(out,indent=2)+'\n');print(p.name,len(draws),'draws',len(trans),'safe clears',len(out['display_banks']),'banks')
