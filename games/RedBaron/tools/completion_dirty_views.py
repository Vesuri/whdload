import json,re,sys,socket,subprocess,time
from pathlib import Path
import route_status as r
out=Path(sys.argv[1]);subprocess.run([sys.executable,'tools/completion_full_layers_check.py',str(out)],check=True)
e=json.loads((out/'entry.json').read_text())['entry'];sim=e['sim'];s=(out/'slave.lst').read_text(encoding='latin1')
sym=lambda n:int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)',s,re.M)[1],16)
base=e['game_anchor']-sym('tape_game_anchor')
with (out/'input.log').open('w') as log:
 host=subprocess.Popen([sys.executable,'tools/completion_host_input.py','--serve','--irq-only'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(out/'input.pid').write_text(str(host.pid))
for _ in range(90):
 if 'INPUT READY' in (out/'input.log').read_text():break
 if host.poll() is not None:raise RuntimeError('Input server stopped')
 time.sleep(1)
else:raise TimeoutError('Owned input server remains pending')
def command(value):
 with socket.socket(socket.AF_UNIX) as c:
  c.connect(str(Path('tmp/run/default/.run/completion-input.sock').resolve()));c.sendall(value.encode());answer=c.recv(65536).decode();assert answer.startswith('OK '),answer

def advance(addr,n):
 raw=r.command(f'gdb delete\nbreak *{addr:#x}\nignore $bpnum {n-1}\ncontinue\ndelete')
 assert re.search(rf'Breakpoint \d+, 0x{addr:x} in',raw),raw
 return raw
command(f'irq-down:{sim},200588,81');advance(sim+0x2d34e,10)
command(f'irq-up:{sim},200588,81');advance(sim+0x2d34e,10)
advance(e['game_anchor'],8)
a=base+sym('cockpit_final_fault')
raw=r.command(f'gdb dump binary memory {out}/first-fault.bin {a:#x} {a+24:#x}\nx/5uw {base+sym("cockpit_final_counts"):#x}')
(out/'fault.log').write_text(raw);print(raw,flush=True)
print((out/'first-fault.bin').read_bytes().hex(),flush=True)
views=[]
for name,key in [('left',82),('right',83),('front',80)]:
 command(f'irq-down:{sim},200588,{key}');advance(sim+0x2d34e,10)
 command(f'irq-up:{sim},200588,{key}');advance(sim+0x2d34e,10)
 advance(e['game_anchor'],8)
 advance(sim+0x3154a,5)
 raw=r.command(f'gdb x/5uw {base+sym("cockpit_final_counts"):#x}')
 print(name,raw,flush=True);views.append({'view':name,'counts':raw})
(out/'views.json').write_text(json.dumps(views,indent=2))
raw=r.command(f'gdb x/3uw {base+sym("cockpit_final_dirty_counts"):#x}\nx/4uh {base+sym("cockpit_final_rect"):#x}')
(out/'dirty.log').write_text(raw);print(raw,flush=True)

a=base+sym('cockpit_final_counts')
r.command(f'gdb dump binary memory {out}/final-counts.bin {a:#x} {a+20:#x}')
subprocess.run([sys.executable,'tools/completion_host_input.py','quit'],check=True);host.wait(timeout=20)
print(r.command('quit'),flush=True)
