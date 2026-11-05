"""Bounded native-key view transitions for the retained gauge cache."""
import json,re,struct,subprocess,sys
from pathlib import Path
sys.path.insert(0,'tools')
from completion_machines import environment
from instrument_cache_result import check
sys.path.insert(0,'tools')
import route_status as r,step_log
out=Path('tmp/prof/completion-e2-gauge-views')
if out.exists():raise SystemExit('Refusing overwrite')
pid=Path('tmp/run/default/.run/fsuae.pid')
if pid.exists():
 p=subprocess.run(['ps','-p',pid.read_text().strip(),'-o','stat=,command='],capture_output=True,text=True)
 if p.returncode==0 and not p.stdout.lstrip().startswith('Z'):raise SystemExit('Existing process: '+p.stdout)
env=environment('040',0x72ffa)
env.update(BOOT_TIMEOUT='240',GAME_DIR='completion-benchmark/RedBaron')
subprocess.run([sys.executable,'-B','tools/reach_flight.py','--no-shot','--out',str(out)],env=env,check=True)
sym={m[1]:int(m[2],16) for line in (out/'slave.lst').read_text(encoding='latin1').splitlines() if (m:=re.match(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',line))}
entry=json.loads((out/'entry.json').read_text())['entry'];base=entry['game_anchor']-sym['tape_game_anchor'];sim=entry['sim']
from runtime_buffers import live_address
lines=(out/'slave.lst').read_text(encoding='latin1').splitlines()
def at(n):return live_address(lines,base,n,r.command)
def values(command):
 raw=r.command('gdb printf "VALUE '+command+'\\n"')
 return raw
raw=r.command(f'gdb printf "H3 %u\\n", *(unsigned int*){at("instrument_cache_h3"):#x}')
h3=int(re.search(r'H3 (\d+)',raw)[1]);rows=[]
def dump(n,size,label):
 p=out/(label+'-'+n+'.bin');a=at(n)
 r.command(f'gdb dump binary memory {p} {a:#x} {a+size:#x}')
 return p.read_bytes()
def advance(count):
 return r.command(f'gdb delete\nbreak *{entry["game_anchor"]:#x}\nignore $bpnum {count-1}\ncontinue\ndelete')

def tap(key):
 q=at('time_input_observe_queue');state=at('time_loop_state')
 raw=r.command(f'gdb printf "QUEUE %u %u %u %u %u %u %u\\n", *(unsigned short*){q:#x}, *(unsigned short*){q+2:#x}, *(unsigned short*){q+4:#x}, *(unsigned int*){state+20:#x}, *(unsigned int*){state+44:#x}, *(unsigned int*){state+40:#x}, *(unsigned short*){at("time_keys_ready"):#x}')
 head,tail,overflow,cursor,paused,active,ready=map(int,re.search(r'QUEUE ([0-9 ]+)',raw)[1].split())
 assert head==tail and not overflow and active==ready==1,raw
 commands=[]
 for i,(delta,down) in enumerate(((1,1),(2,0))):
  data=struct.pack('>IHHII',(cursor-paused+delta)&0xffffffff,key,down,0,0)
  address=q+16+((head+i)&255)*16
  commands.extend(f'set {{unsigned int}}{address+j:#x}={int.from_bytes(data[j:j+4],"big"):#x}' for j in range(0,16,4))
 commands.extend((f'set {{unsigned short}}{q+6:#x}=2',f'set {{unsigned short}}{q:#x}={(head+2)&65535}'))
 r.command('gdb '+'\n'.join(commands))
 print(advance(8),flush=True)
def view(label,expected):
 cmd=['delete','set $gauge_hits=0',f'break *{sim+0x19d22:#x}','commands','silent','set $gauge_hits=$gauge_hits+1','continue','end',f'break *{sim+0x3154a:#x}','ignore $bpnum 4','continue',f'printf "VIEW %u %u\\n", *(unsigned short*){h3+0x6712:#x}, $gauge_hits','delete']
 raw=r.command('gdb '+'\n'.join(cmd));(out/(label+'.log')).write_text(raw)
 v,count=map(int,re.search(r'VIEW (\d+) (\d+)',raw).groups());assert v==expected,(label,v,expected)
 if expected:assert count==0,(label,count)
 print(r.command('shot '+str((out/(label+'.png')).resolve())),flush=True)
 row=dict(label=label,view=v,publications=5,gauge_entries=count)
 rows.append(row);(out/'views.json').write_text(json.dumps(rows,indent=2)+'\n');print(row,flush=True)
print(step_log.advance(80),flush=True)
front=check(dump('instrument_cache_twin_result',32,'front'),dump('instrument_cache_stats',8,'front'))
(out/'front-twin.json').write_text(json.dumps(front,indent=2)+'\n')
view('front',0)
for label,key,v in [('rear',0x51,1),('left',0x52,2),('right',0x53,3),('front-return',0x50,0)]:
 tap(key);view(label,v)
print('VIEW TRANSITIONS COMPLETE; paused for map check',flush=True)
