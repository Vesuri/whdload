#!/usr/bin/env python3
"""Read player snapshots at consecutive VERIFY flight anchors; never write game RAM."""
import argparse,json,re,struct
from pathlib import Path
import route_status as r,step_log
p=argparse.ArgumentParser();p.add_argument('--key-code',type=lambda x:int(x,0));p.add_argument('--end',required=True,type=int);p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
at=r.locate();state=r.read(at);obs,h=step_log.header();sim,h3=state['sim'],h[5];rows=[]
keybase=None
if a.key_code is not None:
 import sys
 sys.path.insert(0,str(Path('tools').resolve()))
 from presentation_state import symbol
 meta=json.loads((a.out.parent/'entry.json').read_text())
 lines=(a.out.parent/'slave.lst').read_text(encoding='latin-1').splitlines()
 base=meta['entry']['game_anchor']-symbol(lines,'tape_game_anchor')
 reply=r.command(f'gdb x/wx {base+symbol(lines,"tape_keybase"):#x}')
 keybase=int(re.findall(r':\s*(0x[0-9a-f]+)',reply)[0],16)
 assert 0<=a.key_code<128 and keybase
 banks=[]
 for lo,hi in r.memory_regions():
  file=a.out/f'initial-{lo:x}.bin'
  r.command(f'gdb dump binary memory {file} {lo:#x} {hi:#x}')
  banks.append(dict(base=lo,size=hi-lo,file=file.name))
 (a.out/'initial.json').write_text(json.dumps(dict(banks=banks,sim=sim,h3=h3),indent=2)+'\n')
# Starting after the current step ensures the first sample is at an exact anchor,
# even when the caller was paused mid-frame by a preceding screenshot.
for target in range(state['game_steps'],a.end+1):
 if target!=state['game_steps']:
  reply=r.command(f'gdb break *{state["game_anchor"]:#x}\nbreak *{sim+0x21f4a:#x}\ncontinue\nprintf "PLAYER_STOP %u\\n", $pc\ndelete')
  stop=re.search(r'PLAYER_STOP (\d+)',reply)
  if not stop or int(stop[1])!=state['game_anchor']:raise RuntimeError('Flight ended before requested player sample')
 now=r.read(at)
 if now['game_steps']!=target:raise RuntimeError('Unexpected player step')
 raw=r.command(f'gdb x/wx {h3+0x4578:#x}')
 obj=int(re.findall(r':\s*(0x[0-9a-f]+)',raw)[0],16)
 if not any(lo<=obj and obj+0x118<=hi for lo,hi in r.memory_regions()):raise RuntimeError('Player object outside RAM')
 dest=a.out/f'player-{target}.bin'
 r.command(f'gdb dump binary memory {dest} {obj:#x} {obj+0x118:#x}')
 b=dest.read_bytes()
 # Retain raw candidates until their airspeed/physical-unit interpretation is proved.
 row=dict(step=target,object=obj,position=struct.unpack_from('>3i',b,8),orientation=struct.unpack_from('>3h',b,20),
          speed_word_7c=struct.unpack_from('>h',b,0x7c)[0],body_velocity_ca=struct.unpack_from('>3h',b,0xca),
          velocity_d0=struct.unpack_from('>3h',b,0xd0),body_velocity_f4=struct.unpack_from('>3h',b,0xf4),
          velocity_fa=struct.unpack_from('>3h',b,0xfa))
 if keybase is not None:
  reply=r.command(f'gdb x/bx {keybase+a.key_code:#x}')
  row['held_key']=dict(code=a.key_code,value=int(re.findall(r':\s*(0x[0-9a-f]+)',reply)[0],16))
 rows.append(row)
 if target in (state['game_steps'],a.end):r.command(f'gdb dump binary memory {a.out}/h3-{target}.bin {h3:#x} {h3+0xbd0c:#x}')
 (a.out/'players.json').write_text(json.dumps(rows,indent=2)+'\n')
steps=step_log.collect();(a.out/'steps.json').write_text(json.dumps(steps,indent=2)+'\n')
print('Retained',len(rows),'player records at steps',rows[0]['step'],'through',rows[-1]['step'])
