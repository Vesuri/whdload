"""One normal-build A2 case. Sequential boot/input/census; retain failures paused."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import route_status as r
p=argparse.ArgumentParser();p.add_argument('machine');p.add_argument('mask',type=lambda s:int(s,0));p.add_argument('out',type=Path);p.add_argument('--resume-entry',action='store_true');a=p.parse_args()
ROOT=Path.cwd();os.environ['GAME_DIR']='completion-benchmark/RedBaron';TRACKED=ROOT/'tools'
def run(*args):subprocess.run([sys.executable,'-B',*map(str,args)],check=True)
if not a.resume_entry:run('tools/completion_boot.py',a.machine,a.mask,a.out,'--entry-only')
ready=json.loads((a.out/'ps-ready.json').read_text());ps=ready['ps']
with (a.out/'input.log').open('w') as log:
 host=subprocess.Popen([sys.executable,'-B',str(TRACKED/'completion_host_input.py'),'--serve','--ps',hex(ps)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(a.out/'input-server.pid').write_text(str(host.pid))
end=time.monotonic()+1000
while 'INPUT READY' not in (a.out/'input.log').read_text():
 if host.poll() is not None:raise RuntimeError('Input server exited; inspect input.log')
 if time.monotonic()>end:raise TimeoutError('Input attachment still pending; inspect existing process, do not restart')
 time.sleep(1)
run('tools/completion_keys.py',hex(ps),'ps',*(['return']*4+['tab']*4+['return','tab','return']))
# Reuse the boot scanner without invoking its CLI again.
import ast,struct
s=ast.parse(Path('tools/completion_boot.py').read_text());fn=next(n for n in s.body if isinstance(n,ast.FunctionDef) and n.name=='locate');exec(compile(ast.Module(body=[fn],type_ignores=[]),'locate','exec'))
sim=locate('sim',0x1ef92,[0x309cc,0x30a4e,0x30aec])
run('tools/completion_keys.py',hex(sim),'sim','tab','return','f10','--polls','1')
keys=['tab']*5+['return']+['right']*20+['return','tab','return']+['right']*20+['return','tab','return']+['tab']*5+['return']
run('tools/completion_keys.py',hex(sim),'sim',*keys)
r.command(f'until {sim+0x21d30:#x}')
env=ready['environment']
meta=dict(machine=a.machine,mask=a.mask,build_mode='developer' if env['DEVELOPER']=='1' else 'normal',sim=sim,ps=ps,slave_sha256=hashlib.sha256((a.out/'slave.slave').read_bytes()).hexdigest(),environment={k:env[k] for k in ['CPU','AMIGA_MODEL','CHIP_KB','FAST_KB','EXTRA_ARGS','WHD_ARGS']},realism_sha256=hashlib.sha256(((Path('tmp/game')/os.environ['GAME_DIR'])/'data/mreal.prf').read_bytes()).hexdigest(),route='Damage-protected benchmark fixture; native keyboard queue via host debugger; maximum World/Aircraft, Ground ON IN COMBAT; unchanged Time Scale')
(a.out/'entry.json').write_text(json.dumps(meta,indent=2)+'\n')
if os.environ.get('BENCH_OMIT_CUSTOM2')=='1':
 proof=r.command(f'gdb x/1hx {sim+0xb06:#x}')
 assert '0x7001' in proof,proof
 (a.out/'default-selection.txt').write_text(proof)

stop=r.command(f'gdb delete\nbreak *{sim+0x21f4a:#x}\nbreak *{sim+0x21d30:#x}\nignore $bpnum 1\ncontinue\ndelete');assert f'0x{sim+0x21d30:08x}' in stop, 'Flight ended while warming'
opening_only=os.environ.get('BENCH_OPENING_ONLY')=='1'
if os.environ.get('BENCH_EVENT_ONLY')!='1':
 run('tools/completion_census.py',a.out,'--fields',int(os.environ.get('BENCH_FIELDS',1000 if a.machine=='a500' else 2000)),'--window','opening' if opening_only else 'steady')
if opening_only:
 r.command('shot '+str((a.out/'final.png').resolve()))
 (a.out/'debug.uae').write_bytes(Path('tmp/run/default/.run/fsuae/Cache/Logs/debug.uae').read_bytes())
 run(TRACKED/'completion_host_input.py','quit');host.wait(timeout=20)
 r.command('quit');print('CASE COMPLETE',a.out,flush=True);raise SystemExit

run('tools/completion_keys.py',hex(sim),'sim','f2','--polls','1')
stop=r.command(f'gdb delete\nbreak *{sim+0x21f4a:#x}\nbreak *{sim+0x21d30:#x}\nignore $bpnum 1\ncontinue\ndelete');assert f'0x{sim+0x21d30:08x}' in stop, 'Flight ended while warming'
run(TRACKED/'completion_host_input.py',f'queue:{sim},{0x30f8c},{0x50}')
run('tools/completion_census.py',a.out,'--fields',2000,'--window','event')
run(TRACKED/'completion_host_input.py',f'release:{sim},{0x30f8c},{0x50}')
r.command('shot '+str((a.out/'final.png').resolve()))
(a.out/'debug.uae').write_bytes(Path('tmp/run/default/.run/fsuae/Cache/Logs/debug.uae').read_bytes())
run(TRACKED/'completion_host_input.py','quit');host.wait(timeout=20)
r.command('quit')
print('CASE COMPLETE',a.out,flush=True)
