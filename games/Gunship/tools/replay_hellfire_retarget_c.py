"""Resolve saved Hellfire forecast mismatches by isolating selector changes."""
from unicorn_b import *
import json,sys,os
base=0x100000
l=(root/'tmp/c/runtime.lst').read_text();sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
live=Path(os.environ['LISTING']).read_text(encoding='latin1');ls=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',live,re.M)[1],16)
reports=[]
for name in sys.argv[1:]:
 folder=Path(name)
 mismatch=json.loads((folder/'actor-forecast-dependency-audit.json').read_text())['mismatches']
 for m in mismatch:
  w=m['world'];d=folder/f'world-{w}';n=folder/f'world-{w+1}'
  arena=(d/'arena.bin').read_bytes();h=struct.unpack_from('>9I',arena,ls('RT_HUNKS'))
  c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data()))
  for i in [0,2,4,5,6]:c.put(h[i],(d/f'h{i}.bin').read_bytes())
  ap=0x300000
  def call(entry,args):
   for r,v in args.items():c.rw(r,v)
   c.rw(8,0x8f000);c.call(base+sym(entry));assert c.rr(18)==0x90000
   return c.rr(9)
  assert call('actor_preview_prepare',{1:h[0],2:h[6],3:ap})==0
  poses=[]
  for changed in [False,True]:
   if changed:c.put(h[0]+0xaa0a,(n/'h0.bin').read_bytes()[0xaa0a:0xaa16])
   native0=c.get(h[0],len((d/'h0.bin').read_bytes()));native6=c.get(h[6],len((d/'h6.bin').read_bytes()))
   mask=call('actor_preview_step',{1:ap,2:h[6]+0x3b88});assert mask&(1<<m['slot'])
   pose=[c.get(ap+sym('AP_ACTORS')+12*axis+2*m['slot'],2).hex() for axis in range(3)]
   assert c.get(h[0],len(native0))==native0 and c.get(h[6],len(native6))==native6
   poses.append(pose)
  assert poses[0]==m['predicted'] and poses[1]==m['native'],(w,poses,m)
  reports.append(dict(run=folder.name,world=w,old_selector=poses[0],next_selector=poses[1],native_next_pose=m['native'],native_memory_unchanged=True))
  c.close()
(root/'tmp/c/hellfire-retarget-replay.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))
