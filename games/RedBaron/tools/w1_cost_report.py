"""Analyze retained instruction traces only; no emulator interaction."""
import argparse,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
import call_costs
p=argparse.ArgumentParser();p.add_argument('entry',type=Path);p.add_argument('--mask',type=int,required=True);a=p.parse_args()
meta=json.loads((a.entry/'entry.json').read_text());sim=meta['entry']['sim'];listing=(a.entry/'slave.lst').read_text(encoding='latin1')
def label(n):return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
slave=meta['entry']['game_anchor']-label('tape_game_anchor')
for window in ('event','steady'):
 dirs=[a.entry/'event'] if window=='event' else sorted(p for p in a.entry.glob('steady-*') if p.is_dir())
 paths=[d/'trace.bin' for d in dirs];stacks={'vbl':set(),'cia':set()}
 for path in paths:
  t=barto.load(path)
  for f in t.fields:
   for pc,cycles,regs in t.instructions(f):
    if pc==sim+0x2d344:stacks['vbl'].add(regs[15])
    if pc==sim+0x2ffcc:stacks['cia'].add(regs[15])
  del t
 assert all(stacks.values()),stacks
 pages={sp&~0x3fff for vals in stacks.values() for sp in vals};assert len(pages)==1,pages
 low=pages.pop();overrides={'draw':(sim+0x30408,sim+0x3045c)}
 if a.mask&1:overrides['mirror']=(sim+0x304d0,slave+label('mirror_fast_return'))
 result=call_costs.measure(paths,sim,low,low+0x4000,overrides);result['observed_callback_stacks']={k:sorted(v) for k,v in stacks.items()}
 (a.entry/f'{window}-costs.json').write_text(json.dumps(result,indent=2)+'\n');print(window,result['summary'],flush=True)
