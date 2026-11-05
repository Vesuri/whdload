"""Read retained complete VBL state; never infer a reset from pose alone."""
import argparse,json,struct,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('names',nargs='+');a=p.parse_args();root=Path(__file__).resolve().parents[1]/'tmp/prof'
for name in a.names:
 path=root/name;meta=json.loads((path/'metadata.json').read_text());size=sum(r['size'] for r in meta['layout']['regions'][1:]);rows=[]
 proc=subprocess.Popen(['zstd','-qdc',str(path/'states.bin.zst')],stdout=subprocess.PIPE)
 while b:=proc.stdout.read(size):
  assert len(b)==size
  def val(off,fmt):return struct.unpack_from('>'+fmt,b,off-0x8002)[0]
  rows.append(dict(field=len(rows)+1,pose=[val(x,'h') for x in [0x98f6,0x98f8,0x98fa]],velocity=val(0x9928,'h'),throttle=val(0x991c,'B'),gear=val(0x9936,'h'),recover=val(0x9605,'B'),phase=val(0x8cec,'B'),crash=val(0x9606,'B'),replay=val(0xadd7,'B'),road=val(0xe94a,'B'),brake=val(0x9911,'B'),buttons=val(0x95f6,'H'),mouse=val(0x95fa,'I'),start_phase=val(0xadde,'B'),engine=val(0xaddc,'B'),offroad_countdown=val(0xadd8,'I'),clock=val(0x9790,'I')))
 assert proc.wait()==0
 def intervals(key):
  out=[];start=None
  for r in rows:
   if r[key] and start is None:start=r['field']
   if not r[key] and start is not None:out.append([start,r['field']]);start=None
  if start is not None:out.append([start,len(rows)+1])
  return out
 transitions=[]
 for old,new in zip(rows,rows[1:]):
  changed=[k for k in ['recover','crash','replay','engine'] if old[k]!=new[k]]
  if changed:transitions.append(dict(changed=changed,before=old,after=new))
 r=dict(name=name,fields=len(rows),intervals={k:intervals(k) for k in ['recover','crash','replay']},transitions=transitions,samples=[rows[i-1] for i in [1,100,200,400,800,1200,3000,5500] if i<=len(rows)])
 (path/'recovery-analysis.json').write_text(json.dumps(r,indent=2)+'\n');print(name,r['intervals']);print(json.dumps(transitions[:8],indent=2))
