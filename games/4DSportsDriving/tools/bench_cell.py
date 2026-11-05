#!/usr/bin/env python3
"""Bounded benchmark runner. Never clean up an emulator outside this harness."""
import argparse,json,os,subprocess,time,hashlib,signal,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];os.chdir(ROOT)
p=argparse.ArgumentParser();p.add_argument('slave',type=Path);p.add_argument('cell',choices=['A','A-fast','B','B-fast','C','C-fast','D','D-fast','E','E-fast']);p.add_argument('output',type=Path);a=p.parse_args();slave=a.slave.resolve();out=a.output.resolve();assert not out.exists()
cell=a.cell.split('-')[0];detail=int(os.environ.get('BENCH_DETAIL','3' if a.cell.endswith('-fast') else '0'));sim=10 if cell=='A' else int(os.environ.get('BENCH_SIMULATION','50' if cell=='E' else '20'))
assert sim in (10,20,50) and (cell!='A' or sim==10)
settings={'A':('A500','68000',512,0,'--slow_memory=1536','kick40063.A600'),'B':('A1200','68EC020',2048,4096,'--slow_memory=0','kick40068.A1200'),'C':('A1200','68030',2048,4096,'--slow_memory=0 --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=50000000','kick40068.A1200'),'D':('A4000','68040-NOMMU',2048,16384,'--slow_memory=0 --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency='+os.environ.get('BENCH_CPU_HZ','25000000'),'kick40068.A1200'),'E':('A1200','68060-NOMMU',2048,16384,'--slow_memory=0 --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=50000000','kick40068.A1200')}
model,cpu,chip,fast,extra,kick=settings[cell]
if os.environ.get('BENCH_MMU')=='1':
 assert cell=='D'
 cpu='68040'
 model='A1200'  # Native IDE must match the available A1200 ROM.
 extra+=' --uae_cpu_model=68040 --uae_mmu_model=68040 --uae_cpu_24bit_addressing=false --jit_compiler=0'

if 'BENCH_FAST_KB' in os.environ:
 fast=int(os.environ['BENCH_FAST_KB'])
 assert cell=='B' and fast==0,'No-fast diagnostic is limited to the 020 cell'
 extra=extra.replace('--slow_memory=0','--slow_memory=1536')
if cell=='B' and 'BENCH_CPU_HZ' in os.environ:extra+=' --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency='+os.environ['BENCH_CPU_HZ']
frame={'A':15,'A-fast':25,'B':40,'B-fast':80}.get(a.cell,80 if detail else 60)
frame=int(os.environ.get('BENCH_FRAME',str(frame)))
# Frame-route production support is the next harness integration; do not silently
# substitute an instrumented build when the caller supplies production.
instrumented=b'4DTAPE!!' in slave.read_bytes()
assert instrumented or sim in (10,20) or b'4DSIMRUN' in slave.read_bytes(),'50 Hz needs an A4000 runtime build'
env=dict(os.environ,SLAVE=str(slave),AMIGA_MODEL=model,CPU=cpu,CHIP_KB=str(chip),FAST_KB=str(fast),EXTRA_ARGS=extra,KICKSTART=str(Path.home()/'.local/share/amiga/Kickstarts'/kick),DEBUG_PORT=os.environ.get('DEBUG_PORT','2471'),WHD_ARGS=os.environ.get('BENCH_WHD_ARGS','CUSTOM2=1'),TAPE_DETAIL=str(detail))
if cell in ('D','E'):
 env['FAST_KB']='8192'
 env['EXTRA_ARGS']+=' --motherboard_ram=8192 --uae_cpu_memory_cycle_exact=true'
 env['BENCH_MEMORY_KB']='8192';env['BENCH_MEMORY_BASE']='0x200000'
if os.environ.get('BENCH_SCAN_CHIP')=='1':
 env['BENCH_MEMORY_BASE']='0';env['BENCH_MEMORY_KB']=str(chip+int(env['FAST_KB']))
