"""Check whether either hardened branch was taken in retained cache-on CPU traces."""
import json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
from hunks import read_hunks
root=Path('tmp/prof');delta=json.loads((root/'w1-fallback-binary-diff.json').read_text());old=(root/'w1-controlled-a500-0/slave.slave').read_bytes();code=read_hunks(old)[0].data
start=old.find(code);assert start>=0 and old.find(code,start+1)==-1
branches=[d['offset']-start-3 for d in delta['changed_bytes']];assert [code[o:o+2] for o in branches]==[bytes.fromhex('6600'),bytes.fromhex('6700')]
report=[]
for machine in ('a500','020'):
 case=root/f'w1-controlled-{machine}-3';meta=json.loads((case/'entry.json').read_text());listing=(case/'slave.lst').read_text(encoding='latin1');anchor=int(re.search(r'^tape_game_anchor\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16);slave=meta['entry']['game_anchor']-anchor
 counts=[{'seen':0,'taken':0} for _ in branches]
 for window in [case/'event',*sorted(p for p in case.glob('steady-*') if p.is_dir())]:
  t=barto.load(window/'trace.bin')
  for f in t.fields:
   for pc,cycles,regs in t.instructions(f):
    for i,off in enumerate(branches):
     if pc==slave+off:
      # UAE's stored SR can have stale lazy CCR bits. The preceding AND.W
      # and TST.L unambiguously define Z from these actual data registers.
      counts[i]['seen']+=1;taken=(regs[3]&65535)!=0 if i==0 else regs[0]==0;counts[i]['taken']+=int(taken)
  del t
 report.append({'machine':machine,'branches':counts});print(report[-1],flush=True)
assert not any(x['taken'] for row in report for x in row['branches'])
(root/'w1-fallback-branch-audit.json').write_text(json.dumps({'binary_diff':delta,'traces':report,'scope':'Only observed CPU traces; cached 68030 has no instruction-level coverage.'},indent=2)+'\n')
