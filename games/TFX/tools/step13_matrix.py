"""Cold-boot executable/option matrix; read-only game code and publication checks."""
import os,sys,json,re,struct,shutil
from pathlib import Path
import replay_flight as replay
from replay_flight import sha
from step13_environment import prepare
ROOT=prepare(replay)
from baseline_matrix import VARIANTS
from amigaxdev import barto
out=Path(sys.argv[1]).resolve();phase=sys.argv[2];os.chdir(ROOT);out.mkdir(parents=True,exist_ok=True)
# Bound discovery to the upper 8 MB, including lower auxiliary hunks; retain
# signature/hunk validation and fail if the executable ever moves outside it.
source=Path(replay.__file__).read_text().replace("dump('locate-fast.bin',0x40000000,0x2000000)","dump('locate-fast.bin',0x41800000,0x800000)").replace('fast[a-0x40000000:a-0x40000000+n]','fast[a-0x41800000:a-0x41800000+n]').replace('0x40000000+pos-off','0x41800000+pos-off')
source=source.replace("cmd('monitor fields 8')", "cmd('monitor fields 40' if machine=='020' and (variant['custom4']&4 or variant['executable'] in ['TFX.FPU','TFX.040']) else 'monitor fields 8')").replace('threading.Timer(180,timeout)', "threading.Timer(60 if s=='continue' else 180,timeout)")
source=source.replace("cmd('monitor fields 1500')", "cmd('monitor fields 3000' if machine=='020' and (variant['custom4']&4 or variant['executable'] in ['TFX.FPU','TFX.040']) else 'monitor fields 1500')").replace("cmd('monitor fields 20')", "cmd('monitor fields 80' if machine=='020' and (variant['custom4']&4 or variant['executable'] in ['TFX.FPU','TFX.040']) else 'monitor fields 20')")
source=source.replace(" def cmd(s):\n", " def cmd(s):\n  if s.startswith('monitor fields ') and int(s.split()[-1])>250:\n   n=int(s.split()[-1]);return '\\n'.join(cmd(f'monitor fields {min(250,n-i)}') for i in range(0,n,250))\n")
source=source.replace('{p.relative_to(ROOT)}','{p}').replace('from tfx import server','# server supplied by the step13 runtime')
ns=dict(replay.__dict__);ns['__name__']='step13_bounded_discovery';exec(compile(source,replay.__file__,'exec'),ns);run=ns['run']
assert ns['ROOT']==ROOT and Path(ns['server'].run_script)==ROOT.parents[1]/'common/run.sh'
suffix='-'+os.environ['STEP13_SHARD'] if os.environ.get('STEP13_SHARD') else ''
summary_path=out/('summary'+suffix+'.json')
(out/('effective-replay'+suffix+'.py')).write_text(source)


