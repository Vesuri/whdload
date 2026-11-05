#!/usr/bin/env python3
"""Exact instruction-region costs and cockpit visibility for the saved demo trace."""
import collections,io,json,sys
from pathlib import Path
from PIL import Image,ImageStat
import barto_mmap as barto
out=Path(sys.argv[1]);t=barto.load(out/'trace.bin');base=0xcfb1d0;slot=t.slow.index(bytes.fromhex('00cfb1d000011a4e'));slave=0xc00000+slot-0x2054
costs=collections.Counter();hits=collections.Counter();phases=[];pc_cycles=collections.Counter()
for f in t.fields:
 for pc,c,r in t.instructions(f):
  pc_cycles[pc]+=c
  if pc is None:costs['STOP_or_missing_pc']+=c
  elif pc==0x7fffffff:costs['interrupt_entry']+=c;hits['interrupt_entry']+=1
  elif slave+0x1712<=pc<slave+0x1766:
   costs['blitter_check_and_wait_routine']+=c
   if slave+0x1730<=pc<slave+0x1760:costs['blitter_poll_and_CIA_wait_body']+=c
  if pc==base+0x44:hits['game_VBL']+=1
  if pc==base+0xb4:hits['buffer_swap']+=1
 im=Image.open(io.BytesIO(f.shot)).convert('RGB')
 cockpit=ImageStat.Stat(im.crop((80,350,710,466))).mean
 phases.append(sum(cockpit)/3>10)
 if f.index in (250,500,750):(out/f'field-{f.index:04}.jpg').write_bytes(f.shot)
missing=next((i for i,v in enumerate(phases) if not v),None)
summary=json.loads((out/'metrics.json').read_text());seconds_per_field=summary['emulated_seconds']/len(t.fields)
result=dict(exact_cycles=dict(costs),percent_of_window={k:100*v/summary['elapsed_cycles'] for k,v in costs.items()},hits=dict(hits),first_field_without_cockpit=missing,seconds_until_cockpit_disappears=missing*seconds_per_field if missing is not None else None,cockpit_visible_fields=sum(phases),swaps_before_cockpit_disappears=sum(f['candidate_swaps'] for f in summary['per_field'][:missing]) if missing is not None else summary['candidate_publications'])
(out/'hardware.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
