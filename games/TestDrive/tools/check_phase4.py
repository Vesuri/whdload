#!/usr/bin/env python3
"""Acceptance for retained phase-4 baselines, including explicit backend limits."""
import json,hashlib,subprocess,sys
from pathlib import Path
from harness import ROOT
from td_report import barto
r=ROOT/'tmp/phase4';result={}
verify='d1b3a400a7a20bb7d78ee9745b815351fee6373f552a536b311076df6046fb07'
for preset in ('a500','a1200','a1200-030'):
 comp=json.loads((r/f'base-{preset}-comparison.json').read_text());assert comp['measurement_repeatable'],preset
 assert comp['start-state_equal'] and comp['end-state_equal']
 assert not comp['start_data_different_offsets'] and not comp['end_data_different_offsets']
 for n in (1,2):
  out=r/f'base-{preset}-{n}';m=json.loads((out/'capture.json').read_text());start=json.loads((out/'start-state.json').read_text());end=json.loads((out/'end-state.json').read_text())
  assert m['fields']==100 and m['slave_sha256']==verify and m['whd_args']=='CUSTOM3=1'
  assert hashlib.sha256((out/'slave.slave').read_bytes()).hexdigest()==verify
  assert (start['mode'],start['stage'],start['race_car'],start['rng'],start['pos'],start['speed'],start['gear'])==(1,3,0,0x1dc9,30<<16,0,0)
  assert end['vbl']-start['vbl']==100
 sw=json.loads((r/f'base-{preset}-swaps-1/swaps.json').read_text());t=barto.load(str(r/f'base-{preset}-1/trace.bin'));physics=[]
 if preset!='a1200-030':
  m=json.loads((r/f'base-{preset}-1/capture.json').read_text());counts=[]
  for f in t.fields:
   ins=list(t.instructions(f));counts.append(sum(pc==m['regions']['td']+0x7aaa for pc,c,regs in ins))
   physics.extend([f.index for pc,c,regs in ins if pc==m['regions']['h4']+0x134])
  assert counts==sw['marker_counts']
  presentation=json.loads((r/f'base-{preset}-1/presentation.json').read_text())
  assert presentation['validated_next_field_dma']==[i for i,n in enumerate(counts) if n and i<99]
 else:
  assert not any(pc not in (None,0x7fffffff) for f in t.fields for pc,c,regs in t.instructions(f))
  assert sw==json.loads((r/f'base-{preset}-swaps-2/swaps.json').read_text())
 result[preset]=dict(fresh_boots=2,fields=100,frame_count=sw['presentations'],nominal_pal_fps=sw['window_fps'],same_initial_car=0,same_initial_seed='0x1dc9',full_game_data_bytes=0x32a4,physics_call_fields=physics,repeatability_scope=comp['repeatability_scope'])
subprocess.run([sys.executable,str(ROOT/'tools/audit_rng.py'),str(r/'base-a500-1'),str(r/'verify-disabled')],check=True,stdout=subprocess.DEVNULL)
(r/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
