"""Accept the A500 gameplay windows only with matching fresh boots and native outcomes."""
import sys,json,struct,hashlib
from pathlib import Path
first,second=map(Path,sys.argv[1:3]);one=json.loads((first/'state-summary.json').read_text());two=json.loads((second/'state-summary.json').read_text())
assert one['summary']['repeat_mismatches']=={'state':[],'front':[],'tape':[]}
assert one['events']==two['events'],'event timing differs'
assert one['per_field']==two['per_field'],'decoded states differ'
rows=one['per_field'];events=one['events'];report={}
for name,start,end in [('A',1,1251),('B',3000,5600)]:
 rr=rows[start-1:end-1];ev=[(a,f) for a,f in events if start<=f<end]
 r=dict(first_field=start,end_field_exclusive=end,fields=end-start,seconds=(end-start)*142102/7093790,swaps=sum(a==0xb4 for a,f in ev),physics_calls=sum(a==0xcdae for a,f in ev),replay_iterations=sum(a==0x10bb6 for a,f in ev))
 r['fps']=r['swaps']/r['seconds'];r['start_state']=rr[0];r['end_state']=rows[end-1]
 for kind in ['state','front','tape']:
  h=hashlib.sha256()
  for f in range(start,end):h.update((first/f'{kind}-{f:05d}.bin').read_bytes())
  r[kind+'_sha256']=h.hexdigest()
 if name=='A':
  assert rr[0]['checkpoint']!=rr[-1]['checkpoint'] and rr[-1]['checkpoint']=='0x1f288'
  assert not any(v['crash'] or v['replay'] for v in rr)
 else:
  assert r['replay_iterations']==90,'full native replay required'
  assert not rows[end-1]['crash'] and not rows[end-1]['replay']
  assert {v['crash'] for v in rr}==set(range(26)),'complete native countdown required'
  # Jump lip: track centre (31939,189,17338); car must be over its width,
  # reach ramp height and then leave wheel contact beyond the crest.
  lip=[v for v in rr if 17280<=v['pose'][2]<=17400 and abs(v['pose'][0]-31939)<=100 and v['pose'][1]>=180 and not v['crash'] and not v['replay']]
  assert lip,'car did not reach the jump lip on the road'
  airborne=[]
  for v in rr:
   x,y,z=v['pose']
   if 16500<z<17300 and y>190 and not v['crash'] and not v['replay']:
    b=(first/f"state-{v['field']:05d}.bin").read_bytes()
    if b[0x7100-0x66f0]==0:airborne.append(v)
  assert airborne,'no airborne trajectory beyond the lip'
  r['jump_lip']=lip[0];r['airborne']=airborne[0]
 report[name]=r
(first/'windows.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
