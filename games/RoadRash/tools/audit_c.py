"""Freeze one game's simulation/render boundaries; list all changed state bytes."""
import os,sys,json,struct
from harness_a import *
s=Session(sys.argv[1])
try:
 initial=route(s)
 tape=json.loads((ROOT/'tools/fixtures/lap.json').read_text())
 for target,event,value in tape['events']:
  advance(s,target);s.input(event,value)
 advance(s,1800)
 target=rd(s,0x87480);data=read_bytes(s,target,1024);off=data.find(b'RRCAUD01')
 assert off>=0,'missing C audit marker'
 addr=target+off;header=read_bytes(s,addr,40)
 calls,mask,start,size,f0,f1,f2,chosen=struct.unpack_from('>8I',header,8)
 assert mask==7,(calls,mask,chosen)
 snapshots=[read_bytes(s,addr+40+i*size,size) for i in range(3)]
 for i,b in enumerate(snapshots):(s.out/f'boundary-{i}.bin').write_bytes(b)
 changes={}
 for label,a,b in [('simulation',snapshots[0],snapshots[1]),('presentation',snapshots[1],snapshots[2])]:
  changes[label]=[dict(address=hex(start+i),before=x,after=y) for i,(x,y) in enumerate(zip(a,b)) if x!=y]
 result=dict(provenance=provenance(os.environ['SLAVE'],s),calls=calls,frame=chosen,fields=[f0,f1,f2],start=start,size=size,changes=changes)
 (s.out/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
 print('fields',result['fields'],'changed bytes',{k:len(v) for k,v in changes.items()},flush=True)
 print('presentation actor writes',[x for x in changes['presentation'] if 0xa5d60<=int(x['address'],16)<0xa6ee0],flush=True)
finally:s.quit()
