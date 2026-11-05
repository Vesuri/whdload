import json,os,re,signal,subprocess,time,struct
from pathlib import Path
from profile_window import command,ROOT
p=ROOT/'tmp/prof/p3-clone-probe';p.mkdir(exist_ok=False)
slave=ROOT/'tmp/build/p3-full-code-fast.slave';syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',slave.with_suffix('.lst').read_text(encoding='latin1'),re.M)}
def alarm(*args):raise TimeoutError('170-second diagnostic watchdog')
signal.signal(signal.SIGALRM,alarm);signal.alarm(170)
env=dict(os.environ,SLAVE=str(slave),DEBUG_PORT='2471',CPU='68060-NOMMU',AMIGA_MODEL='A1200',CHIP_KB='2048',FAST_KB='8192',EXTRA_ARGS='--slow_memory=0 --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=50000000 --motherboard_ram=8192 --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true',WHD_ARGS='CUSTOM2=1',KICKSTART=str(Path.home()/'.local/share/amiga/Kickstarts/kick40068.A1200'),WARP='1',DETERMINISTIC='1',JOY0='none',JOY0_MODE='nothing')
try:
 with (p/'serve.log').open('w') as f:proc=subprocess.Popen(['python3','tools/driving.py','serve'],env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 while 'serving on' not in (p/'serve.log').read_text():
  assert proc.poll() is None;time.sleep(.1)
 command('stop');command('gdb monitor fields 2500')
 (p/'registers.log').write_text(command('gdb info registers'))
 command(f'shot {p}/screen.png')
 command(f'gdb dump binary memory {p.relative_to(ROOT)}/memory.bin 0x200000 0xa00000')
 b=(p/'memory.bin').read_bytes();found=[]
 for i in range(len(b)):
  if b.startswith(b'4DPERF!!',i):
   g=struct.unpack_from('>I',b,i+8)[0]
   if 0x200000<=g<0xa00000 and b[g-0x200000:g-0x200000+2]==b'\x4e\xf9':found.append((0x200000+i+8-syms['perf_game'],g))
 print(found,flush=True);assert len(found)==1
 base,g=found[0];names=['p3_clone_address','raster_buffer','tape_configured','tape_frames','tape_phase'];names=[n for n in names if n in syms]
 text=command('gdb '+'\n'.join(f'p /x *(unsigned int*){base+syms[n]:#x}' for n in names));print(names,text,flush=True)
 (p/'state.json').write_text(json.dumps(dict(slave_base=base,game=g,names=names,values=text),indent=2)+'\n')
 clone=struct.unpack_from('>I',b,base-0x200000+syms['p3_clone_address'])[0]
 text=command('gdb '+ '\n'.join(f'p /x *(unsigned int*){clone+syms[n]:#x}' for n in ['raster_buffer','raster_staged_count','raster_fallback_count','raster_frame_phase','perf_game','perf_reset']))
 (p/'clone-state.log').write_text(text);print(text,flush=True)
finally:
 signal.alarm(0)
 pidfile=ROOT/'tmp/run/default/.run/fsuae.pid'
 if pidfile.exists():
  pid=int(pidfile.read_text());r=subprocess.run(['lsof','-a','-p',str(pid),'-d','cwd','-Fn'],capture_output=True,text=True)
  dirs=[x[1:] for x in r.stdout.splitlines() if x.startswith('n')]
  assert not dirs or len(dirs)==1 and Path(dirs[0]).is_relative_to(ROOT),dirs
  if dirs:
   try:subprocess.run(['python3','tools/driving.py','quit'],check=True,timeout=5)
   except Exception:
    os.kill(pid,signal.SIGTERM)
