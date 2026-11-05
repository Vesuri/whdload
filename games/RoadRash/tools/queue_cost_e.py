import os,sys,subprocess,shutil,json
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');rows=[]
for kind in ['sync','queue']:
 src=root/f'tmp/e-queue-cost-{kind}-source';shutil.copytree(root/'tmp/e-bob-prototype-source',src)
 p=src/'blitter_queue.s';s=p.read_text().replace(' btst #1,verify_attn+3(pc)\n beq .done',' nop\n nop\n nop\n nop\n nop')
 if kind=='sync':s=s.replace(' bsr e_bob_init',' nop\n nop')
 p.write_text(s);build=root/f'tmp/e-queue-cost-{kind}-build';subprocess.run(['bash','tools/build.sh'],env=dict(os.environ,RR_SOURCE=str(src),RR_BUILD_OUT=str(build)),check=True,stdout=subprocess.DEVNULL)
 for cell in ['a500-1m','030-50']:
  env=config(cell);env.update(SLAVE=str(build/'RoadRash.slave'),DEBUG_PORT='27772',WHD_ARGS='CUSTOM2=1')
  if cell=='a500-1m':env['FAST_KB']='8192'
  out=root/f'tmp/e-queue-cost-{kind}-{cell}';out.mkdir()
  try:
   with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/invoke_e.py','tools/check_a.py',str(out),'--normal'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
  finally:cleanup(out)
  row=dict(kind=kind,cell=cell,returncode=p.returncode)
  if (out/'result.json').exists():row['fps']=json.loads((out/'result.json').read_text())['fps']
  rows.append(row);(root/'tmp/e-queue-cost.json').write_text(json.dumps(rows,indent=2));print(row,flush=True);assert not p.returncode
