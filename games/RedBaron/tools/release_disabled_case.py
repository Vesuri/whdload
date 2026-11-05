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

sys.path.insert(0,str(TRACKED))
from check_disabled import check
from hook_ranges import ranges
from hunks import read_hunks
banks=[]
for lo,hi in r.memory_regions():
 path=a.out/f'audit-bank-{lo:x}.bin'
 r.command(f'gdb dump binary memory {path} {lo:#x} {hi:#x}')
 banks.append((lo,path.read_bytes()))
def read(addr,size):
 for lo,b in banks:
  at=addr-lo
  if 0<=at and at+size<=len(b):return b[at:at+size]
 raise ValueError('Missing memory')
results={};files=[]
for domain,filename in [('sim','sim'),('sound','amigasnd.drv')]:
 original=((Path('tmp/game')/os.environ['GAME_DIR'])/'data'/filename).read_bytes()
 hs=read_hunks(original)
 if domain=='sim':candidates=[sim]
 else:
  rel={i for at,target in hs[0].relocations for i in range(at,at+4)}
  offset=next(i for i in range(0,256,2) if not rel.intersection(range(i,i+16)))
  sig=hs[0].data[offset:offset+16];candidates=[]
  for lo,b in banks:
   at=0
   while True:
    at=b.find(sig,at)
    if at<0:break
    candidates.append(lo+at-offset);at+=2
 passed=[]
 for base in candidates:
  try:bases=check(original,base,read,ranges(domain=domain),domain)
  except (ValueError,struct.error):continue
  passed.append(base)
  for j,(h,b) in enumerate(zip(hs,bases)):
   path=a.out/f'{domain}-{base:x}-h{j}.bin'
   path.write_bytes(read(b-4,4+len(h.data)));files.append(dict(base=b-4,file=path.name))
 assert passed,(domain,candidates)
 results[domain]=dict(bases=passed,ranges=len(ranges(domain=domain)))
result=dict(build_mode=meta['build_mode'],custom2=a.mask,slave_sha256=meta['slave_sha256'],domains=results,memory=files)
(a.out/'disabled-check.json').write_text(json.dumps(result,indent=2)+'\n')
print('DISABLED CHECK',json.dumps(result),flush=True)
run(TRACKED/'completion_host_input.py','quit');host.wait(timeout=20)
r.command('quit')
for path in list(a.out.glob('audit-bank-*.bin'))+list(a.out.glob('locate-*.bin')):path.unlink()
