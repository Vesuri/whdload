#!/usr/bin/env python3
"""Verify every compiled simulation hook retains relocated native bytes in legacy mode."""
import sys,re,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];cap=Path(sys.argv[1]);m=json.loads((cap/'anchor.json').read_text());mem=(cap/'memory.bin').read_bytes();sy={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)\s*$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
b=(ROOT/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes();u=lambda o:struct.unpack_from('>I',b,o)[0];nh=u(8);pos=20+4*nh;hunks=[];relocs=[];current=-1
while pos<len(b):
 kind=u(pos)&0x3fffffff;pos+=4
 if kind in (1001,1002,1003):
  current+=1;n=u(pos)*4;pos+=4;hunks.append(bytearray(b[pos:pos+n]) if kind!=1003 else bytearray(n));pos+=n if kind!=1003 else 0
 elif kind==1004:
  while (n:=u(pos)):
   target=u(pos+4);pos+=8
   for _ in range(n):relocs.append((current,u(pos),target));pos+=4
  pos+=4
 elif kind==1010:pass
 elif kind==1008:
  while (n:=u(pos)):pos+=4+4*n+4
  pos+=4
 else:raise ValueError((pos-4,kind))
bases=[m['game_base'],m['data_base']]
for src,off,target in relocs:
 if src==0:struct.pack_into('>I',hunks[0],off,struct.unpack_from('>I',hunks[0],off)[0]+bases[target])
code=hunks[0];source=(ROOT/'src/4DSportsDrivingHD.s').read_text();body=source.split('pl_main\n',1)[1].split('PL_W\t$2E77A',1)[0];checks={}
for kind,addr,args in re.findall(r'^\s*PL_(PSS|PS|P|NOP)\s+\$([0-9a-fA-F]+),([^\n;]+)',body,re.M):
 off=int(addr,16);parts=[x.strip() for x in args.split(',')]
 if kind!='NOP' and parts[0] not in sy:continue
 if off in (0x80ee,0x80f4,0x9e50):continue # bounded replay reader retained deliberately
 n=int(parts[0],0) if kind=='NOP' else 6+(int(parts[1],0) if kind=='PSS' else 0)
 checks[off]=max(checks.get(off,0),n)
for off,n in checks.items():
 actual=mem[m['game_base']-m['memory_base']+off:m['game_base']-m['memory_base']+off+n]
 assert actual==code[off:off+n],(hex(off),n,actual.hex(),code[off:off+n].hex())
base=m['slave_base'];read=lambda n,fmt:struct.unpack_from('>'+fmt,mem,base+sy[n]-m['memory_base'])[0]
assert read('_custom3','I')&1
assert read('sim_clock_installed','H')==read('sim_clock_fields','I')==read('sim_clock_installs','I')==0
assert read('sim_schedule_active','H')==read('sim_preferences_loads','I')==0
for off,target in [(0x80ee,'sim_replay_load_entry_stub'),(0x9e50,'sim_replay_load_result_stub')]:
 at=m['game_base']-m['memory_base']+off;assert mem[at:at+2] in (b'\x4e\xf9',b'\x4e\xb9');assert struct.unpack_from('>I',mem,at+2)[0]==base+sy[target]
r=dict(hook_spans=len(checks),hook_bytes=sum(checks.values()),clock_installs=0,clock_fields=0,prefs_loads=0,bounded_replay_reader=True,all_compiled_simulation_hooks_native=True)
(cap/'legacy-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
