import os,sys,json,shutil,subprocess
from pathlib import Path
p=Path(sys.argv[1]).resolve();os.environ['RUNTIME_CAPTURE']=str(p)
a=p/'start';a.mkdir()
for n in ('anchor.json','slave.lst','slave.slave','memory.bin'):shutil.copyfile(p/n,a/n)
from runtime_lifecycle_probe import snapshot

from runtime_lifecycle_probe import key,fields,command,m,a,irq,base,s,cap
from profile_window import ROOT
def tap(k):key(k,1);fields(10);key(k,0);fields(10)
tap(0x45);fields(40);tap(0x44);fields(30)
for _ in range(3):tap(0x4d)
tap(0x44);fields(40);tap(0x4d);tap(0x44);fields(100)
x=snapshot('loaded');command('shot '+str(cap/'loaded.png'))
assert x['mode']==2 and x['active_rate']==50 and x['recorded_length']==1653,x
nav=[0x4c,0x4c,0x4f,0,0x4e,0x4e,0x4e,0x4e,0x4e]
for _ in range(12):
 if x['replay_selection']==3:break
 tap(nav[x['replay_selection']]);x=snapshot('select-play')
assert x['replay_selection']==3
# Install read-only checkpoints before pressing Play, so no tick can be missed.
lines=['delete','set $hit=0',f"break *{m['game_base']+0xe5f8:#x}",'commands','silent']
for tick in (1500,1550,1600):
 lines += [f'if *(unsigned short *){a-0x940:#x}=={tick}',f'dump binary memory {(cap/('play-'+str(tick)+'.bin')).relative_to(ROOT)} 0x200000 0x600000','end']
lines += [f'if *(unsigned short *){a-0x940:#x}==1600','set $hit=1','else','continue','end','end','monitor key 44 1','continue','monitor key 44 0','delete']
f=cap/'play.gdb';f.write_text('\n'.join(lines)+'\n');(cap/'play.log').write_text(command('gdb source '+str(f.relative_to(ROOT))))
snapshot('played')

import struct,hashlib
packet=(Path(os.environ['GAME'])/'data/a4test.rpl').read_bytes()
b=(cap/'loaded.bin').read_bytes();aa=m['data_base']+0x7ffe-m['memory_base'];ptr=struct.unpack_from('>I',b,aa-0x17a4)[0]-m['memory_base'];assert b[ptr:ptr+1802]==packet[62104:63906]
ref=Path('tmp/runtime-route-v2-regression/full-first/states.bin').read_bytes();matches=[]
for tick in (1500,1550,1600):
 b=(cap/('play-'+str(tick)+'.bin')).read_bytes();v=b[aa-0xa80:aa-0x620]+b[aa+0x228:aa+0x22e]
 for tag,num in [(b'4DA4PHYS',152),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:i=b.index(tag)+12;v+=b[i:i+num]
 expected=ref[(tick-1351)*1510:(tick-1350)*1510];assert v==expected,(tick,[i for i,(x,y) in enumerate(zip(v,expected)) if x!=y][:20]);matches.append(dict(tick=tick,equal_bytes=1510,sha256=hashlib.sha256(v).hexdigest()))
(cap/'route-replay-check.json').write_text(json.dumps(dict(matches=matches,recorded_route_bytes_restored=1802,file_sha256=hashlib.sha256(packet).hexdigest(),scope='Existing format-2 opponent regression fixture, native fresh-process Load and Play. Preserves the recorded 80-entry route even though fresh A4000 routing now chooses 59. This fixture is not new disk-save evidence.'),indent=2)+'\n')
