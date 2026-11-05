"""One normal-build A2 case. Sequential boot/input/census; retain failures paused."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import route_status as r
p=argparse.ArgumentParser();p.add_argument('machine');p.add_argument('mask',type=lambda s:int(s,0));p.add_argument('out',type=Path);p.add_argument('--resume-entry',action='store_true');a=p.parse_args()
ROOT=Path.cwd();os.environ['GAME_DIR']='RedBaron';TRACKED=ROOT/'tools'
def run(*args):subprocess.run([sys.executable,'-B',*map(str,args)],check=True)
if not a.resume_entry:run('tools/feedback_boot.py',a.machine,a.mask,a.out,'--entry-only')
ready=json.loads((a.out/'ps-ready.json').read_text());ps=ready['ps']
with (a.out/'input.log').open('w') as log:
 host=subprocess.Popen([sys.executable,'-B',str(TRACKED/'completion_host_input.py'),'--serve','--ps',hex(ps)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(a.out/'input-server.pid').write_text(str(host.pid))
end=time.monotonic()+1000
while 'INPUT READY' not in (a.out/'input.log').read_text():
 if host.poll() is not None:raise RuntimeError('Input server exited; inspect input.log')
 if time.monotonic()>end:raise TimeoutError('Input attachment still pending; inspect existing process, do not restart')
 time.sleep(1)
scene=os.environ.get('D5_SCENE','ace')
pskeys=(['return','tab','return']+['tab']*3+['return','tab','return']+['tab']*12+['return']+['tab']*3+['return']) if scene=='squadron' else (['return']*4+['tab']*4+['return','tab','return'])
run('tools/completion_keys.py',hex(ps),'ps',*pskeys)
# Reuse the boot scanner without invoking its CLI again.
import ast,struct
s=ast.parse(Path('tools/feedback_boot.py').read_text());fn=next(n for n in s.body if isinstance(n,ast.FunctionDef) and n.name=='locate');exec(compile(ast.Module(body=[fn],type_ignores=[]),'locate','exec'))
sim=locate('sim',0x1ef92,[0x309cc,0x30a4e,0x30aec])
(a.out/'sim.json').write_text(json.dumps(dict(sim=sim,ps=ps)))
run('tools/completion_keys.py',hex(sim),'sim','tab','return','--polls','1')
r.command(f'until {sim+0x21d30:#x}')
print('FLIGHT READY',hex(sim),flush=True)

def irq(raw,up=False):
 run(TRACKED/'completion_host_input.py',f'irq-{"up" if up else "down"}:{sim},{0x30f8c},{raw}')
irq(0x59)
r.command(f'until {sim+0x1fb3a:#x}')
irq(0x59,True)
keys=['tab']*5+['return']+['right']*20+['return','tab','return']+['right']*20+['return','tab','return']+['tab']*5+['return']
scale=int(os.environ.get('D5_SCALE','40'))
if scale!=40:
 assert scale in (0,60)
 keys=keys[:-6]+['tab']*4+['return']+['left']*20+(['right']*10 if scale==60 else [])+['return','tab','return']
run('tools/completion_keys.py',hex(sim),'sim',*keys)
(a.out/'scenario.json').write_text(json.dumps(dict(scene=scene,requested_time_scale=scale)))
# Pause the native game before handing it to the player.
irq(0x19)
r.command(f'until {sim+0x21ac4:#x}')
irq(0x19,True)
r.command('shot '+str((a.out/'ready.png').resolve()))
run(TRACKED/'completion_host_input.py','quit');host.wait(timeout=20)
r.command('gdb delete')
r.command('cont')
print('PLAYER READY: native pause; Return resumes. No automation remains.',flush=True)
