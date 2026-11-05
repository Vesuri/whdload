from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1]/'tmp/prof'
poses=[];screens=[]
for kind in ('original','rebuilt'):
 folder=root/f'equivalence-{kind}-fields-v4';seq=[]
 for i in range(1001):
  b=(folder/f'state-{i:04d}.bin').read_bytes()
  pose=b[0xf0:0xf6]+b[0x144:0x14a] # a4-$6710 / a4-$66bc
  if not seq or seq[-1][1]!=pose:seq.append((i,pose))
 poses.append(seq);frames=[]
 for start in (0,0x8000):
  last=None;first=0
  for i in range(1002):
   h=hashlib.sha256((folder/f'screen-{i:04d}.bin').read_bytes()[start:start+32000]).hexdigest() if i<1001 else None
   if h!=last:
    if i-first>=5:frames.append((first,i,last))
    first=i;last=h
 frames.sort();screens.append(frames)
report=dict(samples=1001,fields=1000,game_layout_matches=True,padding_required=False,
 pose_sequences_match=[x[1] for x in poses[0]]==[x[1] for x in poses[1]],pose_samples=len(poses[0]),
 max_pose_observation_field_difference=max(abs(x[0]-y[0]) for x,y in zip(*poses)),
 stable_image_sequences_match=[x[2] for x in screens[0]]==[x[2] for x in screens[1]],stable_images=len(screens[0]),
 stable_definition='32,000-byte planar image unchanged for at least five consecutive VBL samples; both buffers examined',
 scope='Functional attract outcomes match; transient state/rendering differ. Not cycle-exact equivalence. Clocks outside sampled globals range; no player physics claim.',
 pose_sequence_sha256=hashlib.sha256(b''.join(x[1] for x in poses[0])).hexdigest(),
 image_sequence_sha256=hashlib.sha256(''.join(x[2] for x in screens[0]).encode()).hexdigest())
assert report['pose_sequences_match'] and report['stable_image_sequences_match']
(root/'equivalence-outcomes.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
