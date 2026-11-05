"""Enumerate the native selector's visible/obscured predicate per candidate."""
from unicorn_b import *
import json,itertools
base=0x100000;l=(root/'tmp/c/runtime.lst').read_text();sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
live=(build/'selector-combat.slave.lst').read_text(encoding='latin1');ls=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',live,re.M)[1],16)
folder=root/'tmp/c/homing-selection-pal-060';rows=json.loads((root/'tmp/c/homing-impulse-envelope.json').read_text());reports=[];cases=0
for row in rows:
 world=row['world'];d=folder/f'world-{world}';a=(d/'arena.bin').read_bytes();h=struct.unpack_from('>9I',a,ls('RT_HUNKS'));c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data()))
 for i in (0,6):c.put(h[i],(d/f'h{i}.bin').read_bytes())
 work=0x300000
 def call(name,args):
  for r,v in args.items():c.rw(r,v)
  c.rw(8,0x8f000);c.call(base+sym(name));assert c.rr(18)==0x90000 and c.rr(9)==0
 call('target_select_prepare',{1:h[0],2:h[6],3:work})
 colors=a[ls('RT_TARGET')+sym('WT_PALETTE')+24:ls('RT_TARGET')+sym('WT_PALETTE')+26];assert len(colors)==2
 admitted=next(v for v in range(256) if v not in colors);outcomes=[]
 originals={i:c.get(h[i],len((d/f'h{i}.bin').read_bytes())) for i in (0,6)}
 for variant in row['variants']:
  for visible in itertools.product((False,True),repeat=variant['count']):
   c.put(work+sym('WT_STATE'),bytes.fromhex(variant['candidate_state']))
   c.put(work+sym('WT_PIXELS'),bytes(admitted if v else colors[0] for v in visible)+bytes(6-len(visible)))
   c.put(work+sym('WT_PALETTE')+24,colors)
   call('target_select_step',{1:work,2:work+sym('WT_PIXELS'),3:work+sym('WT_PALETTE')+24})
   result=c.get(work+sym('WT_STATE'),168)
   outcomes.append(dict(impulses=variant['impulses'],visible=visible,selector=result[108:120].hex(),selection=result[4:8].hex(),status=result[0]));cases+=1
   assert all(c.get(h[i],len(v))==v for i,v in originals.items())
 selectors=sorted(set(v['selector'] for v in outcomes));native=(folder/f'world-{world+1}'/'h0.bin').read_bytes()[0xaa0a:0xaa16].hex()
 reports.append(dict(world=world,selectors=selectors,native_selector=native,native_in_envelope=native in selectors,certified_selector=len(selectors)==1 and selectors[0]==native,outcomes=outcomes));assert native in selectors,(world,selectors,native);c.close()
report=dict(cases=cases,stable_worlds=[r['world'] for r in reports if r['certified_selector']],uncertain_worlds=[r['world'] for r in reports if not r['certified_selector']],reports=reports)
(root/'tmp/c/homing-visibility-envelope.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='reports'},indent=2))
