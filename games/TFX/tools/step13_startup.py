"""Capture native configuration/intro/non-action boot paths on every CPU."""
import sys,os,json,shutil,re
from pathlib import Path
import replay_flight as replay
from baseline_matrix import VARIANTS
from step13_environment import prepare
prepare(replay)
from amigaxdev import barto
out=Path(sys.argv[1]).resolve();os.chdir(replay.ROOT);out.mkdir(parents=True,exist_ok=True)
def observe(cmd,dump,bases,hs,d):
 info=cmd('monitor cpuinfo');(d/'cpuinfo.txt').write_text(info)
 fields=dict(re.findall(r'(\w+)=(\w+)',info))
 assert int(fields['cpu'])==int('68'+cpu)
 assert int(fields['fpu'])=={'020':68882 if os.environ.get('STEP13_020_FPU') else 0,'030':68882,'040':68040,'060':68060}[cpu]
 for delay in [0,250,500]:
  if delay:cmd(f'monitor fields {delay}')
  p=d/f'startup-{delay}.trace';cmd(f'monitor profile 1 "" "{p}"');t=barto.load(p);(d/f'startup-{delay}.png').write_bytes(t.fields[-1].shot)
 (d/'registers.txt').write_text(cmd('info registers'))
 # Retain the native screen without guessing whether a later menu was reached.
 (d/'capture.json').write_text(json.dumps(dict(captured=True),indent=2))
source=Path(replay.__file__).read_text()
source=source.replace("cmd('monitor fields 1500');print", "cmd('monitor fields 1500');observer(cmd,dump,[],[],out);return {};print")
source=source.replace(" def cmd(s):\n", " def cmd(s):\n  if s.startswith('monitor fields ') and int(s.split()[-1])>250:\n   n=int(s.split()[-1]);return '\\n'.join(cmd(f'monitor fields {min(250,n-i)}') for i in range(0,n,250))\n")
source=source.replace('from tfx import server','# server supplied by step13 runtime').replace('{p.relative_to(ROOT)}','{p}')
ns=dict(replay.__dict__);ns['__name__']='startup_capture';exec(compile(source,replay.__file__,'exec'),ns)
for cpu in os.environ.get('STEP13_CPUS','040 020 030 060').split():
 for c4,name in [(0,'intro'),(2,'menu'),(3,'configuration'),(16,'action-intro')]:
  d=out/(cpu+'-'+name)
  if (d/'capture.json').exists():continue
  v=dict(VARIANTS['newfpu' if cpu!='020' or os.environ.get('STEP13_020_FPU') else 'integer'],custom3=0,custom4=c4,extra_args='--uae_fpu_no_unimplemented=true')
  if cpu=='020' and os.environ.get('STEP13_020_FPU'):v['extra_args']+=' --uae_fpu_model=68882'
  ns['run'](cpu,d,out/(d.name+'-seed'),observe,v);print('CAPTURE',d.name,flush=True)
shutil.copy(__file__,out/'step13_startup.py')
