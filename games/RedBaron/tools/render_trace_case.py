"""Normal-build flight, warm-up, then one cycle-exact Barto trace with DMA records.

Same entry route as render_profile_case.py (CUSTOM2 omitted, Faster rendering default On).
No breakpoints inside the traced window. Usage, from the game directory:
  BENCH_BATCH_KEYS=1 BENCH_OMIT_CUSTOM2=1 python3 -B tools/render_trace_case.py 030 0 tmp/prof/trace-030 --warm 500 --fields 40
"""
import argparse,ast,hashlib,json,os,struct,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tools'))
import route_status as r
p=argparse.ArgumentParser();p.add_argument('machine');p.add_argument('mask',type=lambda s:int(s,0));p.add_argument('out',type=Path)
p.add_argument('--warm',type=int,default=500);p.add_argument('--fields',type=int,default=40);p.add_argument('--resume-sim',action='store_true');a=p.parse_args()
ROOT=Path.cwd();os.environ['GAME_DIR']='completion-benchmark/RedBaron';TRACKED=ROOT/'tools'
def run(*args):subprocess.run([sys.executable,'-B',*map(str,args)],check=True)
if not a.resume_sim:run('tools/completion_boot.py',a.machine,a.mask,a.out,'--entry-only')
ready=json.loads((a.out/'ps-ready.json').read_text());ps=ready['ps']
class _Host:
 def wait(self,timeout=None):pass
if a.resume_sim:host=_Host()
else:
 with (a.out/'input.log').open('w') as log:
  host=subprocess.Popen([sys.executable,'-B',str(TRACKED/'completion_host_input.py'),'--serve','--ps',hex(ps)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 end=time.monotonic()+1000
 while 'INPUT READY' not in (a.out/'input.log').read_text():
  if host.poll() is not None:raise RuntimeError('Input server exited; inspect input.log')
  if time.monotonic()>end:raise TimeoutError('Input attachment pending')
  time.sleep(1)
 run('tools/completion_keys.py',hex(ps),'ps',*(['return']*4+['tab']*4+['return','tab','return']))
s=ast.parse(Path('tools/completion_boot.py').read_text());fn=next(n for n in s.body if isinstance(n,ast.FunctionDef) and n.name=='locate');exec(compile(ast.Module(body=[fn],type_ignores=[]),'locate','exec'))
sim=locate('sim',0x1ef92,[0x309cc,0x30a4e,0x30aec])
run('tools/completion_keys.py',hex(sim),'sim','tab','return','f10','--polls','1')
keys=['tab']*5+['return']+['right']*20+['return','tab','return']+['right']*20+['return','tab','return']+['tab']*5+['return']
run('tools/completion_keys.py',hex(sim),'sim',*keys)
r.command(f'until {sim+0x21d30:#x}')
if os.environ.get('BENCH_OMIT_CUSTOM2')=='1':
 proof=r.command(f'gdb x/1hx {sim+0xb06:#x}');assert '0x7001' in proof,proof
# The input server's lldb blocks the profiler's lldb: release it while the guest runs.
r.command('cont')
run(TRACKED/'completion_host_input.py','quit');host.wait(timeout=60)
for _ in range(30):
 if subprocess.run(['pgrep','-f','completion_host_input.py --serve'],capture_output=True).returncode:break
 time.sleep(1)
else:raise RuntimeError('Input server still attached')
# Warm-up: count native VBlanks with a breakpoint, then remove it before tracing.
r.command(f'gdb delete\nbreak *{sim+0x2d34e:#x}\nignore $bpnum {a.warm}\ncontinue\ndelete')
r.command('stop')
regions=r.memory_regions()
for lo,hi in regions:r.command(f'gdb dump binary memory {a.out}/ram-{lo:x}.bin {lo:#x} {hi:#x}')
print(r.command(f'profile {a.fields} {(a.out/"trace.bin").resolve()}'),flush=True)
for lo,hi in regions:r.command(f'gdb dump binary memory {a.out}/ram-after-{lo:x}.bin {lo:#x} {hi:#x}')
env=ready['environment']
meta=dict(machine=a.machine,sim=sim,ps=ps,warm_fields=a.warm,fields=a.fields,regions=regions,
 slave_sha256=hashlib.sha256((a.out/'slave.slave').read_bytes()).hexdigest(),
 environment={k:env.get(k) for k in ['CPU','AMIGA_MODEL','CHIP_KB','FAST_KB','EXTRA_ARGS','WHD_ARGS']})
(a.out/'entry.json').write_text(json.dumps(meta,indent=2)+'\n')
(a.out/'debug.uae').write_bytes(Path('tmp/run/default/.run/fsuae/Cache/Logs/debug.uae').read_bytes())
r.command('quit')
print('TRACE COMPLETE',a.out,flush=True)