def capture(v,cpu):
 def observe(cmd,dump,bases,hs,d):
  info=cmd('monitor cpuinfo');(d/'cpuinfo.txt').write_text(info)
  fields=dict(re.findall(r'(\w+)=(\w+)',info))
  assert int(fields['cpu'])==int('68'+cpu)
  assert int(fields['fpu'])=={'020':(68881 if os.environ.get('STEP13_020_FPU')=='68881' else 68882) if os.environ.get('STEP13_020_FPU') else 0,'030':68882,'040':68040,'060':68060}[cpu]
  code=dump('code.bin',bases[0],hs[0]['size'])
  if v['executable']=='tfx.020':
   target=True;original=bool(v['custom4']&4)
   for off in [0x4f840,0x4f9f8]:assert (code[off:off+2]==bytes.fromhex('4ef9'))==(target and not original)
   assert (bases[1]>=0x40000000 and bases[2]>=0x40000000)==(target and not original)
   limit=1 if target and v['custom4']&64 else 0 if target and v['custom4']&32 else 2
   assert struct.unpack_from('>H',code,0x1abfe)[0]==0x7000+limit
   # Native 040 transcendental replacement must respect CUSTOM5 and exclude 030/060.
   assert (code[0x50f82:0x50f86]==bytes.fromhex('4eb801fc'))==(cpu=='040' and not v.get('custom5',0))
  if v['executable']=='tfx.020' and os.environ.get('DELTA_LISTING'):
   from exe_compare_audit import audit
   audit(cmd,dump,bases,hs,d,cpu,v,os.environ['DELTA_LISTING'])
  cmd('delete breakpoints');pc=bases[0]+v['publish']
  assert dump('publication-opcode.bin',pc,6)==bytes.fromhex('23c800dff080')
  cmd(f'break *{pc:#x}')
  for _ in range(3):
   reply=cmd('continue');assert re.search(r'Breakpoint \d+, '+f'0x{pc:08x}',reply),reply[-500:]
  cmd('delete breakpoints');p=d/'flight.trace';cmd(f'monitor profile 1 "" "{p}"');t=barto.load(p);(d/'flight.png').write_bytes(t.fields[-1].shot)
  (d/'audit.json').write_text(json.dumps(dict(passed=True,cpu=cpu,variant=v,publications=3,code_sha256=sha(d/'code.bin')),indent=2))
 return observe

rows=[]
for cpu in os.environ.get('STEP13_CPUS','040 020 030 060').split():
 for c4,label in [(18,'auto'),(22,'auto-original')]:
  name='newfpu' if (cpu in os.environ.get('AUTO_FPU_CPUS','040').split() and phase!='baseline') or (c4&4 and (cpu!='020' or os.environ.get('STEP13_020_FPU'))) else 'integer'
  rows.append((cpu,label,dict(VARIANTS[name],custom3=0,custom4=c4)))
 if phase!='baseline':
  for name in ['integer','fpu','newfpu','beta']:
   if cpu=='020' and not os.environ.get('STEP13_020_FPU') and name!='integer':continue
   rows.append((cpu,name,dict(VARIANTS[name])))
  for c4,label in [(26,'fps'),(30,'fps-original'),(50,'uncapped'),(82,'oneframe'),(114,'both'),(118,'both-original')]:
   name='newfpu' if cpu in os.environ.get('AUTO_FPU_CPUS','040').split() or (c4&4 and (cpu!='020' or os.environ.get('STEP13_020_FPU'))) else 'integer'
   rows.append((cpu,label,dict(VARIANTS[name],custom3=0,custom4=c4)))
  name='integer' if cpu=='020' and not os.environ.get('STEP13_020_FPU') else 'newfpu'
  rows.append((cpu,'no-fpu-fixes',dict(VARIANTS[name],custom5=1)))
  if cpu!='020' or os.environ.get('STEP13_020_FPU'):
   rows.append((cpu,'integer-projection',dict(VARIANTS['newfpu'],custom1=1)))
summary={}
for cpu,label,v in rows:
 key=cpu+'-'+label;d=out/key
 if os.environ.get('STEP13_ROWS') and key not in os.environ['STEP13_ROWS'].split():continue
 if (d/'audit.json').exists():summary[key]=json.loads((d/'audit.json').read_text());continue
 v['extra_args']='--uae_fpu_no_unimplemented=true' if cpu in ['040','060'] else ''
 if cpu=='020' and os.environ.get('STEP13_020_FPU'):v['extra_args']+=' --uae_fpu_model='+('68881' if os.environ.get('STEP13_020_FPU')=='68881' else '68882')
 try:
  run(cpu,d,out/(key+'-seed'),capture(v,cpu),v);summary[key]=json.loads((d/'audit.json').read_text())
 except Exception as e:
  summary[key]=dict(passed=False,error=repr(e));summary_path.write_text(json.dumps(summary,indent=2));raise
 summary_path.write_text(json.dumps(summary,indent=2));print('PASS',key,flush=True)
summary_path.write_text(json.dumps(summary,indent=2))
shutil.copy(__file__,out/('step13_matrix'+suffix+'.py'))
