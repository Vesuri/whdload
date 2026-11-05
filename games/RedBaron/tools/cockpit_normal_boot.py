"""Short direct-scene comparison using the established local native-input harness.

Run from the game directory. Set BENCH_DEVELOPER=1 and BENCH_BATCH_KEYS=1.
Use the same frozen developer binary for both masks; only the feature under test may differ.
The local completion_boot driver supports BENCH_FROZEN_SLAVE for this purpose.
"""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tools'))
import route_status as r
p=argparse.ArgumentParser();p.add_argument('machine',choices=('a500','020','030','030-nommu','040','060'));p.add_argument('mask',type=lambda s:int(s,0));p.add_argument('out',type=Path);p.add_argument('--bank-after',type=int,default=0,help='Additional held-bank FPS window after level flight');p.add_argument('--resume-entry',action='store_true');p.add_argument('--check-only',action='store_true',help='Normal-build default and CPU-gate smoke check, without profiling');p.add_argument('--fields',type=int,default=250);p.add_argument('--dma-fields',type=int,default=0,help='Optional bounded page-safety trace after profiling');p.add_argument('--groups',nargs='+',choices=('stages','draw','fps','rate'),default=['stages','draw']);a=p.parse_args()
if a.bank_after and (not 250 <= a.bank_after <= 2000 or a.check_only or a.dma_fields):p.error('Bank-after requires 250–2000 fields and excludes check-only/DMA')
if not 10 <= a.fields <= 2000:p.error('Use a bounded 10–2000-field window')
if a.dma_fields and (not 10 <= a.dma_fields <= 40 or a.check_only or 'stages' not in a.groups):p.error('DMA checking requires stages and 10–40 fields')
ROOT=Path.cwd();os.environ['GAME_DIR']='completion-benchmark/RedBaron';TRACKED=ROOT/'tools'
def run(*args):subprocess.run([sys.executable,'-B',*map(str,args)],check=True)
if not a.resume_entry:run('tools/completion_boot.py',a.machine,a.mask,a.out,'--entry-only')
ready=json.loads((a.out/'ps-ready.json').read_text());ps=ready['ps']
ready['environment']={k:v for k,v in ready['environment'].items() if k in ('CPU','AMIGA_MODEL','CHIP_KB','FAST_KB','EXTRA_ARGS','WHD_ARGS','DEVELOPER','VERIFY')}
(a.out/'ps-ready.json').write_text(json.dumps(ready,indent=2)+'\n')
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
run('tools/completion_keys.py',hex(sim),'sim','tab','return','--polls','1')

r.command(f"until {sim+0x21d30:#x}")
(a.out/"runtime.json").write_text(json.dumps(dict(sim=sim,ps=ps)))
print("NORMAL FLIGHT READY",hex(sim),flush=True)