if cell=='C':env['EXTRA_ARGS']+=' --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_cpu_data_cache=true'
if os.environ.get('BENCH_CYCLE_EXACT')=='1':env['EXTRA_ARGS']+=' --uae_cpu_cycle_exact=true'
if os.environ.get('BENCH_BLITTER_EXACT')=='1':env['EXTRA_ARGS']+=' --uae_blitter_cycle_exact=true --uae_immediate_blits=false'
if 'BENCH_DCACHE' in os.environ:env['EXTRA_ARGS']+=' --uae_cpu_data_cache='+('true' if os.environ['BENCH_DCACHE']=='1' else 'false')
if os.environ.get('BENCH_INDIRECT')=='1':env['EXTRA_ARGS']+=' --uae_uaeboard=full+indirect'
if os.environ.get('BENCH_NOMMU')=='1':env['EXTRA_ARGS']+=' --uae_mmu_model=0'
if os.environ.get('NTSC')=='1':env['EXTRA_ARGS']+=' --uae_ntsc=true'
assert int(env['DEBUG_PORT'])>=2471
port=subprocess.run(['lsof','-nP','-iTCP:'+env['DEBUG_PORT'],'-sTCP:LISTEN'],capture_output=True,text=True)
assert not port.stdout,'Requested debugger port is already occupied'
def owned():
 f=ROOT/'tmp/run/default/.run/fsuae.pid'
 if not f.exists():return False
 pid=int(f.read_text());q=subprocess.run(['lsof','-a','-p',str(pid),'-d','cwd','-Fn'],capture_output=True,text=True)
 dirs=[x[1:] for x in q.stdout.splitlines() if x.startswith('n')]
 if not dirs:return False
 assert len(dirs)==1 and Path(dirs[0]).is_relative_to(ROOT),f'Refusing to touch unrelated emulator {pid}: {dirs}'
 return True
owned();out.parent.mkdir(parents=True,exist_ok=True);deadline=time.monotonic()+180
log=out.with_suffix('.runner.log').open('w')
def run(args):
 remaining=deadline-time.monotonic();assert remaining>0,'Three-minute cell watchdog expired'
 subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=remaining)
try:
 run(['python3','tools/quick_start.py' if instrumented else 'tools/bench_native_start.py',str(out),'--frame',str(frame),'--simulation',str(sim),'--detail',str(detail)]+(['--opponent',os.environ.get('BENCH_OPPONENT','0')] if instrumented else []))
 if os.environ.get('BENCH_DISABLED')=='1':run(['python3','tools/check_disabled.py',str(out)])
 run(['python3','tools/bench_window.py',str(out),'--seconds',os.environ.get('BENCH_SECONDS','10')])
 if os.environ.get('BENCH_EXTRA_SCRIPT'):run(['python3',os.environ['BENCH_EXTRA_SCRIPT'],str(out)])
 display=None
 if os.environ.get('BENCH_DISPLAY')=='1':
  run(['python3','tools/profile_window.py',str(out),'--fields',os.environ.get('BENCH_PROFILE_FIELDS','250')])
  run(['python3','tools/display_check.py',str(out)])
  display=json.loads((out/'display-check.json').read_text())
 config=ROOT/'tmp/run/default/.run/fsuae/Cache/Logs/debug.uae'
 config_text=config.read_text() if config.exists() else ''
 (out/'emulator-config.uae').write_text(config_text)
 cache_observed=dict(re.findall(r'(\w+)=([0-9a-fA-F]+)',(out/'cache-state.txt').read_text())) if (out/'cache-state.txt').exists() else {}
 cache_config={k:v for line in config_text.splitlines() if '=' in line for k,v in [line.split('=',1)] if k in ('cpu_type','cpu_model','cpu_speed','cpu_frequency','cpu_multiplier','cpu_cycle_exact','cpu_memory_cycle_exact','cpu_data_cache','cachesize')}
 r=json.loads((out/'window.json').read_text());r.update(cell=a.cell,slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(),settings={k:env[k] for k in ('CPU','AMIGA_MODEL','CHIP_KB','FAST_KB','EXTRA_ARGS','WHD_ARGS')},cache_state={'configured':cache_config,'guest_CACR':cache_observed.get('CACR','not captured'),'observed':cache_observed},display_validation=({'scope':'Separate 250-field marker/copper/four-plane DMA correspondence check; full-window FPS uses copper-switch counter','check':display} if display else 'pending DMA validation; copper-switch counts only'),watchdog_seconds=180)
 (out/'bench.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ('cell','fps','steps_per_second','backlog_start','backlog_end')}))
finally:
 if owned():
  try:
   subprocess.run(['python3','tools/driving.py','quit'],stdout=log,stderr=log,timeout=10,check=True)
  except (subprocess.TimeoutExpired,subprocess.CalledProcessError):
   if owned():
    os.kill(int((ROOT/'tmp/run/default/.run/fsuae.pid').read_text()),signal.SIGTERM)
    for _ in range(20):
     if not owned():break
     time.sleep(.1)
    if owned():os.kill(int((ROOT/'tmp/run/default/.run/fsuae.pid').read_text()),signal.SIGKILL)
   raise
 log.close()
