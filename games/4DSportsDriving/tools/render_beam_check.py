#!/usr/bin/env python3
"""Join probe register observations to actual same-trace display DMA."""
import argparse,json,re,struct,collections
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args();cap=a.capture
m=json.loads((cap/'anchor.json').read_text());mem=(cap/'end-memory.bin').read_bytes();listing=(cap/'slave.lst').read_text(encoding='latin1');symbols={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',listing,re.M)}
base=m['marker']+8-symbols['tape_game'];site=base+symbols['sim_render_beam_read'];records=base+symbols['sim_render_beam_records'];count=struct.unpack_from('>I',mem,base+symbols['sim_render_beam_count']-m['memory_base'])[0]
# Descriptor+10 points to a game wrapper; its Amiga BitMap begins at+12.
# Validate stable wrapper headers and all DMA fetches, not just list identity.
initial=(cap/'memory.bin').read_bytes();bitmap_maps={}
for i in range(16):
 off=records+i*24-m['memory_base'];clock,tick,mode,beam,copper,wrapper,seq=struct.unpack_from('>IHH4I',mem,off)
 w=wrapper-m['memory_base'];assert initial[w:w+40]==mem[w:w+40]
 stride,rows,flags,depth,pad=struct.unpack_from('>HHBBH',mem,w+12)
 assert (stride,rows,depth)==(40,200,4)
 planes=struct.unpack_from('>4I',mem,w+20)
 mapping=dict(wrapper=wrapper,bytes_per_row=stride,rows=rows,planes=list(planes))
 assert copper not in bitmap_maps or bitmap_maps[copper]==mapping
 bitmap_maps[copper]=mapping
assert len(bitmap_maps)==2
plane_sets={c:{a for p in v['planes'] for a in range(p,p+8000,2)} for c,v in bitmap_maps.items()}
assert not set.intersection(*plane_sets.values())
t=barto.load(cap/'trace.bin');assert len(t.fields)==250;boundaries=barto.capture_part_starts(cap,t)
observed=[];publications=[];current=None;sequence=0
for f in t.fields:
 if f.index in boundaries:current=None
 for pc,c,r in t.instructions(f):
  sequence+=1
  if pc==site:
   assert current is None,'Nested render'
   seq=r[1];assert r[8]==records+(seq&15)*24+8
   current=dict(field=f.index,order=sequence,sequence=seq,beam=r[2],line=(r[2]>>8)&511,hpos=r[2]&255,draw_copper=r[3],mode=r[0]&65535)
   assert current['line']<=312 and current['hpos']<227
   if seq>=count-16:
    off=records+(seq&15)*24-m['memory_base'];clock,tick,mode,beam,copper,pixels,storedseq=struct.unpack_from('>IHH4I',mem,off)
    assert (seq,mode,beam,copper)==(storedseq,current['mode'],r[2],r[3])
    current['retained_record_verified']=True
   observed.append(current)
  elif pc==m['game_base']+0x35332:
   pub=dict(field=f.index,order=sequence,copper=r[8]);publications.append(pub)
   if current is not None:
    assert current['draw_copper']==r[8]
    current['publication']=pub
   current=None
lists={r['copper'] for r in publications};assert len(lists)==2
selected=[];bounds=[];bus_publications=[]
for f in t.fields:
 assert len(f.dma)//f.dma_size==227*313
 starts=[];fetch=[];fetch_addresses=set();pending=None;bus=[]
 for j,o in enumerate(range(0,len(f.dma),f.dma_size)):
  reg=struct.unpack_from('<H',f.dma,o)[0];data=struct.unpack_from('<Q',f.dma,o+2)[0];addr=struct.unpack_from('<I',f.dma,o+12)[0];typ=struct.unpack_from('<h',f.dma,o+29)[0]
  if typ==3 and addr in lists:starts.append(addr)
  if typ==6:fetch.append(j);fetch_addresses.add(addr)
  if typ==2 and addr==0xdff080:
   assert reg==0x1102;pending=(j,data)
  if typ==2 and addr==0xdff082:
   assert reg==0x1102 and pending is not None,'Split bus publication needs explicit handling'
   slot,hi=pending;bus.append(dict(copper=(hi<<16)|data,line=j//227,hpos=j%227,slot=j,high_slot=slot));pending=None
 assert len(starts)==1 and fetch
 assert fetch_addresses==plane_sets[starts[0]],(f.index,len(fetch_addresses))
 selected.append(starts[0]);bounds.append((min(fetch),max(fetch)))
 expected=[r for r in publications if r['field']==f.index]
 assert [r['copper'] for r in expected]==[r['copper'] for r in bus],(f.index,expected,bus)
 for r,b in zip(expected,bus):r['bus']=b
 bus_publications.extend(bus)
for r in observed:
 f=r['field'];r.update(selected_copper=selected[f],display_first_slot=bounds[f][0],display_last_slot=bounds[f][1],render_target_selected=r['draw_copper']==selected[f])
 r['starts_before_display_end']=r['line']*227+r['hpos']<bounds[f][1]
risk=[r for r in observed if r['render_target_selected'] and r['starts_before_display_end']]
result=dict(bitmap_maps=bitmap_maps,all_displayed_word_addresses_verified=True,fields=250,render_starts=len(observed),retained_records_verified=sum('retained_record_verified' in r for r in observed),selected_buffer_starts_before_display_end=risk,rows=observed,scope='Actual render-entry VPOSR/VHPOSR and draw descriptor, joined to same-field selected copper and bitplane DMA. Matching publication order also verified against CPU bus high/low COP1LC writes. Starting on the selected buffer before its final fetch establishes an ownership overlap, not by itself a proved mixed-pixel/tearing image. Probe perturbs instruction timing; uninstrumented capture remains separate evidence.')
(cap/'render-beam-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
