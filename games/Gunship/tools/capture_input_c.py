#!/usr/bin/env python3
import json,struct,sys
from pathlib import Path
from session_b import Session
from route import run
from flight_profile import ROUTE
s=Session(sys.argv[1])
try:
 run(s,ROUTE)
 mem=s.read(0x200000,0x800000);hits=[];pos=0
 while True:
  pos=mem.find(b'GSIH0002',pos)
  if pos<0:break
  words=struct.unpack_from('>4I',mem,pos+8)
  if all(0x200000<x<0xa00000 for x in words):hits.append((0x200000+pos,words))
  pos+=8
 assert len(hits)==1,hits
 m,(h0,h2,h,sample)=hits[0]
 s.key(0x7f,True);s.fields(2);s.key(0x7f,False)
 initial=s.read(h,20)
 _,_,active,fault,_,_,last=struct.unpack('>4H3I',initial)
 assert active==1 and fault==0,initial.hex()
 field=last-int.from_bytes(initial[:2],'big')
 print('armed',hex(h),field,flush=True)
 s.fields(5)
 s.key('up',True);s.fields(4);s.key('up',False);s.fields(4)
 s.key('f1',True);s.fields(4);s.key('f1',False);s.fields(4)
 s.cmd('monitor mouse 8 -12');s.fields(8)
 s.cmd('monitor input JOY2_FIRE_BUTTON 1');s.fields(4)
 s.cmd('monitor input JOY2_FIRE_BUTTON 0');s.fields(4)
 data=s.read(h,5140);write,read,active,fault,lost,discarded,last=struct.unpack_from('>4H3I',data)
 (s.out/'failed-or-final-history.bin').write_bytes(data)
 print('final',s.read(m,44).hex(),flush=True)
 assert read==0 and 25<=write<128 and active==1 and fault==lost==0,(write,read,active,fault,lost)
 rec=[struct.unpack_from('>4IhhIHhhHII',data,20+40*i) for i in range(write)]
 assert [r[0] for r in rec]==list(range(field+1,field+write+1))
 assert last==field+write
 report=dict(marker=m,hunks=[h0,h2],fields=write,first=field+1,last=last,records=rec,
  directional_changes=sorted(set((r[1],r[2]) for r in rec)),
  command_sequences=sorted(set(r[6] for r in rec)),
  raw_delta_sums=[sum(r[8] for r in rec),sum(r[9] for r in rec)],
  held=sorted(set(r[3] for r in rec)),edges=sorted(set(r[10] for r in rec)))
 q=int.from_bytes(s.read(m+44,4),'big');commands=s.read(q,1048)
 count,player,world,enabled,cqfault=struct.unpack_from('>5H',commands)
 assert (count,player,world,enabled,cqfault)==(2,0,0,1,0),(count,player,world,enabled,cqfault)
 retained=[struct.unpack_from('>IHH',commands,24+8*i) for i in range(count)]
 assert retained==[(5,0x4c,0),(6,0x50,0)],retained
 report['retained_commands']=retained
 (s.out/'commands.bin').write_bytes(commands)
 (s.out/'history.bin').write_bytes(data);(s.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 print({k:v for k,v in report.items() if k!='records'},flush=True)
 s.shot('end.png')
finally:s.quit()
