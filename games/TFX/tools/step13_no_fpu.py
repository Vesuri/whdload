"""Record expected unsupported forced-FPU starts on the no-FPU 020."""
import sys,os,shutil,json
from pathlib import Path
import replay_flight as replay
from baseline_matrix import VARIANTS
from step13_environment import prepare
prepare(replay)
from amigaxdev import barto
out=Path(sys.argv[1]).resolve();os.chdir(replay.ROOT);out.mkdir(parents=True)
def observe(cmd,dump,bases,hs,d):
 cmd('monitor key 44 1');cmd('monitor fields 8');cmd('monitor key 44 0');cmd('monitor fields 1500')
 p=d/'result.trace';cmd(f'monitor profile 1 "" "{p}"');t=barto.load(p);(d/'result.png').write_bytes(t.fields[-1].shot)
 (d/'registers.txt').write_text(cmd('info registers'))
source=Path(replay.__file__).read_text().replace("cmd(f'break *{anchor:#x}');cmd('monitor key 44 1')", "observer(cmd,dump,bases,hs,out);return {}")
source=source.replace(" def cmd(s):\n", " def cmd(s):\n  if s.startswith('monitor fields ') and int(s.split()[-1])>250:\n   n=int(s.split()[-1]);return '\\n'.join(cmd(f'monitor fields {min(250,n-i)}') for i in range(0,n,250))\n")
source=source.replace('from tfx import server','# server supplied by step13 runtime').replace('{p.relative_to(ROOT)}','{p}')
ns=dict(replay.__dict__);ns['__name__']='no_fpu_capture';exec(compile(source,replay.__file__,'exec'),ns)
summary={}
for name in ['fpu','newfpu','beta']:
 try:
  ns['run']('020',out/name,out/(name+'-seed'),observe,dict(VARIANTS[name]));summary[name]={'captured':True,'supported':False}
 except Exception as e:summary[name]={'captured':False,'supported':False,'error':repr(e)}
 (out/'summary.json').write_text(json.dumps(summary,indent=2));print('CAPTURE',name,summary[name],flush=True)
shutil.copy(__file__,out/'step13_no_fpu.py')
