#!/usr/bin/env python3
import sys,json,struct,os,re
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]);m=json.loads((cap/'anchor.json').read_text());aa=m['data_base']+0x7ffe
log=(cap/'replay-route.log').open('w')
def fields(n):
 reply=command(f'gdb monitor fields {n}');command('gdb maintenance flush register-cache');log.write(reply+'\n');log.flush()
def key(k):
 command(f'gdb monitor key {k:x} 1');fields(15);command(f'gdb monitor key {k:x} 0');fields(30)
def snap(n):
 p=cap/(n+'.bin');lo=aa-0x8000;reply=command(f'gdb dump binary memory {p.relative_to(ROOT)} {lo:#x} {aa+0x3000:#x}');assert p.exists(),reply;b=p.read_bytes()
 values={name:struct.unpack_from('>'+fmt,b,0x8000+off)[0] for name,off,fmt in [('mode',0x45,'B'),('rate',-0x15fa,'H'),('consumer',-0x940,'H'),('producer',0xa0,'H'),('length',-0x1738,'H'),('selection',-0x74c1,'B'),('pause',0x44,'B'),('speed',0x3d,'B')]}
 (cap/(n+'.json')).write_text(json.dumps(values,indent=2));print(n,values,flush=True);return values
command('gdb monitor key 4c 0');key(0x45);fields(100);v=snap('replay-panel')
for _ in range(12):
 if v['selection']==6:break
 # Native directional tables at A4-$74c0..-$74a5; breadth-first route.
 from collections import deque
 raw=(cap/'replay-panel.bin').read_bytes()
 edges={0x4f:list(raw[0xb40:0xb49]),0x4e:list(raw[0xb49:0xb52]),0x4c:list(raw[0xb52:0xb5b]),0x4d:list(raw[0xb5b:0xb64])}
 todo=deque([(v['selection'],[])]);seen=set();route=None
 while todo:
  state,path=todo.popleft()
  if state==6:route=path;break
  if state in seen:continue
  seen.add(state)
  for k,table in edges.items():todo.append((table[state],path+[k]))
 assert route
 key(route[0]);v=snap('select-menu')
assert v['selection']==6
command('gdb monitor key 44 1')
reply=command(f'gdb tbreak *{m["game_base"]+0x9c26:#x}\ncontinue\ndelete');log.write(reply+'\n');command('gdb stepi')
command('gdb monitor key 44 0');fields(100);command('shot '+str(cap/'replay-menu.png'))
for _ in range(3):key(0x4d)
key(0x44);fields(100);command('shot '+str(cap/'load-dialog.png'));snap('load-dialog')
key(0x4d)
command('gdb monitor key 44 1');fields(15);command('gdb monitor key 44 0')
reply=command(f'gdb tbreak *{m["game_base"]+0x9f24:#x}\ncontinue\ndelete');log.write(reply+'\n');command('gdb stepi')
fields(100);command('shot '+str(cap/'loaded.png'));v=snap('loaded')
packet=(Path(os.environ['GAME'])/'data/DEFAULT.rpl').read_bytes();count=struct.unpack_from('>H',packet,24)[0];rate=packet[22]
assert v['mode']==2 and v['rate']==rate and v['length']==count,(v,rate,count)
command('wait 0.5');command('stop');command('shot '+str(cap/'loaded-resumed.png'));v=snap('loaded-panel')
print(command('gdb x/16wx $sp\nx/8wx $a5\nx/16bx $a4+0x2396'),flush=True)
key(0x45);fields(100);command('shot '+str(cap/'after-escape.png'));snap('after-escape')
for _ in range(5):key(0x4c)
key(0x44);fields(100);command('shot '+str(cap/'after-return.png'));snap('after-return')
print(command('gdb maintenance flush register-cache\ninfo registers pc a5'),flush=True)
