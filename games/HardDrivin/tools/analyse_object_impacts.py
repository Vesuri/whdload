"""Verify native collision separation and pair its sounds with live operands."""
import json,re,sys
from pathlib import Path
out=Path(sys.argv[1]); text=(out/'events.log').read_text()
cols='site field step object velocity mph px py pz dx dy dz x y z type flag'.split()
rows=[dict(zip(cols,map(int,s.split()))) for s in re.findall(r'^IMPACT ([-0-9 ]+)$',text,re.M)]
pending=None;pairs=[];special=[]
gate_path=out/'gate-check.json'
gates={v['observed_step']:v['emitted'] for v in json.loads(gate_path.read_text())['visits']} if gate_path.exists() else {}
def signed16(v):return (v+32768)%65536-32768
def signed32(v):return (v+2147483648)%4294967296-2147483648
for r in rows:
 if r['site']==0xbc14:
  special.append(r);continue
 if r['site'] in (0xbc62,0xbd40):
  assert pending is None,(pending,r)
  pending=r;continue
 assert pending is not None,r
 b=pending;pending=None
 assert r['site'] in ({0xbcfe,0xbcf2} if b['site']==0xbc62 else {0xbdde,0xbdd2})
 assert (b['step'],b['object'])==(r['step'],r['object'])
 assert r['velocity']==0
 for axis,proj,drift in zip('xyz',['px','py','pz'],['dx','dy','dz']):
  d=signed16(-b[proj]);assert r[drift]==d,(b,r,drift)
  assert r[axis]==signed32(b[axis]+signed16(2*d)),(b,r,axis)
 event=7 if r['site'] in (0xbcfe,0xbdde) else 6
 assert (b['mph']<=45)==(event==7)
 # Native object sound return address is eight bytes after push-immediate.
 matches=re.findall(r'^EVENT (\d+) '+str(r['step'])+' '+str(event)+' '+str(r['site']+8)+r'$',text,re.M)
 if r['step'] in gates:
  matches=re.findall(r'^EVENT (\d+) '+str(r['step'])+' '+str(event)+r' \d+$',text,re.M)
  assert len(matches)==int(gates[r['step']]),(r,matches)
 else:assert len(matches)==1,(r,matches)
 pairs.append(dict(before=b,after=r,event=event))
assert pending is None
assert rows,'No collision coverage'
result=dict(passed=True,columns=cols,pairs=pairs,special=special,counts=dict(impulses=len(pairs),low=sum(x['event']==7 for x in pairs),high=sum(x['event']==6 for x in pairs),special=len(special)))
(out/'impact-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['counts'])
