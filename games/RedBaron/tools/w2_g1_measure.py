"""Focused same-build OFF/ON G1 steady and bank traces, one controller."""
import json,os,re,subprocess,sys
from pathlib import Path
import route_status as r,step_log
sys.path.insert(0,str(r.ROOT/'tools'))
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
import call_costs
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--revision',type=int,default=1);revision=parser.parse_args().revision
suffix='' if revision==1 else f'-r{revision}'
ref=Path('tmp/prof/w2-g1-twins-a500'+suffix);meta=json.loads((ref/'entry.json').read_text())
for mask in (0,4):
 out=Path(f'tmp/prof/w2-g1-a500-{mask}'+suffix);assert not out.exists()
 pid=(r.ROOT/'tmp/run/default/.run/fsuae.pid').read_text().strip();z=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True)
 if z.returncode==0:assert f'--base_dir={r.ROOT/"tmp/run/default/.run/fsuae"}' in z.stdout
 env=dict(os.environ,MallocScribble='1',AMIGA_MODEL='A500',CPU=meta['cpu'],CHIP_KB=meta['chip_kb'],FAST_KB=meta['fast_kb'],EXTRA_ARGS=meta['extra_args'],WHD_ARGS=f'CUSTOM2={mask} CUSTOM5=514',BOOT_BREAK=hex(meta['entry']['game_anchor']))
 with Path(f'tmp/w2-g1-a500-{mask}.log').open('w') as log:subprocess.run([sys.executable,'tools/reach_flight.py','--no-shot','--out',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 assert json.loads((out/'entry.json').read_text())['slave_sha256']==meta['slave_sha256']
 step_log.advance(8);s=step_log.collect();(out/'step8.json').write_text(json.dumps(s,indent=2)+'\n');r.command(f'gdb dump binary memory {out}/h3-step8.bin {s["h3"]:#x} {s["h3"]+0xbd0c:#x}')
 for name,fields in [('steady-0',100),('steady-1',50),('bank',100)]:
  if name=='bank':step_log.advance(24)
  subprocess.run([sys.executable,'tools/capture_current.py','--out',str(out/name),'--fields',str(fields)],check=True)
 listing=(out/'slave.lst').read_text(encoding='latin1')
 def label(n):return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
 sim=meta['entry']['sim'];slave=meta['entry']['game_anchor']-label('tape_game_anchor')
 for window,names in [('steady',['steady-0','steady-1']),('bank',['bank'])]:
  paths=[out/n/'trace.bin' for n in names];stacks={'vbl':set(),'cia':set()}
  for path in paths:
   t=barto.load(path)
   for f in t.fields:
    for pc,cycles,regs in t.instructions(f):
     if pc==sim+0x2d344:stacks['vbl'].add(regs[15])
     if pc==sim+0x2ffcc:stacks['cia'].add(regs[15])
  assert all(stacks.values());pages={v&~0x3fff for vals in stacks.values() for v in vals};assert len(pages)==1;low=pages.pop()
  result=call_costs.measure(paths,sim,low,low+0x4000,{'projection':(sim+0x38c82,slave+label('projection_return') if mask else sim+0x38dca)});result['observed_callback_stacks']={k:sorted(v) for k,v in stacks.items()}
  (out/(window+'-costs.json')).write_text(json.dumps(result,indent=2)+'\n');print(mask,window,result['summary'],flush=True)
 (out/'complete.json').write_text(json.dumps({'complete':True,'mask':mask,'sha256':meta['slave_sha256']},indent=2)+'\n')
