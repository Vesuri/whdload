"""Report native-step equivalence without hiding wall-clock/presentation differences."""
import argparse,json,struct,subprocess
from collections import Counter
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('off');p.add_argument('on');a=p.parse_args();root=Path(__file__).resolve().parents[1]/'tmp/prof'
paths=[root/a.off,root/a.on];meta=[json.loads((d/'metadata.json').read_text()) for d in paths]
assert (paths[0]/'slave.slave').read_bytes()==(paths[1]/'slave.slave').read_bytes()
assert meta[0]['layout']==meta[1]['layout'] and meta[0]['world_regions']==meta[1]['world_regions'],'This checker requires exact matching addresses, no inferred pointer normalization'
size=meta[0]['snapshot_size'];ws=meta[0]['world_snapshot_size'];assert ws>0 and size==meta[1]['snapshot_size']
def load(kind,stride):
 blobs=[subprocess.check_output(['zstd','-qdc',str(d/(kind+'.bin.zst'))]) for d in paths]
 assert len(blobs[0])==len(blobs[1]) and len(blobs[0])%stride==0
 return [[b[i:i+stride] for i in range(0,len(b),stride)] for b in blobs]
data=load('physics',size);world=load('world',ws);controls=load('controls',size);steps=len(data[0]);assert all(len(x)==steps for x in world)
# Dynamic tables must still be at the boot-time addresses captured by the harness.
for snapshots,external in zip(data,world):
 for b,w in zip(snapshots,external):
  for region in meta[0]['world_regions']:
   if 'pointer_global' in region:
    assert struct.unpack_from('>I',b,region['pointer_global']-0x8002)[0]==region['base']
    assert struct.unpack_from('>H',b,region['count_global']-0x8002)[0]==region['count']
  for i,region in enumerate(meta[0]['world_regions'][1:13]):
   assert struct.unpack_from('>I',w,i*46+8)[0]==region['base']
regions=[];off=0
for region in meta[0]['world_regions']:
 bad=[i for i,(x,y) in enumerate(zip(*world)) if x[off:off+region['size']]!=y[off:off+region['size']]]
 regions.append(dict(name=region['name'],bytes_per_snapshot=region['size'],count=region['count'],different_steps=bad));off+=region['size']
assert off==ws
# Native code provenance, not broad byte masks. All differences remain in output.
classes=[(0x8cd8,0x8cdc,'countdown display digits'),(0x8ce8,0x8cea,'off-road deadline display'),(0x902c,0x902e,'field-driven channel2 startup counter'),(0x9040,0x9041,'VBL BCD clock phase'),(0x9042,0x9046,'BCD arithmetic scratch operand'),(0x9090,0x909a,'VBL music player state'),(0x9050,0x9058,'polygon fill bounds scratch: native 329c..32ec'),(0x90aa,0x90b6,'instruction-text cursor/line state: native 69a0..69dc and 6a72..6a9e'),(0x979e,0x983e,'polygon clipping scratch: native 374a'),(0x983e,0x98de,'polygon clipping scratch: native 3746'),(0x9ca2,0x9cf0,'retained instruction-text buffer: native 69ce/69d6/6a8e'),(0x94ba,0x94bb,'scene flag includes off-road deadline byte'),(0x9582,0x9584,'countdown display cache'),(0x95ee,0x95f6,'VBL front/back buffer pointers'),(0x9790,0x9794,'elapsed BCD clock'),(0x9798,0x979c,'remaining BCD clock'),(0xadd8,0xaddc,'off-road BCD deadline')]
changes=Counter();raw_equal=0
for x,y in zip(*data):
 raw_equal+=x==y
 changes.update(i+0x8002 for i,(u,v) in enumerate(zip(x,y)) if u!=v)
classified=[]
for addr,count in sorted(changes.items()):
 category=next((c for lo,hi,c in classes if lo<=addr<hi),'UNCLASSIFIED')
 classified.append(dict(global_offset=hex(addr),different_steps=count,category=category))
domains={}
for name,lo,hi in [('car',0x98f6,0x9952),('rng',0x903c,0x9040),('replay_ring',0xb192,0xe91e),('replay_write_pointer',0xe91e,0xe922)]:
 bad=[i for i,(x,y) in enumerate(zip(*data)) if x[lo-0x8002:hi-0x8002]!=y[lo-0x8002:hi-0x8002]];domains[name]=dict(bytes_per_snapshot=hi-lo,different_steps=bad)
input_ranges=[(0x95f6,0x95f8),(0x95fa,0x95fe),(0x95ff,0x9600),(0x991d,0x991e)]
input_bad=[i for i,(x,y) in enumerate(zip(*controls)) if any(x[lo-0x8002:hi-0x8002]!=y[lo-0x8002:hi-0x8002] for lo,hi in input_ranges)]
scene_flag_boolean_equal=all(bool(x[0x94ba-0x8002])==bool(y[0x94ba-0x8002]) for x,y in zip(*data))
report=dict(scope='Paired per-physics-return snapshots; input mode is defined by the captured slave build. Complete native data/BSS and listed external structures, not rendered pixels or pointed-to vertex buffers',steps=steps,strict_data_bss_equal_steps=raw_equal,strict_full_snapshot_equivalence=raw_equal==steps and all(not r['different_steps'] for r in regions),external_regions=regions,domains=domains,control_snapshots=[len(x) for x in controls],input_difference_steps=input_bad,scene_flag_boolean_equal=scene_flag_boolean_equal,changed_global_bytes=classified,elapsed_fields=[m['events'][-1]['field'] for m in meta])
(paths[1]/'native-world-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
assert all(not r['different_steps'] for r in regions) and all(not d['different_steps'] for d in domains.values()) and not input_bad and len(controls[0])==len(controls[1]) and scene_flag_boolean_equal
print(json.dumps({k:v for k,v in report.items() if k not in ['external_regions','changed_global_bytes']},indent=2));print('Classified differing global bytes:',len(classified),'unclassified:',sum(x['category']=='UNCLASSIFIED' for x in classified))
