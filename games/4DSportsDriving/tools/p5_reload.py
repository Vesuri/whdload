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
assert x['mode']==2 and x['active_rate']==50 and x['recorded_length']==651,x
nav=[0x4c,0x4c,0x4f,0,0x4e,0x4e,0x4e,0x4e,0x4e]
for _ in range(12):
 if x['replay_selection']==3:break
 tap(nav[x['replay_selection']]);x=snapshot('select-play')
assert x['replay_selection']==3
# Install read-only checkpoints before pressing Play, so no tick can be missed.
lines=['delete','set $hit=0',f"break *{m['game_base']+0xe5f8:#x}",'commands','silent']
for tick in (200,400,600):
 lines += [f'if *(unsigned short *){a-0x940:#x}=={tick}',f'dump binary memory {(cap/('play-'+str(tick)+'.bin')).relative_to(ROOT)} 0x200000 0x600000','end']
lines += [f'if *(unsigned short *){a-0x940:#x}==600','set $hit=1','else','continue','end','end','monitor key 44 1','continue','monitor key 44 0','delete']
f=cap/'play.gdb';f.write_text('\n'.join(lines)+'\n');(cap/'play.log').write_text(command('gdb source '+str(f.relative_to(ROOT))))
snapshot('played')
