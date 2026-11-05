"""Frozen W2 build: bounded same-build steady costs, swap rate and state on each CPU."""
import argparse,json,os,re,subprocess,sys
from pathlib import Path
import route_status as r,step_log
sys.path.insert(0,str(r.ROOT/'tools'))
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
import call_costs,census_window,display_ownership
EXPECTED='1456f8d5b84cf787f3429b7ae6580fcc88ce94903d604bbb3d339610f85853b3'
p=argparse.ArgumentParser();p.add_argument('--machine',choices=['a500','020','030'],required=True);p.add_argument('--mask',type=int,choices=[0,56,60],required=True);p.add_argument('--suffix',default='');a=p.parse_args()
out=Path(f'tmp/prof/w2-combined-{a.machine}-{a.mask}{a.suffix}');assert not out.exists()
ref=Path(f'tmp/prof/w2-combined-twins-{a.machine}-bank');meta=json.loads((ref/'entry.json').read_text());assert meta['slave_sha256']==EXPECTED
common=' --uae_cpu_speed=real --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_blitter_cycle_exact=true'
env=dict(os.environ,MallocScribble='1',WHD_ARGS=f'CUSTOM2={a.mask} CUSTOM5=512'+(' MMU' if a.machine=='030' else ''),BOOT_BREAK=hex(meta['entry']['game_anchor']),CPU=meta['cpu'],CHIP_KB=meta['chip_kb'],FAST_KB=meta['fast_kb'],EXTRA_ARGS=meta['extra_args'],AMIGA_MODEL='A1200' if a.machine=='020' else 'A500')
if a.machine=='020':env['KICKSTART']=os.environ['KICKSTART_A1200']
pid=(r.ROOT/'tmp/run/default/.run/fsuae.pid').read_text().strip();z=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True)
if z.returncode==0:assert f'--base_dir={r.ROOT/"tmp/run/default/.run/fsuae"}' in z.stdout
with Path(f'tmp/w2-combined-{a.machine}-{a.mask}{a.suffix}.log').open('w') as log:subprocess.run([sys.executable,'tools/reach_flight.py','--no-shot','--out',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
assert json.loads((out/'entry.json').read_text())['slave_sha256']==EXPECTED
step_log.advance(8)
def snapshot(step):
 state=step_log.collect();assert state['count']==step
 (out/f'step{step}.json').write_text(json.dumps(state,indent=2)+'\n')
 r.command(f'gdb dump binary memory {out}/h3-step{step}.bin {state["h3"]:#x} {state["h3"]+0xbd0c:#x}')
 return state
s=snapshot(8);sim=s['sim']
if a.machine=='030':
 if a.mask==56:
  subprocess.run([sys.executable,'tools/w2_math_clock.py','--group','math','--entry',str(out),'--mask',str(a.mask),'--step','14','--out',str(out/'math-clock.json')],check=True)
  subprocess.run([sys.executable,'tools/routine_wall_time.py',str(out/'math-clock.json'),'--first-step','8','--last-step','13','--out',str(out/'math-summary.json')],check=True)
 subprocess.run([sys.executable,'tools/routine_clock.py','--step','16','--out',str(out/'steady-clock.json')],check=True)
 subprocess.run([sys.executable,'tools/capture_current.py','--out',str(out/'dma'),'--fields','20'],check=True)
 names=['dma']
else:
 names=[]
 for n,fields in ([('steady-0',100),('steady-1',50)] if a.machine=='a500' else [('steady-0',40)]):
  subprocess.run([sys.executable,'tools/capture_current.py','--out',str(out/n),'--fields',str(fields)],check=True);names.append(n)
 paths=[out/n/'trace.bin' for n in names];listing=(out/'slave.lst').read_text(encoding='latin1')
 def label(n):return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
 slave=meta['entry']['game_anchor']-label('tape_game_anchor');stacks={'vbl':set(),'cia':set()}
 for path in paths:
  t=barto.load(path)
  for field in t.fields:
   for pc,cycles,regs in t.instructions(field):
    if pc==sim+0x2d344:stacks['vbl'].add(regs[15])
    if pc==sim+0x2ffcc:stacks['cia'].add(regs[15])
 assert all(stacks.values());pages={v&~0x3fff for vals in stacks.values() for v in vals};assert len(pages)==1;low=pages.pop()
 overrides={'projection':(sim+0x38c82,slave+label('projection_return') if a.mask else sim+0x38dca),'dot':(sim+0x3b1fa,slave+label('dot_return') if a.mask else sim+0x3b280),'clip':(sim+0x39ecc,(slave+label('clip_return'),sim+0x39f5a) if a.mask else sim+0x39f5a),'vertex':(sim+0x38dcc,(sim+0x38e00,slave+label('vertex_return')) if a.mask else (sim+0x38e00,sim+0x38e7e))}
 result=call_costs.measure(paths,sim,low,low+0x4000,overrides);(out/'steady-costs.json').write_text(json.dumps(result,indent=2)+'\n');print(a.machine,a.mask,'costs',result['summary'],flush=True)
# Reuse the short captures for ownership and CUSTOM-off audits.
for name in names:
 window=out/name;before=json.loads((window/'before.json').read_text());after=json.loads((window/'after.json').read_text())
 buffers=sorted({row['display'] for log in (before,after) for row in log['records']});assert len(buffers)==2
 result=display_ownership.analyse(window/'trace.bin',sim,buffers);(window/'display.json').write_text(json.dumps(result,indent=2)+'\n');print(a.machine,a.mask,'display',result['observable'],len(result['active_display_conflicts']),flush=True)
args=[sys.executable,'tools/check_disabled.py','tmp/game/RedBaron/data/sim','--sim',str(sim),'--custom2',str(a.mask)]
for memory in sorted((out/names[0]).glob('memory-*.bin')):args+=['--memory',str(int(memory.stem.split('-')[1],16))+':'+str(memory)]
subprocess.run(args,check=True)
start,end={'a500':(40,140),'020':(80,400),'030':(120,660)}[a.machine]
step_log.advance(start);snapshot(start)
print(r.command('shot '+str((out/'start.png').resolve())),flush=True)
subprocess.run([sys.executable,'tools/w2_window.py','--step-limit',str(end+1),'--out',str(out/'census')],check=True)
census=json.loads((out/'census/census.json').read_text());summary=census_window.summarize(census,start,end);assert summary['meets_2000_fields']
(out/'rate.json').write_text(json.dumps(summary,indent=2)+'\n');print(a.machine,a.mask,'RATE',summary,flush=True)
snapshot(end+1);print(r.command('shot '+str((out/'end.png').resolve())),flush=True)
(out/'complete.json').write_text(json.dumps(dict(complete=True,machine=a.machine,mask=a.mask,sha256=EXPECTED),indent=2)+'\n')
