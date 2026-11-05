#!/usr/bin/env python3
"""Native keyboard and frame-anchor route for a production slave; no guest writes.
The owning bench_cell enforces the 180-second watchdog and emulator cleanup.
"""
import argparse,json,os,struct,subprocess,time,hashlib,re
from pathlib import Path
from profile_window import command,ROOT
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--frame',type=int,required=True);p.add_argument('--simulation',type=int,choices=[10,20,50],required=True);p.add_argument('--detail',type=int,choices=[0,3],required=True);a=p.parse_args();cap=a.capture.resolve();assert cap.is_relative_to(ROOT/'tmp');cap.mkdir()
slave=Path(os.environ['SLAVE']);assert b'4DTAPE!!' not in slave.read_bytes()
(cap/'slave.slave').write_bytes(slave.read_bytes());listing=slave.with_suffix('.lst')
if listing.exists():(cap/'slave.lst').write_bytes(listing.read_bytes())
log=(cap/'serve.log').open('w');proc=subprocess.Popen(['python3','tools/driving.py','serve'],cwd=ROOT,env=dict(os.environ,WARP="1",DETERMINISTIC="1",JOY0="none",JOY0_MODE="nothing"),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(cap/'serve.pid').write_text(str(proc.pid))
while 'serving on' not in (cap/'serve.log').read_text():
 if proc.poll() is not None:raise RuntimeError((cap/'serve.log').read_text())
 time.sleep(.1)
command('stop')
def fields(n):
 while n:
  k=min(n,6000);command(f'gdb monitor fields {k}');n-=k

def key(code):
 command(f'gdb monitor key {code:x} 1');fields(10);command(f'gdb monitor key {code:x} 0');fields(10)
for _ in range(2 if os.environ.get("BENCH_NATIVE_OPPONENT") else 4):fields(400);key(0x44)
fields(100)
fast=int(os.environ.get('BENCH_MEMORY_KB',os.environ['FAST_KB']));base=int(os.environ.get('BENCH_MEMORY_BASE','0x200000'),0) if fast else 0;end=base+fast*1024 if fast else 0xc00000+1536*1024

def dump(name):
 target=cap/name
 if fast:command(f'gdb dump binary memory {target.relative_to(ROOT)} {base:#x} {end:#x}')
 else:
  blob=bytearray(end)
  for lo,hi in [(0,int(os.environ['CHIP_KB'])*1024),(0xc00000,end)]:
   part=cap/'bank.bin';reply=command(f'gdb dump binary memory {part.relative_to(ROOT)} {lo:#x} {hi:#x}');assert part.exists(),reply;blob[lo:hi]=part.read_bytes();part.unlink()
  target.write_bytes(blob)
 return target.read_bytes()
b=dump('discovery.bin');command('shot '+str(cap/'discovery.png'));print('Discovery saved',flush=True);candidates=[]
for i in range(len(b)):
 if b.startswith(b'4DPERF!!',i):
  g=struct.unpack_from('>I',b,i+8)[0]
  if base<=g<end and b[g-base:g-base+2]==b'\x4e\xf9':candidates.append(g)
assert len(candidates)==1,candidates
g=candidates[0];data=4*struct.unpack_from('>I',b,g-base-4)[0]+4;aa=data+0x7ffe
# Optional native opponent setup, matching the established keyboard tape route.
if os.environ.get('BENCH_NATIVE_OPPONENT'):
 target=int(os.environ['BENCH_NATIVE_OPPONENT']);assert 1<=target<=6
 def menu_selection(off,local):
  out=command(f'gdb delete\nbreak *{g+off:#x}\ncontinue\np /u *(unsigned char *)($a5-({local}))\ndelete\nstepi')
  return int(re.search(r'^\$\d+ = (\d+)',out,re.M)[1])
 def select(off,local,wanted):
  for _ in range(12):
   selected=menu_selection(off,local)
   if selected==wanted:return
   key(0x4f)
  raise AssertionError(('Native menu selection',wanted,selected))
 select(0x32b0,2,2);key(0x44);fields(100)
 for _ in range(7):
  select(0x4dc6,10,1)
  out=command(f'gdb p /u *(unsigned char *){aa-0x174a:#x}')
  identity=int(re.search(r'\$\d+ = (\d+)',out)[1])
  if identity==target:break
  key(0x44);fields(100)
 assert identity==target
 select(0x4dc6,10,4);key(0x44);fields(100)
 select(0x32b0,2,0);key(0x44);fields(100)
 (cap/'opponent-setup.json').write_text(json.dumps(dict(opponent=target,route='Native Left/Return menus; no game-state writes'))+'\n')
# A loaded hunk has mode=0 before the cockpit exists. Require execution of
# the actual live frame boundary, using Return presses until it is reached.
import re
command(f'gdb delete\nbreak *{g+0x7500:#x}\ncondition $bpnum *(unsigned char *){aa+0x45:#x}==0 && *(unsigned char *){aa-0x16d8:#x}==0')
reached=False
for _ in range(40):
 for pressed in (1,0):
  command(f'gdb monitor key 44 {pressed}')
  command('wait 0.15');command('stop')
  regs=command('gdb info registers pc')
  pc_match=re.search(r'pc\s+0x([0-9a-f]+)',regs)
  if not pc_match:
   raise RuntimeError('Cannot read stopped PC at native startup: '+regs)
  if int(pc_match[1],16)==g+0x7500:
   reached=True;break
 if reached:break
assert reached,'Native Return route did not reach a live frame'
command('gdb delete\nmonitor key 44 0')
mode=0
b=dump('live-discovery.bin')
rate=struct.unpack_from('>H',b,aa-base-0x15fa)[0]
if os.environ.get('BENCH_EXPECT_RATE_AUTO')=='1':
 assert rate in (10,20);a.simulation=rate
else:assert rate==a.simulation,('Native default rate differs; explicit menu selection required',rate,a.simulation)
print('Mode',mode,'rate',rate,'detail',b[aa-base-0x7708],flush=True)
if b[aa-base-0x7708]!=a.detail:
 command('gdb monitor key 63 1');key(0x24);command('gdb monitor key 63 0');fields(100)
 if a.detail==3:key(0x4d);key(0x4d)
 key(0x44);key(0x45);fields(100)
command('shot '+str(cap/'ready.png'))
print('Driving frame anchor',flush=True)
if os.environ.get('BENCH_INITIAL_RIGHT')=='1':command('gdb monitor key 4e 1')
if os.environ.get('BENCH_NO_THROTTLE')!='1':command('gdb monitor key 4c 1')
script=['delete','set $bench_native_frames=0',f'break *{g+0x7500:#x}',f'condition $bpnum *(unsigned char *){aa+0x45:#x}==0','commands','silent','set $bench_native_frames=$bench_native_frames+1',f'if $bench_native_frames<{a.frame}','continue','end','end','continue','delete']
out=command('gdb '+'\n'.join(script));(cap/'frame-anchor.log').write_text(out)
b=dump('memory.bin');assert b[aa-base-0x7708]==a.detail
import re
syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
perf=next(i for i in range(len(b)) if b.startswith(b'4DPERF!!',i) and struct.unpack_from('>I',b,i+8)[0]==g)
slave_base=base+perf+8-syms['perf_game']
clock_symbols={n:slave_base+syms[n] for n in ('sim_clock_fields','sim_time_field_hz','sim_schedule_read','sim_schedule_write','sim_schedule_overflow','sim_schedule_ticks','sim_schedule_active','perf_failure') if n in syms}
m={'game_base':g,'data_base':data,'slave_base':slave_base,'clock_symbols':clock_symbols,'memory_base':base,'memory_size':len(b),'frame':a.frame,'anchor_code_offset':'0x7500','native_frame_counter':True,'slave_sha256':hashlib.sha256(slave.read_bytes()).hexdigest(),'scope':'Production native keyboard route; frame count begins when held throttle is queued after opening screens/detail selection. No VERIFY or guest memory writes.'};(cap/'anchor.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m))
