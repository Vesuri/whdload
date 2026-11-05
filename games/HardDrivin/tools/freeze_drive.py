"""Assemble the successful input-only calibration segments into VERIFY source."""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'tmp/prof/drive-stunt-calibration-4'
events={1:[1,320,200,4,0]}
first=json.loads((root/'tmp/prof/drive-steering-calibration/straight-recording.json').read_text())
for r in first['records']:
 if r[0]<708:events[r[0]]=r
for label in ['stunt','stunt-adaptive']:
 for r in json.loads((out/(label+'-recording.json')).read_text())['records']:events[r[0]]=r
events[2096]=[2096,320,200,0,0]
for label in ['stunt-recovered','stunt-recovered-fast']:
 for r in json.loads((out/(label+'-recording.json')).read_text())['records']:events[r[0]]=r
# Additional final jump/crash inputs are explicit field-indexed native controls.
extra=out/'final-inputs.json'
if extra.exists():
 for r in json.loads(extra.read_text()):events[r[0]]=r
# Frozen-run correction: align with the narrow ramp before takeoff.
events={f:r for f,r in events.items() if not 4001<=f<4595}
events[4001]=[4001,380,200,4,0]
events[4097]=[4097,360,200,4,0]
events[4233]=[4233,320,200,4,0]
compact=[]
for f,r in sorted(events.items()):
 assert f>0 and 0<=r[1]<=639 and 0<=r[2]<=399 and r[3] in [0,1,4,5] and r[4]==0
 if not compact or r[1:]!=compact[-1][1:]:compact.append(r)
assert compact[-1][3]==0,'Final input must release buttons for replay'
p=root/'src/HardDrivinVerify.s'
s=p.read_text(encoding='latin1').split('_verify_drive_tape:\n')[0]+'_verify_drive_tape:\n'
for f,x,y,buttons,key in compact:s+=f'\tdc.l {f}\n\tdc.w {x},{y},{buttons},{key}\n'
s+='\tdc.l -1\n';p.write_text(s,encoding='latin1')
(out/'frozen-inputs.json').write_text(json.dumps(compact,indent=2)+'\n')
print(len(compact),'events; last',compact[-1])
