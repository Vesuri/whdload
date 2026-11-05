"""Read-only native pose snapshots plus exact intervening lifecycle addresses."""
import argparse,json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from presentation_state import symbol
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--steps',type=int,default=16);a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(encoding='latin-1').splitlines();base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');stop=base+symbol(lines,'time_pose_captured');life=base+symbol(lines,'time_pose_invalidate');h3=json.loads((a.capture/'entry-steps.json').read_text())['h3'];banks=r.memory_regions()
player=int.from_bytes((a.capture/'entry-h3.bin').read_bytes()[0x4578:0x457c],'big')
loop=base+symbol(lines,'time_loop_state');header=base+symbol(lines,'time_pose_header');exit_at=base+symbol(lines,'time_loop_exit')
cmd=['delete',f'break *{life:#x}','commands','silent','printf "LIFE %u\\n", $a3','continue','end',f'break *{stop:#x}']
cmd += [f'break *{m["entry"]["sim"]+0x193a2:#x} if *(unsigned long*)($a5+16) == {player:#x}', 'commands', 'silent', f'printf "IMPACT %u %u %d %d %u\\n", *(unsigned long*){loop+28:#x}, *(unsigned long*){header+4:#x}, *(int*){player+16:#x}, *(short*){player+254:#x}, *(unsigned char*){player+266:#x}', 'continue', 'end']
cmd += [f'break *{m["entry"]["sim"]+0x192d8:#x} if *(unsigned long*)($sp+12) == {player:#x}', 'commands', 'silent', 'set $contact_limits=*(unsigned long*)($sp+4)', 'set $contact_motion=*(unsigned long*)($sp+8)', f'printf "CONTACT %u %d %d %d %d %d %d %d %d %d %d\\n", *(unsigned long*){loop+28:#x}, *(short*){player+20:#x}, *(short*){player+22:#x}, *(short*)($contact_motion+56), *(short*)($contact_motion+64), *(signed char*)($contact_motion+76), *(short*)($contact_limits+62), *(short*)($contact_limits+64), *(short*)($contact_limits+66), *(short*)($contact_limits+68), *(short*)($contact_limits+70)', 'continue', 'end']
for off in [0x15cc6]:
 cmd += [f'break *{m["entry"]["sim"]+off:#x} if $a3 == {player:#x}', 'commands', 'silent', f'printf "FLAG_CONSUME %u %u %u\\n", *(unsigned long*){loop+28:#x}, *(unsigned char*){player:#x}, *(unsigned char*){player+36:#x}', 'continue', 'end']
for off,label,fmt,args in [
 (0x19d1a,'RECT_READ','%u %u %u %d %d %d %d %d %d %d %u',f'*(unsigned long*){loop+28:#x}, $d4 & 65535, *(unsigned char*){h3+0x711d:#x}, $a0-{h3:#x}, *(short*)$a0, *(short*)($a0+2), *(short*)($a0+4), *(short*)($a0+6), *(signed char*){h3+0x1b1a:#x}, *(signed char*){h3+0x1b1b:#x}, (($d7 & 65535) != 0) || (*(unsigned char*){h3+0x711c:#x} != 0)'),
 (0x19d8c,'RECT_CLIP','%d %d %d %d',f'*(short*){h3+0x9d48:#x}, *(short*){h3+0x9d4a:#x}, *(short*){h3+0x9d4c:#x}, *(short*){h3+0x9d4e:#x}'),
 (0x19ddc,'RECT_STORE','%d %d %d %d %d',f'$a1-{h3:#x}, *(short*)$a0, *(short*)($a0+2), *(short*)($a0+4), *(short*)($a0+6)'),
 (0x19de0,'RECT_AFTER','%d %d %d %d %d',f'$a1-{h3:#x}-8, *(short*)($a1-8), *(short*)($a1-6), *(short*)($a1-4), *(short*)($a1-2)')]:
 cmd += [f'break *{m["entry"]["sim"]+off:#x}', 'commands', 'silent', f'printf "{label} {fmt}\\n", {args}', 'continue', 'end']
cmd += [f'break *{exit_at:#x}']
initial=[]
for address,end in banks:
 file=a.capture/f'world-initial-{address:x}.bin'
 r.command(f'gdb dump binary memory {file} {address:#x} {end:#x}')
 assert file.stat().st_size==end-address
 initial.append(dict(base=address,size=end-address,file=file.name))
(a.capture/'world-initial.json').write_text(json.dumps(dict(sha256=m['slave_sha256'],h3=h3,banks=initial),indent=2)+'\n')
r.command('gdb '+'\n'.join(cmd));frames=[]
for i in range(a.steps):
 raw=r.command('gdb continue\nprintf "POSESTOP %u\\n", $pc')
 (a.capture/f'pose-{i}-events.txt').write_text(raw)
 match=re.search(r'POSESTOP (\d+)',raw)
 if not match or int(match[1]) not in (stop,exit_at):raise RuntimeError(raw[-1500:])
 terminal=int(match[1])==exit_at
 files=[]
 for address,end in banks:
  file=a.capture/f'pose-{i}-{address:x}.bin'
  r.command(f'gdb dump binary memory {file} {address:#x} {end:#x}')
  assert file.stat().st_size==end-address
  files.append(dict(base=address,size=end-address,file=file.name))
 if terminal:
  state=r.command(f'gdb printf "EXIT %u %u %u\\n", $d0, *(unsigned long*){loop+28:#x}, *(unsigned long*){header+4:#x}')
  values=list(map(int,re.search(r'EXIT ([0-9 ]+)',state)[1].split()))
  (a.capture/'flight-exit.json').write_text(json.dumps(dict(sha256=m['slave_sha256'],h3=h3,return_value=values[0],started=values[1],completed=values[2],banks=files,events=raw),indent=2)+'\n')
  print('Flight exit',values,flush=True);break
 frames.append(dict(index=i,contacts=[list(map(int,v.split())) for v in re.findall(r'^CONTACT ([0-9 -]+)$',raw,re.M)],impacts=[list(map(int,v.split())) for v in re.findall(r'^IMPACT ([0-9 -]+)$',raw,re.M)],lifecycle=[int(v) for v in re.findall(r'^LIFE (\d+)',raw,re.M)],banks=files))
 (a.capture/'poses.json').write_text(json.dumps(dict(sha256=m['slave_sha256'],h3=h3,frames=frames),indent=2)+'\n')
 print('Captured pose boundary',i,'lifecycle events',len(frames[-1]['lifecycle']),flush=True)
