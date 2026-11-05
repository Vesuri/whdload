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
# Cache epochs and fetches only: no writes to emulated memory.
def logbreak(at, body):
 cmd.extend([f'break *{at:#x}', 'commands', 'silent', *body, 'continue', 'end'])
sim=m['entry']['sim']
logbreak(sim+0x3a900,[f'set $gc_n=*(unsigned short*){h3+0xa350:#x}', 'set $gc_j=0', 'set $gc_sum=0', 'while $gc_j < $gc_n', f'set $gc_sum=$gc_sum+*(unsigned char*)({h3+0xa4e6:#x}+$gc_j)', 'set $gc_j=$gc_j+1', 'end', 'printf "GEO_RESET %u %u\\n", $gc_n, $gc_sum'])
coords=lambda: ', '.join(f'*(unsigned long*)({h3+off:#x}+4*$gc_i)' for off in (0xa5e6,0xa9e2,0xadde))
for off,path,index in [(0x38dcc,32,'$d0 & 65535'),(0x3ab30,16,'$d2 & 65535'),(0x3abf4,17,'$d2 & 65535')]:
 body=[f'set $gc_i={index}',f'printf "GEO_FETCH {path} %u %u %u %u %u\\n", $gc_i, *(unsigned char*)({h3+0xa4e6:#x}+$gc_i), '+coords()]
 if path==32:
  body += [f'if *(unsigned char*)({h3+0xa4e6:#x}+$gc_i) == 0', f'set $gc_v=*(unsigned long*){h3+0xa34c:#x}+6*$gc_i', f'set $gc_m=*(unsigned long*){h3+0xa438:#x}']
  args=[f'*(unsigned short*)($gc_v+{i*2})' for i in range(3)]+[f'*(unsigned short*)($gc_m+{i*2})' for i in range(9)]+['*(unsigned char*)($gc_m+18)',f'*(unsigned short*){h3+0xa344:#x}']+[f'*(unsigned long*){h3+off:#x}' for off in (0xa448,0xa44c,0xa450)]
  body += ['printf "GEO_INPUT '+' '.join(['%u']*len(args))+'\\n", '+', '.join(args),'end']
 logbreak(sim+off,body)
for at,path,scratch,width in [(sim+0x38e00,32,0xa4c6,4),(base+symbol(lines,'vertex_return'),32,0xa4c6,4),(sim+0x38e7e,32,0xa4c6,4),(sim+0x3abda,16,0xa4ae,2),(sim+0x3acc2,17,0xa4b4,2)]:
 vals=', '.join(f'*(unsigned {"long" if width==4 else "short"}*){h3+scratch+i*width:#x}' for i in range(3))
 logbreak(at,[f'printf "GEO_RESULT {path} %u %u %u %u %u %u %u %u\\n", $gc_i, *(unsigned char*)({h3+0xa4e6:#x}+$gc_i), '+coords()+', '+vals])
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
