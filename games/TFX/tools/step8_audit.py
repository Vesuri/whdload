#!/usr/bin/env python3
"""Check live relocated operands and allocation domains; no memory writes."""
import os,sys,json,struct
from pathlib import Path
from replay_flight import ROOT,run
import map_symbols as m
out=Path(sys.argv[1]).resolve();cpu=sys.argv[2] if len(sys.argv)>2 else '040';custom4=int(os.environ.get('CUSTOM4','18'));os.chdir(ROOT)
def capture(cmd,dump,bases,hs,out):
 ns=m.load(m.GAME/'tfx.020');cmd('delete breakpoints')
 for a,h in zip(bases,hs):cmd(f"monitor tfxsync {a:x} {h['size']}")
 data=[dump(f'hunk{i}.bin',a,h['size']) for i,(a,h) in enumerate(zip(bases,hs))]
 split=cpu=='040' and not custom4&4
 chip=struct.unpack_from('>I',data[0],0x4d35c)[0]-0x3290
 assert (bases[1]>=0x40000000 and bases[2]>=0x40000000)==split
 if split:assert 0<chip<0x200000-0x22760
 rows=[]
 for group in json.loads((ROOT/'tmp/step8/relocations.json').read_text()):
  src=group['source'];target=group['target']
  targetbase=(chip+group['chip_offset']-group['start']) if split else bases[target]
  for o in group['offsets']:
   old=struct.unpack_from('>I',ns[src]['data'],o)[0];actual=struct.unpack_from('>I',data[src],o)[0];expected=targetbase+old
   rows.append(dict(source=src,offset=hex(o),target=target,expected=hex(expected),actual=hex(actual),equal=actual==expected))
 # Data pointer tables can be changed by the game; all 50 code operands must retain exact mapped targets.
 assert all(r['equal'] for r in rows if r['source']==0),[r for r in rows if r['source']==0 and not r['equal']]
 if split:
  cmd(f'monitor tfxsync {chip:x} {0x22760}')
  dump('dma-allocation.bin',chip,0x22760)
 (out/'audit.json').write_text(json.dumps(dict(split=split,bases=bases,chip_base=chip,chip_bytes=0x22760 if split else None,relocations=rows),indent=2))
 print(out.name,'allocation/50 code operand checks passed; data matches',sum(r['equal'] for r in rows if r['source']==1),flush=True)
v=dict(executable='tfx.020',custom3=3,custom4=custom4,swap=0x19fc,extra_args='--uae_fpu_no_unimplemented=true' if cpu=='040' else '')
run(cpu,out,Path(os.environ.get('TEST_SEED',str(out)+'-seed')),capture,v)
